# coding: utf-8

import time
import pickle
import socket
import random
import logging
import argparse



 

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler('{0}/{1}.log'.format('./logs', 'simulation'), mode='w'),
                        logging.StreamHandler()
                    ])


def main(port, ring, timeout):
    # Create a logger for the client
    logger = logging.getLogger('SIMU - Client: '+str(port))
    

    # UDP Socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.bind(('localhost', port))

    # Wait for a random time
    delta = random.gauss(2, 0.5)
    logger.info('Wait for %f seconds', delta)
    time.sleep(delta)

    

    # Make a random request 
    requested_items = {'hamburger': 0, 'drink': 0, 'fries': 0}
    for i in range(random.randint(1,5)):
        item_id = random.randint(0,2)
        requested_items[list(requested_items)[item_id]] += 1
    
    # Request some food
    logger.info('Request some food...')
    p = pickle.dumps({'method': 'ORDER', 'args': requested_items})
    sock.sendto(p, ring) 

    # Wait for Ticket
    p, addr = sock.recvfrom(1024)
    o = pickle.loads(p)
    # Received message is: o['args'] = {'ticket_no': ticket_no, 'order': order}
    logger.info('Received ticket %s', o['args']['ticket_no'])

    # Pickup order 
    logger.info('Pickup order No. %s', o['args']['ticket_no'])
    p = pickle.dumps({"method": 'PICKUP', "args": o['args']})
    sock.sendto(p, ring)

    # Wait for payment request
    p, addr = sock.recvfrom(1024)
    o = pickle.loads(p)
    logger.info('Received total amount to pay: $%s', o)

    # Send payment
    logger.info('Sending payment with total amount of: $%s', o)
    p = pickle.dumps({'method': 'PAYMENT', 'amount': o})
    sock.sendto(p, addr)

    # Wait for payment request
    p, addr = sock.recvfrom(1024)
    o = pickle.loads(p)
    logger.info('Order received: %s', o)

    # Close socket
    logger.info('Leaving Drive-Through')
    sock.close()

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pi HTTP server')
    parser.add_argument('-p', dest='port', type=int, help='client port', default=5004)
    parser.add_argument('-r', dest='ring', type=int, help='ring ports ', default=5100)
    parser.add_argument('-t', dest='timeout', type=int, help='socket timeout', default=30000)
    args = parser.parse_args()
    main(args.port, ('localhost', args.ring), args.timeout)
