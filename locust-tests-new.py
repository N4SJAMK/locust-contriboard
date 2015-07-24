from os     import urandom
from locust import HttpLocust, TaskSet, task, events

import json
import string
import random
import base64
import datetime
import time

#VARIABLE SETTINGS
MAX_BOARDS 				= 2
MAX_WAIT_TIME_SECONDS 	= 2

#CONSTANT STUFF
COLOR = ['#4F819A','#724A7F','#DCC75B','#EB584A']
BACKGROUND = ['SWOT','PLAY','BLANK','DEFAULT','KANBAN','KEEP_DROP_TRY','NONE','SMOOTH_BRAINSTORMING','IDEA_GATHERING','LEAN_CANVAS']
AVATAR = ['http://placebacon.net/400/300', 'https://placehold.it/350x150', 'http://lorempixel.com/100/100/cats/']
EXPORT_FORMAT = ['json', 'csv', 'plaintext', 'image']
logfile = open('logs/' + str(time.time()) + 'locustlog.txt', 'w')
failurelog = open('logs/'+ str(time.time()) + 'failurelog.txt', 'w')

#Prevent stats being reset after all locusts hatched
#so we can log all requests correctly.
from locust.stats import RequestStats
def noop(*arg, **kwargs):
    print "Stats reset prevented by monkey patch!"
RequestStats.reset_all = noop

def successlogging(request_type, name, response_time, response_length):	
	st = datetime.datetime.fromtimestamp(time.time()).strftime('%d-%m-%Y %H:%M:%S.%f')
	logfile.write('[' + st + '] ' + request_type + '\t' + name + '\n')

def faillogging(request_type, name, response_time, exception):
	print exception
	st = datetime.datetime.fromtimestamp(time.time()).strftime('%d-%m-%Y %H:%M:%S.%f')
	failurelog.write('[' + st + '] ' + request_type + '\t' + name + '\t' + str(exception) + '\n')
	
def close_log():
	logfile.close()
	failurelog.close() 

events.request_success += successlogging 
events.request_failure += faillogging 
events.quitting += close_log

#Common store for all hatchlings
sharedboards = { }
USER_COUNT = 0

#TASKS START
class TeamboardTasks(TaskSet):

	#When we start we want to automaticaly register and log in the spawned user.
	def on_start(self):
		global USER_COUNT
		self.boards  	= { }
		self.token 		= None
		self.username = 'test_' + urandom(16).encode('hex') + '@garnet.red'
		self.password = urandom(16).encode('hex')
		with self.client.post('api/auth/register', 
							data={
								'email': self.username,
								'password': self.password
							}, 
							timeout=MAX_WAIT_TIME_SECONDS, 
							name='Register', catch_response=True) as response:
			if response.status_code != 201:
				response.failure("Register failed, code: " + str(response.status_code))
				
		with self.client.get('api/auth/basic/login', 
										params={
											'email': self.username,
											'password': self.password
										}, 
										headers={
											'Authorization':'Basic ' + base64.b64encode(self.username+':'+self.password)
										}, 
										timeout=MAX_WAIT_TIME_SECONDS, 
										name='Login', catch_response=True) as response:

			if response.status_code == 200:
				self.token = response.headers['x-access-token']
				USER_COUNT = USER_COUNT + 1
			else:
				response.failure("On start login failed, code: " + str(response.status_code))

			print USER_COUNT
	'''
	API: /routes/auth.js
	'''

	@task(1)
	def get_auth(self):
		if self.token is None: return
		with self.client.get('api/auth',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Auth request',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Get Auth failed, code: " + str(response.status_code))

	#Test user logout and then get resource after user has been logged out
	#Then we log user back in so we can continue our tests.
	@task(3)
	def logout_login(self):
		if self.token is None: return
		with self.client.post('api/auth/logout',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									json={},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Logout',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Logout failed, code: " + str(response.status_code))

		with self.client.get('api/auth',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Auth (old token)',
									catch_response=True) as response:
			if response.status_code == 401:
				response.success()
			else:
				response.failure("Get Auth after logout != 401, code: " + str(response.status_code))

		with self.client.get('api/auth/basic/login', 
										params={
											'email': self.username,
											'password': self.password
										}, 
										headers={
											'Authorization':'Basic ' + str(base64.b64encode(self.username+':'+self.password))
										}, 
										timeout=MAX_WAIT_TIME_SECONDS, 
										name='Login', catch_response=True) as response:

			if response.status_code == 200:
				self.token = response.headers['x-access-token']
			else:
				#This will prevent any more requests by hatchling
				#Maybe we should raise some error to stop this hatchling.
				#Or somehow recover from this.
				self.token = None 
				response.failure("Login failed, code: " + str(response.status_code))

	'''
	API: /routes/board.js
	'''

	@task(5)
	def post_board(self):
		if self.token is None: return
		if len(self.boards) >= MAX_BOARDS: return

		with self.client.post('api/boards',
								json = {
										'background': 'NONE',
                              		  	'size': {
                               		        'width': random.randint(5, 20),
                                    		'height': random.randint(5, 20)
                               		 	}
            					},
								headers = {
										'Authorization': 'Bearer ' + self.token
								}, name='Board Create', catch_response=True) as response:

			if response.status_code is 201:
				newboard = response.json()
				newboard['tickets'] = [ ]
				self.boards[newboard['id']] = newboard;
				with self.client.post('api/boards/'+newboard["id"]+'/access',
									headers = {
											'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board Share',
									catch_response=True) as shareresponse:
					if shareresponse.status_code == 200:
						sharedboards[newboard['id']] = shareresponse.json()['accessCode']
						print 'http://sut-cb.n4sjamk.org/boards/' + newboard["id"] + '/access/' + shareresponse.json()["accessCode"]
					else:
						shareresponse.failure("Share board failed, code: " + str(shareresponse.status_code))
			else:
				response.failure("Board creation failed, code: " + str(response.status_code))


	@task(5)
	def get_board_byid(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		with self.client.get('api/boards/' + board['id'],
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board Get Single',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Getting board by id failed, code " + str(response.status_code))

	@task(5)
	def get_board(self):
		if self.token is None: return

		with self.client.get('api/boards/',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board Get All',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Getting boards failed, code " + str(response.status_code))

	@task(10)
	def edit_board(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		background = random.choice(BACKGROUND)

		with self.client.put('api/boards/' + board['id'] +'',
									json = {
                               				'id': board,
                               				'name':'',
                               				'background': background,
                               				'customBackground': '',
                               				'size':
                                       			{'width':random.randint(2, 40),'height':random.randint(2, 40)}
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='Board Edit',
       								catch_response=True) as response:

			if response.status_code == 200:
				newdata = response.json()
				newdata['tickets'] = board['tickets']
				self.boards[board['id']] = newdata
			else:
				response.failure("Board edit failed, code: " + str(response.status_code))

	@task(2)
	def delete_board(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]

		with self.client.delete('api/boards/' + board['id'] +'',
									json = {
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='Board Delete',
       								catch_response=True) as response:

			if response.status_code == 200:
				del self.boards[board['id']]
			else:
				response.failure("Board remove failed, code: " + str(response.status_code))
	
	@task(3)
	def export_board(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		format = random.choice(EXPORT_FORMAT)
		with self.client.get('api/boards/' + board['id'] + '/export',
									params={
										'format': format
									},
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board export as ' + format,
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Export failed, code " + str(response.status_code))

	@task(5)
	def get_board_tickets(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		with self.client.get('api/boards/' + board['id'] + '/tickets',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board Get Tickets',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Getting board tickets failed, code " + str(response.status_code))

	@task(20)
	def post_ticket(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		with self.client.post('api/boards/' + board['id'] + '/tickets',
									json = {
                               				'id': 'dirty_newticket',
                               				'position':
                                       			{'x': random.randint(1, board['size']['width'])*192,'y':random.randint(1, board['size']['height'])*108, 'z': 0},
                                       		'color': random.choice(COLOR)
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='Ticket Create', 
       								catch_response=True) as response:
			if response.status_code == 201:
				board['tickets'].append(response.json())
			else:
				response.failure("Creating new ticket failed, code: " + str(response.status_code)) 

	@task(20)
	def move_ticket(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		if len(board['tickets']) is 0: return

		ticket = random.choice(board['tickets'])
		
		with self.client.put('api/boards/' + board['id'] + '/tickets/' + ticket['id'],
									json = {
                               				'id': ticket['id'],
                               				'position':
                                       			{
                                       				'x': random.randint(1, board['size']['width'])*192,
                                       				'y':random.randint(1, board['size']['height'])*108, 
                                       				'z': 0
                                       			}
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								}
       								,
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='Ticket Move',
       								catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Failed to move ticket, code: " + str(response.status_code))

	@task(15)
	def modify_content(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		if len(board['tickets']) is 0: return

		ticket = random.choice(board['tickets'])
		
		with self.client.put('api/boards/' + board['id'] + '/tickets/' + ticket['id'],
									json = {
                               				'id': ticket['id'],
                               				'content': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(50)),
                               				'heading': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15)),
                       						'color': random.choice(COLOR)
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS ,
       								name='Ticket Modify Content',
       								catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Ticket modify failed, code: " + str(response.status_code))

	@task(4)
	def delete_ticket(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		if len(board['tickets']) is 0: return

		ticket = random.choice(board['tickets'])
		
		with self.client.delete('api/boards/' + board['id'] + '/tickets/' + ticket['id'],
									json = {
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								}, 
									timeout=MAX_WAIT_TIME_SECONDS,
       								name='Ticket Delete',
       								catch_response=True) as response:
			if response.status_code == 200:
				board['tickets'].remove(ticket)
			else:
				response.failure("Ticket deletion failed, code: " + str(response.status_code))

	@task(15)
	def comment_ticket(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		if len(board['tickets']) is 0: return

		ticket = random.choice(board['tickets'])
		
		with self.client.post('api/boards/' + board['id'] + '/tickets/' + ticket['id'] + '/comments',
									json = {
                               				'comment': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(200))
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='Ticket Comment',
       								catch_response=True) as response:
			if response.status_code != 201:
				response.failure("Ticket comment failed, code: " + str(response.status_code))

	@task(1)
	def get_board_events(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = self.boards[random.choice(self.boards.keys())]
		with self.client.get('api/boards/' + board['id'] + '/events',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Board Get Events',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Getting board events failed, code " + str(response.status_code))

	## TODO: Access get and delete
	## Access is actually done in startup

	@task(2)
	def edit_user(self):
		if self.token is None: return		
		with self.client.put('api/user/edit',
									json = {
                               				'name': ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10)),
                               				'avatar': random.choice(AVATAR)
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='User Edit',
       								catch_response=True) as response:
			if response.status_code != 200:
				response.failure("User edit failed, code: " + str(response.status_code))

	@task(1)
	def edit_user_password(self):
		if self.token is None: return
		newpass = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))
		with self.client.put('api/user/changepw',
									json = {
                               				'old_password': self.password,
                               				'new_password': newpass
                       				},
                       				headers = {
                          					'Authorization': 'Bearer ' + self.token
       								},
       								timeout=MAX_WAIT_TIME_SECONDS,
       								name='User Password Change',
       								catch_response=True) as response:
			if response.status_code == 200:
				self.password = newpass
			else:
				response.failure("User password change failed, code: " + str(response.status_code))

	'''
	API: /routes/version.js
	'''
	@task(2)
	def version_img(self):
		if self.token is None: return

		with self.client.get('api/version/img',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Version Img',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Version img failed, code: " + str(response.status_code))

	@task(2)
	def version_api(self):
		if self.token is None: return

		with self.client.get('api/version/api',
									headers = {
										'Authorization': 'Bearer ' + self.token
									},
									timeout=MAX_WAIT_TIME_SECONDS,
									name='Version Api',
									catch_response=True) as response:
			if response.status_code != 200:
				response.failure("Version api failed, code: " + str(response.status_code))

#DEFINE TASKSETS
class TeamboardUser(HttpLocust):
        weight = 10
        task_set = TeamboardTasks
        min_wait = 1000
        max_wait = 3000
