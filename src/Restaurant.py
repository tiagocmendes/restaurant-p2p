import argparse
import configparser
import logging
import time
import socket
import pickle
import threading
import queue
import random
from utils import work, send, recv
from random import gauss
from ringNode import RingNode
from threading import Thread

# configure the log with INFO level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

logger = logging.getLogger('Restaurant')

# abstract class 
class Equipment:
    def __init__(self, mean, std_deviation):
        self.mean = mean
        self.std_deviation = std_deviation
    
    def equipment_action(self):
        work_time = gauss(self.mean, pow(self.std_deviation, 2))
        # chef will sleep for a random time, simulating items preparation
        return work_time     

# BarbecueGrill extends Equipment
class BarbecueGrill(Equipment):
    def __init__(self, config):
        mean = config.getint('BARBECUE_GRILL','MEAN') 
        std_deviation = config.getfloat('BARBECUE_GRILL','STD_DEVIATION') 
        Equipment.__init__(self, mean, std_deviation)

    def to_grill(self):
        return Equipment.equipment_action(self)

# Bar extends Equipment
class Bar(Equipment):
    def __init__(self, config):
        mean = config.getint('BAR','MEAN') 
        std_deviation = config.getfloat('BAR','STD_DEVIATION') 
        Equipment.__init__(self, mean, std_deviation)

    def prepare_drink(self):
        return Equipment.equipment_action(self)

# Fryer extends Equipment
class Fryer(Equipment):
    def __init__(self, config):
        mean = config.getint('FRYER','MEAN') 
        std_deviation = config.getfloat('FRYER','STD_DEVIATION')
        Equipment.__init__(self, mean, std_deviation)
    
    def to_fry(self):
        return Equipment.equipment_action(self)


class Restaurant(threading.Thread):
    def __init__(self, ring_port, ring_size, timeout, port = 5000, ide = 0):
        threading.Thread.__init__(self)
        self.name = 'Drive-Through'
        self.id = ide
        self.port = port
        self.ring_addr = ('localhost', ring_port)
        if self.port == ring_port:
            self.ring_addr = None
        self.ring_size = ring_size

        # holds the order that is beeing cooked and decrements its value 
        self.fryer_order = queue.Queue()
        self.bar_order = queue.Queue()
        self.barbecue_grill_order = queue.Queue()

        # flags to know if a certain kitchen equipment is beeing used
        self.using_fryer = None 
        self.using_bar = None 
        self.using_barbecue_grill = None 

        # Create a logger for the clerk
        self.logger = logging.getLogger('SIMU - (' + str(self.id) + ') ' + self.name)
        self.logger.setLevel(logging.INFO)

        # Start communication thread
        self.comm_thread = RingNode(self.name, self.id, ('localhost', self.port), self.ring_size, self.ring_addr, timeout)
        self.comm_thread.start()

    def run(self):
        # load the configuration file
        config = configparser.ConfigParser()
        config.read('../config.ini')
        
        # socket for receiving clients requests
        client_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(3)
        client_socket.bind(('localhost', self.port + 100)) # client_port = port + 100

        # create kitchen equipments
        barbecue_grill = BarbecueGrill(config)
        fryer = Fryer(config)
        bar = Bar(config)

        
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
                if method == 'ORDER':
                    self.logger.info('Order: %s', o['args'])
                    self.logger.info('Forwarding ORDER request to Clerk')
                    args = {'client_addr': addr,'order': o['args'], 'id': entities_table['Clerk'][0]}
                    o = {'method':'CLIENT_ORDER', 'args': args}
                    self.comm_thread.put_send_requests(o)
                if method == 'PICKUP':
                    self.logger.info('Forwarding PICKUP request to Waiter')
                    args = {'client_addr':addr,'order': o['args']['order'],'ticket_no': o['args']['ticket_no'], 'id': entities_table['Waiter'][0]}
                    o = {'method':'CLIENT_PICKUP', 'args': args}
                    self.comm_thread.put_send_requests(o)
            else:
                request = self.comm_thread.get_recv_requests()
                
                if request is not None:
                    self.logger.debug('Request %s', request)
                    
                    client_addr = request['args']['client_addr']
                    ticket_no = request['args']['ticket_no']
                    from_id = request['args']['from']

                    # check witch kitchen equipment is beeing requested
                    if request['method'] == 'REQUEST_BARBECUE_GRILL':
                        if self.using_barbecue_grill is None:
                            self.logger.info('Barbecue grill request by Chef %s', from_id)
                            time = barbecue_grill.to_grill()
                            args = {'equipment': 'barbecue_grill','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id}
                            o = {'method': 'COOK_TIME', 'args': args}
                            self.using_barbecue_grill = from_id
                            self.comm_thread.put_send_requests(o)

                        else:
                            self.barbecue_grill_order.put({'client_addr':client_addr,'ticket_no':ticket_no,'id':from_id})
                    elif request['method'] =='REQUEST_FRYER':
                        if self.using_fryer is None:
                            self.logger.info('Fryer request by Chef %s', from_id)
                            time = fryer.to_fry()
                            args = {'equipment':'fryer','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id}
                            o = {'method': 'COOK_TIME', 'args': args}
                            self.using_fryer = from_id
                            self.comm_thread.put_send_requests(o)

                        else:
                            self.fryer_order.put({'client_addr':client_addr,'ticket_no':ticket_no,'id':from_id})

                    elif request['method'] =='REQUEST_BAR':
                        if self.using_bar is None:
                            self.logger.info('Bar request by Chef %s', from_id)
                            time = bar.prepare_drink()
                            args = {'equipment':'bar','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id}
                            o = {'method': 'COOK_TIME', 'args': args}
                            self.using_bar = from_id
                            self.comm_thread.put_send_requests(o)

                        else:
                            self.bar_order.put({'client_addr':client_addr,'ticket_no':ticket_no,'id':from_id})
                    
                    elif request['method'] == 'FREE_BARBECUE_GRILL':
                        if self.using_barbecue_grill == from_id:
                            # check if there are other barbecue grill requests
                            if self.barbecue_grill_order.qsize() != 0:
                                req = self.barbecue_grill_order.get()
                                client_addr = req['client_addr']
                                ticket_no = req['ticket_no']
                                from_id = req['id']
                                self.logger.info('Barbecue Grill request by Chef %s', from_id)
                                time = barbecue_grill.to_grill()
                                args = {'equipment':'barbecue_grill','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id,'olaaaa':'olaaa'}
                                o = {'method': 'COOK_TIME', 'args': args}
                                self.using_barbecue_grill = from_id
                                self.comm_thread.put_send_requests(o)

                            else:
                                self.logger.info('Barbecue Grill is free')
                                self.using_barbecue_grill = None
                        
                    elif request['method'] == 'FREE_FRYER':
                        if self.using_fryer == from_id:
                            # check if there are other fryer requests
                            if self.fryer_order.qsize() != 0:
                                req = self.fryer_order.get()
                                client_addr = req['client_addr']
                                ticket_no = req['ticket_no']
                                from_id = req['id']
                                self.logger.info('Fryer request by Chef %s', from_id)
                                time = fryer.to_fry()
                                args = {'equipment':'fryer','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id}
                                o = {'method': 'COOK_TIME', 'args': args}
                                self.using_fryer = from_id
                                self.comm_thread.put_send_requests(o)

                            else:
                                self.logger.info('Fryer is free')
                                self.using_fryer = None
                    elif request['method'] == 'FREE_BAR':
                        if self.using_bar == from_id:
                            if self.bar_order.qsize()!=0:
                                req=self.bar_order.get()

                                client_addr = req['client_addr']
                                ticket_no = req['ticket_no']
                                from_id=req['id']
                                time = bar.prepare_drink()
                                self.logger.info('Bar request by Chef %s', from_id)
                                args = {'equipment':'bar','time': time, 'client_addr': client_addr, 'ticket_no': ticket_no, 'id': from_id}
                                o = {'method': 'COOK_TIME', 'args': args}
                                self.using_bar = from_id
                                self.comm_thread.put_send_requests(o)

                            else:
                                self.logger.info('Bar is free')
                                self.using_bar = None