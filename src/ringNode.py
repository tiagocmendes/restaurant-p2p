import logging
import pickle
import queue
import socket
import threading
from utils import contains_successor, work

class RingNode(threading.Thread):
    def __init__(self, name, identification, address, ring_size, ring_addr = None, timeout = 3):
        threading.Thread.__init__(self)
        
        # basic properties
        self.name = name
        self.id = identification
        self.address = address
        
        # token ring properties
        self.ring_size = ring_size
        self.ring_addr = ring_addr
        self.nodes_table = {self.name: [self.id]}
        self.token_turn = 0

        # queues to store received requests and requests to be sent
        self.recv_requests = queue.Queue()
        self.send_requests = queue.Queue()

        # check if 'self' is the first node in the ring
        if ring_addr is None:
            self.successor_id = self.id
            self.successor_addr = self.address
            self.inside_token_ring = True
            self.initial_entity = True
        else:
            self.successor_id = None
            self.successor_addr = None
            self.inside_token_ring = False
            self.initial_entity = False
        
        self.socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)

        # Create a logger for this node
        self.logger = logging.getLogger('COMM - (' + str(self.id) + ') ' + self.name)
        self.logger.setLevel(logging.INFO)

    
    def send(self, address, o):
        # self.logger.debug('Sending %s to %s', o, address)
        p = pickle.dumps(o)
        self.socket.sendto(p, address)
    
    def recv(self):
        try:
            p, addr = self.socket.recvfrom(1024)
        except socket.timeout:
            return None, None
        else:
            if len(p) == 0:
                return None, addr
            else:
                return p, addr
    
    # get nodes table in 'self' perspective
    def get_nodes_table(self):
        total_size = 0
        for key, value in self.nodes_table.items():
            total_size += len(value)

        if total_size == self.ring_size:
            return self.nodes_table

    # used by simulation thread
    def get_recv_requests(self):
        self.logger.debug('Get received request')
        if self.recv_requests.qsize() != 0:
            return self.recv_requests.get()
        else:
            return None

    # used by communication thread
    def put_recv_requests(self, o):
        self.logger.debug('Put received request: %s', o)
        self.recv_requests.put(o)

    # used by communication thread
    def get_send_requests(self):
        self.logger.debug('Get request to be sent')
        if self.send_requests.qsize() != 0:
            return self.send_requests.get()

    # used by simulation thread
    def put_send_requests(self, o):
        self.logger.debug('Put request to be sent: %s', o)
        self.send_requests.put(o)

    def node_discovery(self, args):
        token_entity_table=args['args']['args']

        if self.name in token_entity_table:
            temp=token_entity_table[self.name]
            if self.id not in temp:
                temp.append(self.id)
            token_entity_table[self.name]=temp
        else:
            token_entity_table[self.name]=[self.id]


        self.nodes_table = token_entity_table
        self.logger.info('NODE_DISCOVERY - My Table of Nodes: %s', self.nodes_table)
        args['args']['args']=token_entity_table
        

        self.send(self.successor_addr,args)
    
    def entity_join(self, args):
        
        identification = args['id']
        address = args['address']

        self.logger.info('NODE_JOIN - Request from ID: %s; Address: %s;', identification, address)

        if self.id == self.successor_id:
            self.successor_id = identification
            self.successor_addr = address
            args = {'successor_id': self.id, 'successor_addr': self.address}
            self.logger.info('NODE_JOIN - Successor: %s; Address: %s', self.successor_id, self.successor_addr)
            self.send(address,{'method': 'NODE_JOIN_REP', 'args': args})
        elif contains_successor(self.id, self.successor_id, identification):
            args = {'successor_id': self.successor_id, 'successor_addr': self.successor_addr}
            self.successor_id = identification
            self.successor_addr = address
            self.logger.info('NODE_JOIN - Successor: %s; Address: %s', self.successor_id, self.successor_addr)
            self.send(address, {'method': 'NODE_JOIN_REP', 'args': args})
        else:
            self.logger.debug('NODE_JOIN - Find Successor (id = %s)', identification)
            self.send(self.successor_addr, {'method': 'NODE_JOIN_REQ', 'args': args})
    
    def run(self):
        # node binding to itself
        self.logger.info('NODE_JOIN - Binding to address %s', self.address)
        try:
            self.socket.bind(self.address)
        except socket.error as msg:
            self.logger.info('Error binding to address %s: %s', self.address, msg)

        # initial entity sends a token to check if the ring is complete
        if self.initial_entity:
            o = {'method': 'TOKEN', 'args': {'method': 'RING_COUNT', 'args': 1}}
            self.logger.info('NODE_JOIN - Current ring size: %s', 1)
            self.send(self.successor_addr, o)

        while not self.inside_token_ring:
            # token ring join message
            o = {'method': 'NODE_JOIN_REQ', 'args': {'id': self.id, 'address': self.address}}
            self.logger.info('NODE_JOIN - Sending NODE_JOIN request')
            # send to the initial token ring node
            self.send(self.ring_addr, o)
            # block the program execution until receiving a message
            p, addr = self.recv()

            if p is not None:
                o = pickle.loads(p)
                if o['method'] == 'NODE_JOIN_REP':
                    self.logger.debug('NODE_JOIN - Received NODE_JOIN response')
                    args = o['args']
                    self.successor_id = args['successor_id']
                    self.successor_addr = args['successor_addr']
                    self.inside_token_ring = True
                    self.logger.info('NODE_JOIN - Joined Token-Ring - Successor: %s; Address: %s', self.successor_id, self.successor_addr)
       
        done = False
        while not done:
            p, addr = self.recv()
            if p is not None:
                o = pickle.loads(p)
                self.logger.debug('Received "O": %s', o)
                if o['method'] == 'NODE_JOIN_REQ':
                    self.entity_join(o['args'])

                # Token methods
                if o['method'] == 'TOKEN':
                    if o['args']['method'] == 'RING_COUNT':
                        self.logger.debug('NODE_JOIN - Current ring size: %s', o['args']['args'])
                        # check if the token returns to the initial entity
                        if self.initial_entity:
                            # check if the ring is complete
                            if o['args']['args'] == self.ring_size: 
                                self.logger.info('NODE_JOIN process COMPLETED')
                                self.logger.info('NODE_DISCOVERY process STARTED')
                                self.logger.info('NODE_DISCOVERY - My Table of Nodes: %s', self.nodes_table)
                                self.token_turn += 1
                                o = {'method': 'TOKEN', 'args': {'method':'NODE_DISCOVERY', 'args': self.nodes_table}} 
                            else:
                                # reset the ring size counter
                                o['args']['args'] = 1
                        else:
                            o['args']['args'] += 1
                        self.send(self.successor_addr, o)
                    elif o['args']['method'] == 'NODE_DISCOVERY':
                        # local variable that is incremented everytime this message arrives
                        self.token_turn += 1
                        # in the second time, the node discovery process is complete
                        if self.token_turn > 2:
                            o = {'method': 'TOKEN', 'args': {'method':None, 'args':None}}
                            self.logger.info('NODE_DISCOVERY process COMPLETED')
                            self.logger.info('SIMULATION process STARTED')
                            self.send(self.successor_addr, o)
                        else:
                            # continue node discovery process
                            self.node_discovery(o)

                    elif o['args']['method'] == None:
                        p = self.get_send_requests()
                        
                        if p is not None:
                            self.logger.debug('Send": %s', p)
                            o= {'method': 'TOKEN', 'args': p}
                        self.send(self.successor_addr,o)
                    else:
                        received_id = o['args']['args']['id']
                        received_req = o['args']
                        
                        if self.id == received_id:
                            # put received requests in a queue for the simulation thread
                            self.put_recv_requests(received_req)
                            p=self.get_send_requests()
                            if p is not None:
                                self.logger.debug('Send: %s', p)
                                o = {'method': 'TOKEN', 'args': p}
                            else:
                                o = {'method': 'TOKEN', 'args': {'method':None, 'args':None}}

                        self.send(self.successor_addr, o)
                    
    def __str__(self):
        return 'Name: {}; ID: {}; Address: {}; Successor: {}'\
            .format(self.name, self.id, self.address, self.successor_addr)

    def __repr__(self):
        return self.__str__()