__author__ = 'Vyacheslav Karneichik'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = ['Jan Bogaerts']
__maintainer__ = "Jan Bogaerts"
__email__ = "slava@embs.be"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('liato')

import bglib
import serial
import time
from core import config

from Queue import Queue
from threading import Thread, Lock

mutex = Lock()

run = True

ble = 0
ser = 0
peripheral_list = []
connection_handle = 0
att_handle_data = 0

uuid_my_service = [0x23, 0xd1, 0xbc, 0xea, 0x5f, 0x78, 0x23, 0x15, 0xde, 0xef, 0x12, 0x12, 0x24, 0x15, 0x00, 0x00]

STATE_STANDBY = 0
STATE_CONNECTING = 1
STATE_FINDING_ATTRIBUTES = 2
STATE_WRITE_DATA = 3
STATE_DISCONNECTING = 4
state = STATE_STANDBY

# handler to notify of an API parser timeout condition


def my_timeout(sender, args):
    # might want to try the following lines to reset, though it probably
    # wouldn't work at this point if it's already timed out:
    #ble.send_command(ser, ble.ble_cmd_system_reset(0))
    #ble.check_activity(ser, 1)
    logger.error("BGAPI parser timed out. Make sure the BLE device is in a known/idle state.")


def getAdvChunk(arr, type):
    try:
        while len(arr) > 0:
            if arr[1] != type:
                arr = arr[arr[0] + 1:]
            else:
                return arr[2:arr[0] + 1]
    except IndexError:
        return None
    return None

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

# test_counter = 0
# gap_scan_response handler


def my_ble_evt_gap_scan_response(sender, args):
    global state, ble, ser, wdt_count
    wdt_count = 0
    sender = ''.join(['%02X' % b for b in args['sender'][::-1]])
    filter_packets([args['rssi'], sender, args['data'], time.time()])


# connection_status handler
def my_ble_evt_connection_status(sender, args):
    global state, ble, ser, connection_handle

    if (args['flags'] & 0x05) == 0x05:
        # connected, now perform service discovery
        logger.info("Connected to %s" % ':'.join(['%02X' % b for b in args['address'][::-1]]))
        connection_handle = args['connection']
        state = STATE_FINDING_ATTRIBUTES
        ble.send_command(ser, ble.ble_cmd_attclient_find_information(connection_handle, 0x0001, 0xffff))
        ble.check_activity(ser, 1)

# attclient_find_information_found handler


def my_ble_evt_attclient_find_information_found(sender, args):
    global state, ble, ser, att_handle_data, att_handle_data_ccc

    # check for our data characteristic
    if args['uuid'] == list(uuid_my_service):
        logger.error("Found our data attribute: handle=%d" % args['chrhandle'])
        att_handle_data = args['chrhandle']

# attclient_procedure_completed handler


def my_ble_evt_attclient_procedure_completed(sender, args):
    global state, ble, ser, connection_handle, att_handle_start, att_handle_end, att_handle_data, att_handle_data_ccc

    # check if we just finished searching for services
    if state == STATE_FINDING_ATTRIBUTES:
        if att_handle_data > 0:
            state = STATE_WRITE_DATA
            ble.send_command(ser, ble.ble_cmd_attclient_attribute_write(connection_handle, att_handle_data, [0x61]))
            ble.check_activity(ser, 1)

    elif state == STATE_WRITE_DATA and args['chrhandle'] == att_handle_data:
        # disconnect
        ble.send_command(ser, ble.ble_cmd_connection_disconnect(connection_handle))
        ble.check_activity(ser, 1)
        state = STATE_DISCONNECTING


def my_ble_evt_connection_disconnected(sender, args):
    global state
    logger.info('Disconnected')
    state = STATE_STANDBY
    # start scanning now
    logger.info("Scanning for BLE peripherals...1")
    ble.send_command(ser, ble.ble_cmd_gap_discover(2))
    ble.check_activity(ser, 1)


errorQueue = Queue()


def listener():
    global run, ble, ser

    while (run):
        try:
            # check for all incoming data (no timeout, non-blocking)
            with mutex:
                ble.check_activity(ser)

            # don't burden the CPU
            time.sleep(0.01)

        except Exception as e:
            logger.error(str(e))
            errorQueue.put(str(e))


def wdt():
    global run, wdt_count
    while (run):
        try:
            if wdt_count > 30:
                with mutex:
                    start_scan()
                wdt_count = 0
            else:
                time.sleep(1)
                wdt_count += 1

        except Exception as e:
            logger.error(str(e))
            errorQueue.put(str(e))


wdt_count = 0
queue = Queue()


options_port = "/dev/ttyAMA0"
# options_port = "COM4"
options_baud = 115200


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


def start_scan():
    global ser, ble

    # flush buffers
    ser.flushInput()
    ser.flushOutput()

    # reset
    import RPi.GPIO as GPIO  # Import GPIO Library -> do this locally, don't need to keep it loaded all the time.
    pin = 37  # We're working with pin 26
    GPIO.setmode(GPIO.BOARD)  # Use BOARD pin numbering
    GPIO.setup(pin, GPIO.OUT)  # Set pin 26 to OUTPUT

    GPIO.output(pin, GPIO.LOW)  # Turn off GPIO pin (LOW)
    time.sleep(1)  # Wait 1 second
    GPIO.output(pin, GPIO.HIGH)  # Turn on GPIO pin (HIGH)
    time.sleep(1)  # Wait 3 second

    GPIO.cleanup()  # Cleanup

    #    ble.send_command(ser, ble.ble_cmd_system_reset(False))
    #    ble.check_activity(ser, 1)
    #    time.sleep(5)

    # disconnect if we are connected already
    ble.send_command(ser, ble.ble_cmd_connection_disconnect(connection_handle))
    ble.check_activity(ser, 3)

    # stop advertising if we are advertising already
    ble.send_command(ser, ble.ble_cmd_gap_set_mode(0, 0))
    ble.check_activity(ser, 3)

    # stop scanning if we are scanning already
    ble.send_command(ser, ble.ble_cmd_gap_end_procedure())
    ble.check_activity(ser, 3)

    # set scan parameters
    ble.send_command(ser, ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 0))
    ble.check_activity(ser, 3)

    # start scanning now
    logger.info("Scanning for BLE peripherals...")
    ble.send_command(ser, ble.ble_cmd_gap_discover(2))
    ble.check_activity(ser, 3)


def connect(debug=False):
    global ble, ser, connection_handle, att_handle_data, worker

    # create and setup BGLib object
    ble = bglib.BGLib()
    ble.packet_mode = True
    ble.debug = debug

    # add handler for BGAPI timeout condition (hopefully won't happen)
    ble.on_timeout += my_timeout

    # add handlers for BGAPI events
    ble.ble_evt_gap_scan_response += my_ble_evt_gap_scan_response
    ble.ble_evt_connection_status += my_ble_evt_connection_status
    ble.ble_evt_attclient_find_information_found += my_ble_evt_attclient_find_information_found
    ble.ble_evt_attclient_procedure_completed += my_ble_evt_attclient_procedure_completed
    ble.ble_evt_connection_disconnected += my_ble_evt_connection_disconnected

    # create serial port object
    try:
        ser = serial.Serial(port=options_port, baudrate=options_baud, timeout=1, writeTimeout=1)
    except serial.SerialException as e:
        logger.error("Port error %s" % e)
        exit(2)

    start_scan()

    worker = Thread(target=listener, args=())
    worker.setDaemon(True)
    worker.start()

    wdt_worker = Thread(target=wdt, args=())
    wdt_worker.setDaemon(True)
    wdt_worker.start()


def get_report():
    return queue.get()


def get_error():
    if errorQueue.qsize() > 0:
        return errorQueue.get()
    return None


def set_status(device_ID, status=[0x61]):
    global status_to_set
    state = STATE_CONNECTING
    status_to_set = status
    logger.info("connecting")
    # connect to this device
    ble.send_command(ser, ble.ble_cmd_gap_connect_direct(device_ID[::-1], 1, 0x06, 0x10, 0x100, 0))
    ble.check_activity(ser, 1)


if __name__ == '__main__':

    connect()

    counter = 0
    while (1):
        ob = get_report()
        out = ','.join(str(b) for b in ob)
        print out
