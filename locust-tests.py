from os     import urandom
from locust import HttpLocust, TaskSet, task

import json
import random
shared = [ ]
COLOR = ['#4F819A','#724A7F','#DCC75B','#EB584A']
BACKGROUND= ['SWOT','PLAY','SCRUM','KANBAN','KEEP_DROP_TRY','NONE','CUSTOMER_JOURNEY_MAP','BUSINESS_MODEL_CANVAS']
class jarmo(TaskSet):

	@task(90)
        def change_background(self):
                background = random.choice(BACKGROUND)
                response = self.client.put('api/boards/55812f4b38a6dd23002181b2',
                        data = json.dumps({
                                'id': '55812f4b38a6dd23002181b2',
                                'name':'',
                                'background': background,
				'customBackground': '',
                                'size':
					{'width':10,'height':10}


                        }),
                        headers = {
				'content-type':  'application/json',
                                'authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjU0NjFkZmEyOTA1YmMxMGYwMGE5NGYxZSIsInR5cGUiOiJ1c2VyIiwidXNlcm5hbWUiOiJhYmNAYWJjLmFiYyIsImlhdCI6MTQzNDUyOTYwOX0.gVDdrqH7taDfCON0PNGEsXaGLYfVlcysClzgPenesGQ'
        })
                print response








class TeamboardTasks(TaskSet):

	def on_start(self):
		self.boards  = [ ]
		self.tickets = [ ]
		self.accessCode = {}
		self.x_token = {} 

		self.user = {
			'email': 'test_' + urandom(16).encode('hex') + '@garnet.red',
			'passwordRegister': 'test_password',
			'passwordAgain': 'test_password',
			'password': 'test_password'
		}
		self.token = None

		self.client.post('api/auth/register', self.user)

	#@task(1)
	#def login(self):
		response   = self.client.post('api/auth/login', self.user)
		self.token = response.headers['x-access-token']
             

	@task(1)
	def post_board(self):
		if self.token is None: return
                if len(self.boards) > 1: return
		response = self.client.post('api/boards',
			data = {
				'name':     'Botti vauhdissa',
			},
			headers = {
				
				'authorization': 'bearer ' + self.token + ''
			})
		self.boards.append(response.json())

	@task(2)
	def get_board(self):
		if self.token is None: return
		if len(self.boards) is 0: return

		board = random.choice(self.boards)
		self.client.get('api/boards/' + board['id'] + '',
			headers = {
				'authorization': 'bearer ' + self.token + ''
			})
	@task(90)
	def share_board(self):
		if self.token is None: return
                if len(self.boards) is 0: return
		if len(shared) >0: return 
		board = random.choice(self.boards)
		if board['id'] in self.accessCode: return
		


		response = self.client.post('api/boards/' + board['id'] + '/access',
			headers = {
                                'authorization': 'bearer ' + self.token + ''
                        })


		accessCode = response.json()
		self.accessCode[board['id']] = {
			'accessCode': accessCode['accessCode']
		}
		shared.append({
			'boardid': board['id'],
                        'accessCode': accessCode['accessCode']
                })

		print self.client.base_url + 'boards/' + board['id'] + '/access/' + accessCode['accessCode']


	@task(1)
	def join_board(self):
		if len(shared) == 0: return
		target = random.choice(shared)
		if target['boardid'] in self.x_token: return
		
		response = self.client.post('api/boards/' + target['boardid'] + '/access/' + target['accessCode'])
		self.x_token[target['boardid']] = {'x-access-token': response.headers['x-access-token'],'tickets':[]}


	@task(4)
	def create_guest_tickets(self):
		if len(self.x_token) == 0: return
		target_boardid = random.choice(self.x_token.keys())
		target_access = self.x_token[target_boardid]['x-access-token']
		#if len(self.x_token[target_boardid]['tickets']) > 5: return
		color = random.choice(COLOR)
		response = self.client.post('api/boards/' + target_boardid + '/tickets',
			data = {
				'heading': 'Liikuteltavaa2',
                                'content': 'sisaltoa2',
                                'color': color
                        },
                        headers = {
                                'authorization': 'bearer ' + target_access + ''
                        })
		ticket = response.json()
		if 'id' not in ticket:
			print ticket
			return
                self.x_token[target_boardid]['tickets'].append(
                        ticket['id']
                )


	@task(20)
        def move_guest_ticket(self):
                
                if len(self.x_token) == 0: return

                target_boardid = random.choice(self.x_token.keys())
                target_access = self.x_token[target_boardid]['x-access-token']
		tickets = self.x_token[target_boardid]['tickets']
		if len(tickets) == 0: return
		target_ticket = random.choice(tickets)


                response = self.client.put('api/boards/' + target_boardid + '/tickets/' +
                                target_ticket + '',
                        data = json.dumps({
                                'position': {
                                        'x': random.randint(0, 1000),
                                        'y': random.randint(0, 800),
                                        
                                }
                        }),
                        headers = {
                                'content-type':  'application/json',
                                'authorization': 'bearer ' + target_access + ''
                        })
	########
	@task(90)
        def export(self):
                if len(self.x_token) == 0: return
		if self.token is None: return
                target_boardid = random.choice(self.x_token.keys())
                board = random.choice(self.boards)
		target_access = self.x_token[target_boardid]['x-access-token']
                #if len(self.x_token[target_boardid]['tickets']) > 5: return
                
                self.client.post('api/boards/' + board['id'] + '/export?access_token=' + self.token +'&format=image')

                

	########

	@task(90)
        def change_background(self):
		if self.token is None: return
                if len(self.boards) is 0: return
                #if len(shared) >0: return
		board = random.choice(self.boards)
                #if board['id'] in self.accessCode: return
                
                #target_access = self.x_token[target_boardid]['x-access-token']
                #if len(self.x_token[target_boardid]['tickets']) > 5: return
		background = random.choice(BACKGROUND)
                response = self.client.put('api/boards/' + board['id'] +'',
                        data = json.dumps({
                                'id': board,
                                'name':'',
                                'background': background,
                                'customBackground': '',
                                'size':
                                        {'width':10,'height':10}


                        }),

                        headers = {
				'content-type':  'application/json',
                                'authorization': 'Bearer ' + self.token + ''
        })
		
		#print response
			

class TeamboardUser(HttpLocust):
        weight = 10
        task_set = TeamboardTasks
        min_wait = 100
        max_wait = 200


class jarmo(HttpLocust):
	weight = 10
        task_set = jarmo
        min_wait = 1000
        max_wait = 2000
