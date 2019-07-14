import configparser
import time
from random import randint
import socket
import pickle

# simulate entity work
def work(seconds):
    time.sleep(seconds)

# load the configuration file
config = configparser.ConfigParser()
config.read('../config.ini')

count_Chef=-1

def contains_successor(identification, successor, node):
    if identification < node <= successor:
        return True
    elif successor < identification and (node > identification or node < successor):
        return True
    return False

def recv(sock):
    try:
        p, port = sock.recvfrom(1024)
    except socket.timeout:

        return None, None
    else:
        if len(p) == 0:
            return None, port
        else:
            return p, port

def send(sock,address, o):
    p = pickle.dumps(o)
    sock.sendto(p, address)

def choose_node(name,table):
    
    size = len(table[name])
    if size == 0:
        return table['name'][0]
    else:
        globals()['count_%s'%name] += 1
        return table[name][globals().get('count_%s'%name)%size]




