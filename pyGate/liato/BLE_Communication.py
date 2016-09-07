__author__ = 'Vyacheslav Karneichik'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = ['Jan Bogaerts']
__maintainer__ = "Jan Bogaerts"
__email__ = "slava@embs.be"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('liato')

import serial
import struct
from Queue import Queue
from threading import Thread
import time
from core import config


# define API commands for this script


def ble_cmd_system_reset(p, boot_in_dfu):
    p.write(struct.pack('5B', 0, 1, 0, 0, boot_in_dfu))


def ble_cmd_connection_disconnect(p, connection):
    p.write(struct.pack('5B', 0, 1, 3, 0, connection))


def ble_cmd_gap_set_mode(p, discover, connect):
    p.write(struct.pack('6B', 0, 2, 6, 1, discover, connect))


def ble_cmd_gap_end_procedure(p):
    p.write(struct.pack('4B', 0, 0, 6, 4))


def ble_cmd_gap_set_scan_parameters(p, scan_interval, scan_window, active):
    p.write(struct.pack('<4BHHB', 0, 5, 6, 7, scan_interval, scan_window, active))


def ble_cmd_gap_discover(p, mode):
    p.write(struct.pack('5B', 0, 1, 6, 2, mode))


# define basic BGAPI parser
bgapi_rx_buffer = []
bgapi_rx_expected_length = 0


def bgapi_parse(b, queue):
    global bgapi_rx_buffer, bgapi_rx_expected_length
    if len(bgapi_rx_buffer) == 0 and (b == 0x00 or b == 0x80):
        bgapi_rx_buffer.append(b)
    elif len(bgapi_rx_buffer) == 1:
        bgapi_rx_buffer.append(b)
        bgapi_rx_expected_length = 4 + \
            (bgapi_rx_buffer[0] & 0x07) + bgapi_rx_buffer[1]
    elif len(bgapi_rx_buffer) > 1:
        bgapi_rx_buffer.append(b)

    # print '%02X: %d, %d' % (b, len(bgapi_rx_buffer),
    # bgapi_rx_expected_length)
    if bgapi_rx_expected_length > 0 and len(bgapi_rx_buffer) == bgapi_rx_expected_length:
        #        print '<=[ ' + ' '.join(['%02X' % b for b in bgapi_rx_buffer ]) + ']'
        packet_type, payload_length, packet_class, packet_command = bgapi_rx_buffer[:4]
        bgapi_rx_payload = b''.join(chr(i) for i in bgapi_rx_buffer[4:])
        if packet_type & 0x80 == 0x00:  # response
            bgapi_filler = 0
        else:  # event
            if packet_class == 0x06:  # gap
                if packet_command == 0x00:  # scan_response
                    rssi, packet_type, sender, address_type, bond, data_len = struct.unpack('<bB6sBBB', bgapi_rx_payload[:11])
                    sender = ''.join(['%02X' % ord(b) for b in sender[::-1]])
                    data_data = [ord(b) for b in bgapi_rx_payload[11:]]
#                    print(data_data)
                    filter_packets([rssi, sender, data_data, time.time()])
        bgapi_rx_buffer = []

run = True
buf = {}

def filter_packets(i):
    name = getAdvChunk(i[2], 0x08)
    if name is not None:
        name = ''.join(chr(b) for b in name)
    t = getAdvChunk(i[2], 0xff)
    if t is not None:
        if t[0] == 0x50 and t[1] == 0xfa:  # our company tag
            if buf.get(i[1], [0])[0] != t[2]:
                out = [str(i[3]), name, str(i[1]), i[0]] + [b for b in t[2:]]
                queue.put(out)
                buf[i[1]] = t[2:]

def get_report():
    return queue.get()

def get_error():
    if errorQueue.qsize() > 0:
        return errorQueue.get()
    return None

def listener(queue):
    global run
    while (run):
        # catch all incoming data
        while (ser.inWaiting()):
            bgapi_parse(ord(ser.read()), queue)
        # don't burden the CPU
        time.sleep(0.01)


# set all options


options_port="/dev/ttyACM0"
# options_port = "COM4"
options_baud = 256000
options_interval = 0xC8
options_window = 0xC8
options_display = "trpsabd"
options_uuid = []
options_mac = []
options_rssi = 0
options_active = False
options_quiet = False
options_friendly = False

def loadBLESettings():
    configs = config.loadConfig('BLE')
    if configs:
        global options_port, options_baud
        options_port = configs.get('general', 'port')
        options_baud = int(configs.get('general', 'baud'))
        return True
    else:
        return False
    logger.info("Serial port:\t%s" % options_port)
    logger.info("Baud rate:\t%s" % options_baud)
    logger.info("Scan interval:\t%d (%.02f ms)" % (options_interval, options_interval * 1.25))
    logger.info("Scan window:\t%d (%.02f ms)" % (options_window, options_window * 1.25))
    logger.info("Scan type:\t%s" % ['Passive', 'Active'][options_active])
    logger.info("Friendly mode:\t%s" % ['Disabled', 'Enabled'][options_friendly])
    logger.info("----------------------------------------------------------------")
    logger.info("Starting scan for BLE advertisements...")

queue = None
errorQueue = Queue()
ser = None                   # init globals

def connect():
    # open serial port for BGAPI access
    global queue, ser

    _connectSuccess = False
    while not _connectSuccess:
        try:
            ser = serial.Serial(port=options_port, baudrate=options_baud, timeout=1)
            _connectSuccess = True
        except serial.SerialException as e:
            logger.info("\n================================================================")
            logger.info("Port error (name='%s', baud='%ld'): %s" % (options_port, options_baud, e))
            logger.info("================================================================")

    # flush buffers
    logger.info("Flushing serial I/O buffers...")
    ser.flushInput()
    ser.flushOutput()


    # disconnect if we are connected already
    # print "Disconnecting if connected..."
    ble_cmd_connection_disconnect(ser, 0)
    response = ser.read(7)  # 7-byte response
    # for b in response: print '%02X' % ord(b),

    # stop advertising if we are advertising already
    # print "Exiting advertising mode if advertising..."
    ble_cmd_gap_set_mode(ser, 0, 0)
    response = ser.read(6)  # 6-byte response
    # for b in response: print '%02X' % ord(b),

    # stop scanning if we are scanning already
    logger.info("Exiting scanning mode if scanning...")
    ble_cmd_gap_end_procedure(ser)
    response = ser.read(6)  # 6-byte response
    # for b in response: print '%02X' % ord(b),

    # set scan parameters
    logger.info("Setting scanning parameters...")
    ble_cmd_gap_set_scan_parameters(ser, options_interval, options_window, options_active)
    response = ser.read(6)  # 6-byte response
    # for b in response: print '%02X' % ord(b),

    # start scanning now
    # print "Entering scanning mode for general discoverable..."
    ble_cmd_gap_discover(ser, 2)

    queue = Queue()

    worker = Thread(target=listener, args=(queue,))
    worker.setDaemon(True)
    worker.start()


def getAdvChunk(arr, type):
    while len(arr) > 1:
        if arr[1] != type:
            arr = arr[arr[0] + 1:]
        else:
            return arr[2:arr[0]+1]
    return
