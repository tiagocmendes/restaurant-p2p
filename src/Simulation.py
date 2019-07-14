# coding: utf-8

import argparse
import logging
import random
import time
import client
from Chef import Chef
from Waiter import Waiter
from Clerk import Clerk
from Restaurant import Restaurant

# configure the log with DEBUG level
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')


def main(access_port, no_clients, timeout,ft=0, r = 0):
    # logger for the main
    logger = logging.getLogger('Token Ring')

    first_entity = 0
    if r == 1:
        first_entity = ft
    # initial node (Restaurant)
    restaurant_node = Restaurant(5000 + first_entity,4,3)
    restaurant_node.start()
    
    # Clerk
    clerk_node = Clerk(5000 + first_entity,4,3)
    clerk_node.start()

    # Chef
    chef_node_1 = Chef(5000 + first_entity, 4,3)
    #chef_node_2 = Chef(5000 + first_entity, 5, 3, 5004, 4)

    chef_node_1.start()
    #chef_node_2.start()
    
    # Waiter
    waiter_node=Waiter(5000 + first_entity, 4, 3)
    waiter_node.start()
    
    # Clients
    #for i in range(no_clients):
    #    client_node = client.main(5005 + i,('localhost', access_port + first_entity), timeout)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulation argument parser')
    parser.add_argument('-a', dest='access_port', type=int, help='access port', default = 5100)
    parser.add_argument('-c', dest='no_clients', type=int, help='number of clientes', default = 1)
    parser.add_argument('-t', dest='timeout', type=int, help='clients timeout', default = 300)
    parser.add_argument('-ft', dest='first_entity', type=int, help='first entity', default = 0)
    parser.add_argument('-r', dest='random', type=int, help='random access port', default = 0)
    args = parser.parse_args()
    main(args.access_port, args.no_clients, args.timeout,args.first_entity, args.random)
