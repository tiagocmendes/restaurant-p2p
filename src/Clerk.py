import time
import pickle
import socket
import random
import logging
import argparse
import threading
import uuid

from ringNode import RingNode
from utils import recv, send, work, choose_node


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

logger = logging.getLogger('Clerk')


class Clerk(threading.Thread):
    def __init__(self, ring_port, ring_size, timeout, port = 5001, ide = 1):
        threading.Thread.__init__(self)
        self.name ='Clerk'
        self.id = ide
        self.port = port
        self.ring_addr = ('localhost', ring_port)
        if self.port == ring_port:
            self.ring_addr = None
        self.ring_size = ring_size

        # Create a logger for the clerk
        self.logger = logging.getLogger('SIMU - (' + str(self.id) + ') ' + self.name)
        self.logger.setLevel(logging.INFO)

        # Start communication thread
        self.comm_thread = RingNode(self.name, self.id, ('localhost', self.port), self.ring_size, self.ring_addr, timeout)
        self.comm_thread.start()

    def run(self):
        # socket to give clients a ticket number for their order
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(3)
        client_socket.bind(('localhost', self.port + 100))

        # get entities table
        entities_table = self.comm_thread.get_nodes_table()
        while entities_table is None:
                entities_table = self.comm_thread.get_nodes_table()
                work(0.5)
        
        self.logger.info('Entities table: %s', entities_table)

        # all orders
        #orders = {}

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
                self.logger.info('Received client request: %s', method)

                if o['method'] == 'ORDER':
                    self.logger.info('Order: %s', o['args'])
                    # ticket number to identify client order
                    ticket_no = str(uuid.uuid4())
                    
                    order = o['args']
                    #orders[ticket_no] = order
                    
                    # send cook order to chef
                    args = {}
                    args['client_addr'] = addr
                    args['order'] = order
                    args['ticket_no'] = ticket_no
                    args['id'] = choose_node('Chef', entities_table)
                    self.logger.info('Sending cook order to one Chef')
                    self.comm_thread.put_send_requests({'method': 'COOK_ORDER', 'args': args})

                    # send ticket number back to the client
                    self.logger.info('Ticket number: %s', ticket_no)
                    args = {'ticket_no': ticket_no, 'order': order}
                    send(client_socket, addr, {'method': 'ORDER_REP', 'args': args})
                
                elif method == 'PICKUP':
                    args = {}
                    args['client_addr'] = addr
                    args['order'] = o['args']['order']
                    args['ticket_no'] = o['args']['ticket_no']
                    args['id'] = entities_table['Waiter'][0]
                    self.logger.info('Forwarding pickup request to Waiter')
                    self.comm_thread.put_send_requests({'method':'CLIENT_PICKUP', 'args': args})
                    
            else:
                try:
                    self.logger.debug('Getting received request')
                    request = self.comm_thread.get_recv_requests()
                    if request is None:
                        work(0.5)
                        continue
                except:
                    self.logger.debug('Error getting received request')
                    continue

                if request is not None:
                    self.logger.debug('Request %s', request)

                    # Wait for a random time
                    delta = random.gauss(2, 0.5)
                    self.logger.info('Wait for %f seconds', delta)
                    work(delta)
                    
                    if request['method'] == 'CLIENT_ORDER':
                        # ticket number to identify client order
                        ticket_no = str(uuid.uuid4())

                        client_addr = request['args']['client_addr']
                        order = request['args']['order']
                        #orders[ticket_no] = order
                        
                        # send cook order to chef
                        self.logger.info('Sending cook order to one Chef')
                        args = {}
                        args['client_addr'] = client_addr
                        args['order'] = order
                        args['ticket_no'] = ticket_no
                        args['id'] = choose_node('Chef',entities_table)
                        self.comm_thread.put_send_requests({'method': 'COOK_ORDER', 'args': args})

                        # send ticket number back to the client
                        self.logger.info('Ticket number: %s', ticket_no)
                        args = {'ticket_no': ticket_no, 'order': order}
                        send(client_socket, client_addr, {'method': 'ORDER_REP', 'args': args})
                