from os     import urandom
from locust import HttpLocust, TaskSet, task

import json
import random
shared = [ ]
COLOR = ['#4F819A','#724A7F','#DCC75B','#EB584A']
class TeamboardTasks(TaskSet):

	def on_start(self):
		self.boards  = [ ]
		self.tickets = [ ]
		self.accessCode = {}
		self.x_token = {} 

		self.user = {
			'email':    'test_' + urandom(16).encode('hex') + '@garnet.red',
			'password': 'test_password'
		}
		self.token = None

		self.client.post('/auth/register', self.user)

	#@task(1)
	#def login(self):
		response   = self.client.post('/auth/login', self.user)
		self.token = response.headers['x-access-token']
             

	@task(1)
	def post_board(self):
		if self.token is None: return
                if len(self.boards) > 1: return
		response = self.client.post('/boards',
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
		self.client.get('/boards/' + board['id'] + '',
			headers = {
				'authorization': 'bearer ' + self.token + ''
			})
	@task(1)
	def share_board(self):
		if self.token is None: return
                if len(self.boards) is 0: return
		if len(shared) >0: return 
		board = random.choice(self.boards)
		if board['id'] in self.accessCode: return
		


		response = self.client.post('/boards/' + board['id'] + '/access',
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

		print self.client.base_url + '/board/' + board['id'] + '/access/' + accessCode['accessCode']


	@task(1)
	def join_board(self):
		if len(shared) == 0: return
		target = random.choice(shared)
		if target['boardid'] in self.x_token: return
		
		response = self.client.post('/boards/' + target['boardid'] + '/access/' + target['accessCode'])
		self.x_token[target['boardid']] = {'x-access-token': response.headers['x-access-token'],'tickets':[]}


	@task(5)
	def create_guest_tickets(self):
		if len(self.x_token) == 0: return
		target_boardid = random.choice(self.x_token.keys())
		target_access = self.x_token[target_boardid]['x-access-token']
		color = random.choice(COLOR)
		response = self.client.post('/boards/' + target_boardid + '/tickets',
			data = {
                                'content': 'sisaltoa2',
                                'color': color
                        },
                        headers = {
                                'authorization': 'bearer ' + target_access + ''
                        })
		ticket = response.json()
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


                response = self.client.put('/boards/' + target_boardid + '/tickets/' +
                                target_ticket + '',
                        data = json.dumps({
                                'position': {
                                        'x': random.randint(0, 712),
                                        'y': random.randint(0, 556),
                                        
                                }
                        }),
                        headers = {
                                'content-type':  'application/json',
                                'authorization': 'bearer ' + target_access + ''
                        })


			

class TeamboardUser(HttpLocust):
        weight = 10
        task_set = TeamboardTasks
        min_wait = 1000
        max_wait = 2000


