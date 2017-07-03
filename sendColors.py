from lifxplay import *
import socket
import time
import socket
from pprint import pprint


'''
returns bubls as {mac: (ip_addr, port, '', '')}
the third value can later be set to the bulb's label.
the fourth can be later set to the bulbs group
'''
def discover_bulbs(timeout=5):
    set_timeout(timeout)
    send_discovery()

    bulbs = {}
    try:
        while True:
            data, (ipaddr, port) = receive()
            protocol, results = decode_payload_auto(data)
            if protocol == MSG_IDS['StateService']:
                _, port = results
                mac, _, _, _, _, _ = decode_frame_address(data)
                bulbs[mac] = (ipaddr, port, '', '')
    except socket.timeout:
        pass

    return bulbs

    
def get_labels(bulbs):
    for mac in bulbs:
        ip, port, _, _ = bulbs[mac]
        send_msg('GetLabel', None, target=(mac, ip, port))
                
    try:
        while True:
            data, (ipaddr, port) = receive()
            protocol, label = decode_payload_auto(data)
            if protocol == MSG_IDS['StateLabel']:
                label = ''.join(label)
                label = label[::-1].rstrip('\0')
                mac, _, _, _, _, _ = decode_frame_address(data)
                bulbs[mac] = (ipaddr, port, label, '')
    except socket.timeout:
        pass
       
       
       
def get_color_zones(mac, bulb):
    ip, port, _, _ = bulb
    
    zones = {}
    zone_count = 0
    
    send_msg('GetColorZones', (0, 255), target=(mac, ip, port), verbose=True)
    
    try:
        while True:
            data, (ipaddr, port) = receive()
            ret_mac, _, _, _, _, _ = decode_frame_address(data)
            if ret_mac != mac:
                continue

            protocol, payload = decode_payload_auto(data)
            if protocol == MSG_IDS['StateMultiZone']:
                print('multi')
                zone_count, index = payload[0:2]
                for i in range(8):
                    h,s,b,k = payload[i*4+2:i*4+6]
                    zones[index + i] = (h,s,b,k)
            if protocol == MSG_IDS['StateZone']:
                print('single')
                zone_count, index, h, s, b, k = payload
                zones[index] = (h,s,b,k)
                
    except socket.timeout:
        pass
        
    return (zone_count, zones)
        
'''
bulbs = discover_bulbs(1)
get_labels(bulbs)
pprint(bulbs)

cb = [b for b in bulbs if bulbs[b][2] == 'Cabinet Lights'][0]
cb = [cb].append(bulbs[cb])
print(cb)
'''

set_timeout(2)
zones = get_color_zones(272528909366224, ('192.168.1.233', 56700, 'Cabinet Lights', ''))
pprint(zones)
exit()


cabinet = (272528909366224, '192.168.1.233', 56700)
for i in range(80):
    h = int(65535.0/80.0*i)
    s = 65535
    b = 65535
    k = 3500
    payload = (i, i, h, s, b, k, 2000, APPLY['NO_APPLY'])
    send_msg('SetColorZones', payload, target=cabinet, verbose=True)
    time.sleep(.050)
send_msg('SetColorZones', (0, 0, 0, 0, 0, 5000, 0, APPLY['APPLY_ONLY']))
exit()


bulbs = {b:bulbs[b] for b in bulbs if bulbs[b][2] == 'Bedroom'}

for j,b in enumerate(bulbs):
    d = bulbs[b]
    target=(b,d[0],d[1])
    c = Color(270, 1, 1, 5000)
    #send_wave(c, 750, form=3, cycles=.75, duty=-((2**15)-1),target=None, set_back=False)
    set_color(40, 1, 1, 5000, 1, target)