# coding: utf-8

import configparser
import time
import pickle
import socket
import random
import logging
import argparse
import threading
from ringNode import RingNode
from utils import work, send, recv


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')


class Waiter(threading.Thread):
    def __init__(self, ring_port, ring_size, timeout, port = 5003, ide = 3):
        threading.Thread.__init__(self)
        self.name = 'Waiter'
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

        # load the configuration file
        self.config = configparser.ConfigParser()
        self.config.read('../config.ini')

        # items price
        self.fries_price = self.config.getint('PRICE', 'FRIES')
        self.drink_price = self.config.getint('PRICE', 'DRINK')
        self.hamburger_price = self.config.getint('PRICE', 'HAMBURGER')
    
    # calculate total order cost
    def order_cost(self, order):
        # Wait for a random time
        delta = random.gauss(2, 0.5)
        self.logger.info('Calculating order cost for %f seconds', delta)
        work(delta)
        total_cost = order['fries'] * self.fries_price
        total_cost += order['drink'] * self.drink_price
        total_cost +=  order['hamburger'] * self.hamburger_price
        return total_cost
                

    def run(self):
        # socket for sending the finished request back to the client
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(3)
        client_socket.bind(('localhost', self.port + 100))

        # pending pickup orders
        pending_order = {}

        # get entities table
        entities_table = self.comm_thread.get_nodes_table()
        while entities_table is None:
                entities_table = self.comm_thread.get_nodes_table()
                work(0.5)
        
        self.logger.info('Entities table: %s', entities_table)

        done = False    
        while not done:
                # waiting for client pickup request
                p, addr = recv(client_socket)

                if p is not None:
                    # Wait for a random time
                    delta = random.gauss(2, 0.5)
                    self.logger.info('Wait for %f seconds', delta)
                    work(delta)
                    o = pickle.loads(p)

                    method = o['method']
                    self.logger.info('Received client request: %s', method)

                    if method == 'PICKUP':
                        ticket_no = o['args']['ticket_no']
                        self.logger.info('Client pickup request')
                        if ticket_no not in pending_order:
                            pending_order[ticket_no] = o['args']['order']

                    elif method == 'ORDER':
                        self.logger.info('Order: %s', o['args'])
                        self.logger.info('Forwarding ORDER request to Clerk')
                        to_send = {'method':'CLIENT_ORDER','args':{'client_addr':addr,'order':o['args'], 'id':entities_table['Clerk'][0]}}
                        self.comm_thread.put_send_requests(to_send)
                    
                else:

                    try:    
                        self.logger.debug('Getting received request')
                        recv_request = self.comm_thread.get_recv_requests()
                        if recv_request is None:
                            work(0.5)
                            continue
                    except:
                        self.logger.debug('Error getting received request')
                        continue

                    if recv_request is not None:
                        # Wait for a random time
                        delta = random.gauss(2, 0.5)
                        self.logger.info('Wait for %f seconds', delta)
                        work(delta)
                        
                        
                                
                        # token parsing
                        method = recv_request['method']
                        client_addr = recv_request['args']['client_addr']
                        ticket_no = recv_request['args']['ticket_no']

                        self.logger.info('Received %s request', method)

                        if method == 'CLIENT_PICKUP':
                            self.logger.info('Client pickup request')
                            order = recv_request['args']['order']
                            if ticket_no not in list(pending_order.keys()):
                                pending_order[ticket_no] = order
                        
                        elif method == 'ORDER_READY':
                            if ticket_no in list(pending_order.keys()):
                                order = pending_order[ticket_no]
                                del pending_order[ticket_no]
                                
                                # get order total cost
                                order_cost = self.order_cost(order)

                                self.logger.info('Payment request for order No. %s', ticket_no)
                                self.logger.info('Total cost: $%s', order_cost)
                                send(client_socket, client_addr, order_cost)

                                payed = False
                                while not payed:
                                    # waiting for client payment
                                    p, addr = recv(client_socket)

                                    if p is not None:
                                        o = pickle.loads(p)
                                        self.logger.info('Received payment amount of $%s', o['amount'])
                                        self.logger.info('Order ready: %s', order)
                                        self.logger.info('Sending finished order to client address: %s', client_addr)
                                        send(client_socket, client_addr, order)
                                        payed = True
            
