from lifxplay import *
import socket
import time
from pprint import pprint
import threading
    
'''
c = Color(270, 1, 1, 5000)
send_wave(c, 3000, form=0, cycles=3, duty=((2**14)-1), target=None, set_back=False)
exit()

#-((2**15)-1)
'''

#set_timeout(5)
send_discovery()

def read_response():
    while True:
        data, addr = receive()
        print(decode_protocol_header(data))
        print(decode_frame_address(data))
        print(server)
        msg = FROM_MSGS[
    except Exception as e:
        print(e)
    exit()
    
threading.Thread(target=read_response) # start the server to listen for responses

def get_ack(seq):
    while(True):
        data, server = receive()
        msgtype = decode_protocol_header(data)[1]
        pSeq = decode_frame_address(data)[5]
        if msgtype == 45 and pSeq == seq:
            break
        
# mac: (ip, port, name)
bulbs = {
 6979621057488: ('192.168.1.134', 56700, 'Dining Room'),
 40974287205328: ('192.168.1.129', 56700, 'Dining Room'),
 50955791201232: ('192.168.1.132', 56700, 'Dining Room'),
 246806283121616: ('192.168.1.136', 56700, 'Dining Room'),
 64128455898064: ('192.168.1.148', 56700, 'Dining Room'),
 65331046740944: ('192.168.1.137', 56700, 'Living Room'),
 78538087953360: ('192.168.1.103', 56700, 'Living Room'),
 200948917302224: ('192.168.1.111', 56700, 'Living Room'),
 169187650925520: ('192.168.1.131', 56700, 'Bedroom'),
 192019697071056: ('192.168.1.102', 56700, 'Bedroom'),
 195245217510352: ('192.168.1.105', 56700, 'Bedroom'),
 }
        

bulbs = {b:bulbs[b] for b in bulbs if bulbs[b][2] == 'Bedroom'}
pprint(bulbs)

for j,b in enumerate(bulbs):
    d = bulbs[b]
    target=(b,d[0],d[1])
    c = Color(270, 1, 1, 5000)
    #send_wave(c, 750, form=3, cycles=.75, duty=-((2**15)-1),target=None, set_back=False)
    set_color(40, 1, 1, 5000, 1, target)