'''
A VERY messy, hacky LIFX LAN python implementation. There are better versions out there worth using. This one is just for play and my learning, but if it helps you, feel free to use it.
'''
import socket
from bitstruct import pack, unpack, byteswap, calcsize
from binascii import hexlify

# frame header: size|origin|tagged|addressable|protocol|source
fheader_fmt = 'u16u2u1u1u12u32'
fheader_bs = '224'

# frame address: target|reserved|reserved|ack|res|sequence
faddr_fmt = 'u64u48u6u1u1u8'
faddr_bs = '8611'

# protocol header: reserved|type|reserved|(payload)
pheader_fmt = 'u64u16u16'
pheader_bs = '822'

lifxsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
bcast = ("192.168.1.255", 56700)

# name: (protocol, 'fmt', 'bswap') # description (Response)
TO_MSGS = {
    'GetService': (2, '', ''), # bcast to acquire responses (StateService)
    'GetHostInfo': (12, '', ''), # get MCU info (StateHostInfo)
    'GetHostFirmware': (14, '', ''), # get MCU Firmware info (StateHostFirmware)
    'GetWifiInfo': (16, '', ''), # get Wifi info (StateWifiInfo)
    'GetWifiFirmware': (18, '', ''), # get Wifi firmware info (StateWifiFirmware)
    'GetPower': (20, '', ''), # gets power level (StatePower)
    'SetPower': (21, 'u16', '2'), # set power level 0-65535
    'SetLabel': (23, 't256', ['32']), # sets the bulb label
    'GetVersion': (32, '', ''), # gets HW version (StateVersion)
    'GetInfo': (34, '', ''), # get runtime info (StateInfo)
    'GetLocation': (48, '', ''), # get location info (StateLocation)
    'GetGroup': (51, '', ''), # get group info (StateGroup)
    'EchoRequest': (58, 'u512', ['64']), # echo a payload (EchoResponse)
    'SetColorZones': (501, 'u8u8u16u16u16u16u32u8', '11222241'), # start|end|HSBK|duration|apply
    'GetColorZones': (502, 'u8u8', '11'), # start|end (StateZone or StateZones)
    'GetLightState': (101, '', ''), # (StateColor)
    'SetColor': (102, 'u8u16u16u16u16u32', '122224'), # set the color
    'GetPower': (116, '', ''), # (StatePower)
    'SetPower': (117, 'u16u32', '24'), # level|duration
    'GetInfrared': (120, '', ''), # get max power level of Infrared channel
    'SetInfrared': (122, 'u16', '2') # brightness
}

# protocol: ('Name', 'fmt', 'bswap') # description
FROM_MSGS = {
    3: ('StateService', 'u8u32', '14') # service|port
    13: ('StateHostInfo', 'u32u32u32u16', '4442'), # signal|tx|rx|reserved
    15: ('StateHostFirmware', 'u64u64u32', '884'), # build|reserved|version
    17: ('StateWifiInfo', 'u32u32u32u16', '4442'), # signal|tx|rx|reserved
    19: ('StateWifiFirmware' 'u64u64u32', '884'), # build|reserved|version
    22: ('StatePower', 'u16', '2'), # level (0-65535)
    25: ('StateLabel', 't256', ['32']), # label (256 bytes)
    33: ('StateVersion', 'u32u32u32', '444'), # vendor|product|version
    35: ('StateInfo', 'u64u64u64', '888'), # current time|uptime|downtime (ns since epoch)
    45: ('Acknowledgement', '', ''), # ACK response when ACK sent with value of 1
    50: ('StateLocation', 'u128t256u64', ['16','32','8']), # location|label|updated_at
    53: ('StateGroup', 'u128t256u64', ['16','32','8']), # group|label|updated_at
    59: ('EchoResponse', 'u512', ['64']), # payload
    503: ('StateZone', 'u8u8u16u16u16u16', '112222'), # count (#avail)|index|HSBK
    506: ('StateMultiZone', 'u8u8'+'u16u16u16u16'*8, '11'+'2222'*8), # count|index|color[0]...color[7]
    107: ('StateColor', 'u16u16u16u16s16u16t256u64', ['2']*6+['32','8']), # HSBK|resv|power|label|resv
    121: ('StateInfrared', 'u16', '2'), # brightness
}

# for Multizone packets, NO_APPLY buffers msg, APPLY applies this and buffered changes, APPLY_ONLY applies buffered, but not this message
APPLY = { 'NO_APPLY': 0, 'APPLY': 1, 'APPLY_ONLY': 2 }

# various valid responses to StateVersion mesages for product type. Note LIFX is Vendor 1
PRODUCT_INFO = {
    1: 'Original 1000',
    3: 'Color 650',
    10: 'White 800 (Low Voltage)',
    11: 'White 800 (High Voltage)'
    31: 'LIFX Z'
}


def set_timeout(value):
    '''sets the lifx socket timeout, in seconds'''
    lifxsock.settimeout(value)

def send_packet(packet, addr):
    '''sends the given packet to the given address on the lifx socket'''
    lifxsock.sendto(packet, addr)
    
def receive():
    '''receives 4096 bytes from the lifx socket, if available; blocks for the timeout or throws'''
    return lifxsock.recvfrom(4096)

def sizeof(format):
    '''returns the number of bytes in a format, using calcsize / 8'''
    return int(calcsize(format) / 8)
        
def decode(packet, start, fmt, bswap):
    '''decodes a packet, starting at start, using format fmt and byte swap pattern bswap'''
    data = packet[start:start+sizeof(fmt)]
    return unpack(fmt, byteswap(bswap, data))

headers_size = sizeof(pheader_fmt + fheader_fmt + faddr_fmt)
def decode_payload(packet, fmt, bswap):
    '''decodes a payload packet using fmt and bswap by calling decode at the payload starting position'''
    return decode(packet, headers_size, fmt, bswap)
    
def make_frame_header(size, tagged):
    '''returns a frame header using the given size and tagged parameters'''
    unswapped_header = pack(fheader_fmt, \
        size, 0, tagged, 1, 1024, 25061990)
    return byteswap(fheader_bs, unswapped_header)

fh_start = 0
def decode_header(packet):
    '''decodes the header of a packet using decode starting at the header position'''
    return decode(packet, 0, fheader_fmt, fheader_bs)
    
def make_frame_address(target, ack_required, res_required, sequence):
    '''returns a frame address with the given target, ack/res, and sequence values'''
    unswapped_header = pack(faddr_fmt, target, 0, 0, ack_required, res_required, sequence)
    return byteswap(faddr_bs, unswapped_header)

fa_start = sizeof(fheader_fmt)
def decode_frame_address(packet):
    '''decodes a frame address for a packet using decode with the frame address start position'''
    return decode(packet, fa_start, faddr_fmt, faddr_bs)

def make_protocol_header(message_type):
    '''creates a protocol header of the given type'''
    unswapped_header = pack(pheader_fmt, 0, message_type, 0)
    return byteswap(pheader_bs, unswapped_header)

pt_start = sizeof(fheader_fmt + faddr_fmt)
def decode_protocol_header(packet):
    '''decodes a protocol header by using decode with the correct protocol header position'''
    return decode(packet, pt_start, pheader_fmt, pheader_bs)
    
def send_discovery():
    '''creates the discovery packet (GetService) and transmits it over the broadcast address'''
    frame_header = make_frame_header(headers_size, 1)
    frame_address = make_frame_address(0, 0, 1, 0)
    protocol_header = make_protocol_header(2)
    header = frame_header + frame_address + protocol_header
    send_packet(header, bcast)

def get_group(target, seq=0):
    '''creates and sends the GetGroup packet to the given target, using the seq # (or zero)'''
    frame_header = make_frame_header(headers_size, 0)
    frame_address = make_frame_address(target[0], 0, 1, seq)
    protocol_header = make_protocol_header(51)
    packet = frame_header + frame_address + protocol_header
    send_packet(packet, (target[1], target[2]))
    
def get_mata(target, ack):
    if target is None:
        addr = bcast
        mac = 0
    else:
        mac = target[0]
        addr = (target[1], target[2])
    tagged = 1 if target is None else 0
    ack = 1 if ack is True else 0
    return (mac, addr, tagged, ack)
    
def set_color(hue, saturation, brightness, kelvin, duration, 
    target=None, ack=False, seq=0):
    # Set the colour of the bulb, based on the input values.

    # Set the format of the payload for this type of message
    payload_format = 'u8u16u16u16u16u32'
    payload_byteswap = '122224'

    packet_size = headers_size + sizeof(payload_format)

    mac, addr, tagged, ack = get_mata(target, ack)
    print((mac, addr, tagged))

    frame_header = make_frame_header(packet_size, tagged)
    frame_address = make_frame_address(mac, ack, 0, seq)
    protocol_header = make_protocol_header(102)
    header = frame_header + frame_address + protocol_header   

    hue = int((float(hue) / 360) * 65535)
    saturation = int(float(saturation) * 65535)
    brightness = int(float(brightness) * 65535)
    kelvin = int(kelvin)
    duration = int(duration)

    unswapped_payload = pack(payload_format, 0, hue, saturation, brightness, kelvin, duration)
    payload = byteswap(payload_byteswap, unswapped_payload)

    packet = header + payload
    send_packet(packet, addr)
    
class Color():
    def __init__(self, h, s, b, k):
        self.h = h
        self.s = s
        self.b = b
        self.k = k
        
    def get_packet(self):
        hue = int((float(self.h) / 360) * 65535)
        saturation = int(float(self.s) * 65535)
        brightness = int(float(self.b) * 65535)
        kelvin = int(self.k)
        return byteswap('2222', pack('u16u16u16u16',
            hue, saturation, brightness, kelvin))

'''
    period - length of each cycle in ms
    form - wave form
        0 - saw
        1 - sine
        2 - half sine
        3 - triangle
        4 - pulse (square)
    cycles - number of cycles
    set_back - return to original afterward
    duty - (16bit signed) 
        more negative: spend more time at first
        more positive: spend more time at second
'''
def send_wave(color, period, form, cycles=1, set_back=True, duty=0, target=None, ack=False, seq=0):
    fmt = 'u8u8u16u16u16u16u32f32s16u8'
    packet_size = headers_size + sizeof(fmt)
    mac,addr,tagged,ack = get_mata(target, ack)
    fhdr = make_frame_header(packet_size, tagged)
    faddr = make_frame_address(mac, ack, 0, seq)
    phdr = make_protocol_header(103)
    hdr = fhdr + faddr + phdr
    transient = 1 if set_back is True else 0
    payload = byteswap('11', pack('u8u8',0,transient)) +\
        color.get_packet() +\
        byteswap('4421', pack('u32f32s16u8', period, cycles, duty, form))
    print(payload)
    packet = hdr + payload
    send_packet(packet, addr)
    

def pulse_color(hue, brightness=.5, duration=.25):
    b = max(min(brightness, .15), .85)
    set_color(hue, 1, b, 5000, duration*1000)
    time.sleep(duration)
    set_color(hue, 1, .1, 5000, 1)


def pulse_red():
    pulse_color(30)


def pulse_blue():
    pulse_color(270)


def pulse_purple():
    pulse_color(300)


def pulse_green():
    pulse_color(120)
