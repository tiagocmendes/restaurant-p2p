import time
import pickle
import socket
import random
import logging
import argparse
import threading
import queue
from ringNode import RingNode
from utils import recv, send, work


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

logger = logging.getLogger('Chef')

class Chef(threading.Thread):
    def __init__(self, ring_port, ring_size, timeout, port=5002, ide=2):
        threading.Thread.__init__(self)
        self.name = 'Chef'
        self.id = ide
        self.port = port
        self.ring_addr = ('localhost', ring_port)
        if self.port == ring_port:
            self.ring_addr = None
        self.ring_size = ring_size
        self.cook_order = queue.Queue()
        # holds the order that is beeing cooked
        self.currently_cooking = {} 

        # Create a logger for the clerk
        self.logger = logging.getLogger('SIMU - (' + str(self.id) + ') ' + self.name)
        self.logger.setLevel(logging.INFO)

        # Start communication thread
        self.comm_thread = RingNode(self.name, self.id, ('localhost', self.port), self.ring_size, self.ring_addr, timeout)
        self.comm_thread.start()

    def run(self):

        # socket for receiving clients requests
        client_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(3)
        client_socket.bind(('localhost', self.port + 100))  # client_port = port + 100

        # get entities table
        entities_table = self.comm_thread.get_nodes_table()
        while entities_table is None:
            entities_table = self.comm_thread.get_nodes_table()
            work(0.5)
        
        self.logger.info('Entities table: %s', entities_table)

        done = False
        while not done:

            # waiting for client order
            p, addr = recv(client_socket)

            if p is not None:

                # Wait for a random time
                delta = random.gauss(2, 0.5)
                self.logger.info('Wait for %f seconds', delta)
                work(delta)
                o = pickle.loads(p)
                
                method = o['method']
                self.logger.info('Request received: %s', method)

                # received client order
                if method == 'ORDER':
                    self.logger.info('Order: %s', o['args'])
                    to_send = {'method':'CLIENT_ORDER', 'args':{'client_addr':addr,'order':o['args'], 'id':entities_table['Clerk'][0]}}
                    self.comm_thread.put_send_requests(to_send)
                # received client request to pickup his order
                if method == 'PICKUP':
                    to_send = {'method':'CLIENT_PICKUP','args':{'client_addr':addr,'order':o['args']['order'],'ticket_no':o['args']['ticket_no'], 'id':entities_table['Waiter'][0]}}
                    self.comm_thread.put_send_requests(to_send)
            else:                
                self.logger.debug('Getting received request')
                recv_request = self.comm_thread.get_recv_requests()
                
                if recv_request is not None:
                    self.logger.debug('Request received %s', recv_request)

                    method = recv_request['method']
                    client_addr = recv_request['args']['client_addr']
                    ticket_no = recv_request['args']['ticket_no']

                    if method == 'COOK_ORDER':
                        self.logger.info('Cook order No. %s received', ticket_no)
                        
                        # not currently cooking
                        if not any(self.currently_cooking):
                            
                            order = recv_request['args']['order']

                            n_fries = 0
                            n_drink = 0
                            n_hamburger = 0
                            
                            if 'hamburger' in order:
                                n_hamburger = order['hamburger']

                            if 'fries' in order:
                                n_fries = order['fries']

                            if 'drink' in order:
                                n_drink = order['drink']

                            recv_request['args']['fries_cook'] = n_fries
                            recv_request['args']['hamburger_cook'] = n_hamburger
                            recv_request['args']['drink_cook'] = n_drink
                            
                            args = {}
                            args['client_addr'] = client_addr
                            args['ticket_no'] = ticket_no
                            args['id'] = entities_table['Drive-Through'][0]
                            args['from'] = self.id

                            self.currently_cooking[ticket_no] = recv_request['args']
                            
                            if n_hamburger != 0:
                                self.logger.info('Requesting Barbecue Grill')
                                o = {'method': 'REQUEST_BARBECUE_GRILL', 'args': args}
                            elif n_fries != 0:
                                self.logger.info('Requesting Fryer')
                                o = {'method': 'REQUEST_FRYER', 'args': args}
                            elif n_drink != 0:
                                self.logger.info('Requesting Bar')
                                o = {'method': 'REQUEST_BAR', 'args': args}

                            self.comm_thread.put_send_requests(o)
                        else:
                            self.cook_order.put(recv_request['args'])
                       
                    elif method == 'COOK_TIME':
                        # after requesting a certain kitchen equipment, chef is ready to cook
                        equipment = recv_request['args']['equipment']
                        ticket_no = recv_request['args']['ticket_no']
                        time = recv_request['args']['time']

                        if equipment == 'fryer':
                            self.logger.info('Using fryer for %s seconds', time)
                            self.currently_cooking[ticket_no]['fries_cook'] -= 1
                            args = {'client_addr': client_addr, 'ticket_no': ticket_no, 'id': entities_table['Drive-Through'][0],'from': self.id}
                            o = {'method': 'FREE_FRYER', 'args': args}

                        elif equipment == 'barbecue_grill':
                            self.logger.info('Using barbecue grill for %s seconds', time)
                            self.currently_cooking[ticket_no]['hamburger_cook'] -= 1
                            args = {'client_addr': client_addr, 'ticket_no': ticket_no, 'id': entities_table['Drive-Through'][0],'from': self.id}
                            o = {'method': 'FREE_BARBECUE_GRILL', 'args': args}

                        elif equipment == 'bar':
                            self.logger.info('Using bar for %s seconds', time)
                            self.currently_cooking[ticket_no]['drink_cook'] -= 1
                            args = {'client_addr': client_addr, 'ticket_no': ticket_no, 'id': entities_table['Drive-Through'][0],'from': self.id}
                            o = {'method': 'FREE_BAR', 'args': args}

                        # simulating work
                        work(time)
                        
                        self.comm_thread.put_send_requests(o)

                        # chef if the order is ready
                        drinks_left = self.currently_cooking[ticket_no]['drink_cook']
                        hamburgers_left = self.currently_cooking[ticket_no]['hamburger_cook']
                        fries_left = self.currently_cooking[ticket_no]['fries_cook']
                        
                        if drinks_left == 0 and hamburgers_left == 0 and fries_left == 0:
                            # Order is ready
                            self.logger.info('Order No. %s ready', ticket_no)
                            args = {'client_addr': client_addr, 'ticket_no': ticket_no, 'id': entities_table['Waiter'][0]}
                            o = {'method': 'ORDER_READY', 'args': args}
                            del self.currently_cooking[ticket_no]

                            # send to Waiter
                            self.comm_thread.put_send_requests(o)
                            
                            # start preparing the next order in the queue
                            if self.cook_order.qsize() != 0:
                                item = self.cook_order.get()
                                order = item['order']
                                client_addr = item['client_addr']
                                ticket_no = item['ticket_no']


                                n_fries = 0
                                n_drink = 0
                                n_hamburger = 0
                                
                                if 'hamburger' in order:
                                    n_hamburger = order['hamburger']

                                if 'fries' in order:
                                    n_fries = order['fries']
                                
                                if 'drink' in order:
                                    n_drink = order['drink']
                                
                                item['fries_cook'] = n_fries
                                item['hamburger_cook'] = n_hamburger
                                item['drink_cook'] = n_drink
                                
                                args={}
                                args['client_addr'] = client_addr
                                args['ticket_no'] = ticket_no
                                args['id'] = entities_table['Drive-Through'][0]
                                args['from'] = self.id

                                self.currently_cooking[ticket_no] = item
                                
                                if n_hamburger != 0:
                                    self.logger.info('Requesting Barbecue Grill')
                                    o = {'method': 'REQUEST_BARBECUE_GRILL', 'args': args}
                                elif n_fries != 0:
                                    self.logger.info('Requesting Fryer')
                                    o = {'method': 'REQUEST_FRYER', 'args': args}
                                elif n_drink != 0:
                                    self.logger.info('Requesting Bar')
                                    o = {'method': 'REQUEST_BAR', 'args': args}
                                
                                self.comm_thread.put_send_requests(o)

                        else:
                            # if order is not ready, continue requesting kitchen equipments
                            args = {'client_addr': client_addr, 'ticket_no': ticket_no, 'id': entities_table['Drive-Through'][0],'from':self.id}

                            if self.currently_cooking[ticket_no]['drink_cook'] != 0:
                                self.logger.info('Requesting Bar')
                                o = {'method': 'REQUEST_BAR', 'args': args}
                            elif self.currently_cooking[ticket_no]['hamburger_cook'] != 0:
                                self.logger.info('Requesting Barbecue Grill')
                                o = {'method': 'REQUEST_BARBECUE_GRILL', 'args': args}
                            elif self.currently_cooking[ticket_no]['fries_cook'] != 0:
                                self.logger.info('Requesting Fryer')
                                o = {'method': 'REQUEST_FRYER', 'args': args}

                            self.comm_thread.put_send_requests(o)