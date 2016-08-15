__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import serial
from xbee import ZigBee
import logging

from gateway import Gateway
import config

logger = logging.getLogger('zigbee')
serial_port = None
gateway = None
zb = None
devices = {}                                           #contains the dictionary of devices already known
_isRunning = True

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global gateway, serial_port, zb

    if not config.configs.has_option('zigbee', 'port'):
        logger.error('zigbee configuration missing: port')
        return
    if not config.configs.has_option('zigbee', 'baud rate'):
        logger.error('zigbee configuration missing: baud rate')
        return
    port = config.configs.get('zigbee', 'port')
    logger.info('zigbee server on port: ' + port)
    baudrate = config.configs.get('zigbee', 'baud rate')
    logger.info('zigbee baud rate: ' + baudrate)

    gateway = Gateway(moduleName)
    serial_port = serial.Serial(port, baudrate)                 #for windows
    zb = ZigBee(serial_port)

def stop():
    global _isRunning
    _isRunning = False
    if serial_port:
        serial_port.close()

def run():
    while _isRunning:
        try:
            data = zb.wait_read_frame()                                             #Get data, this is blocking
            if _isRunning:
                if data['id'] == 'node_id_indicator':
                    _tryAddDevice(data)
                else:

                    logger.info("found data: " + str(data))
                    deviceId = data['source_addr_long'].encode("HEX")
                    for key, value in data['samples'][0]:
                        gateway.send(value, deviceId, key)									#adjust according to your needs
        except Exception as e:                                                      				#in case of an xbee error: print it and try to continue
            logger.exception("value error occured")


def _tryAddDevice(data):
    """checks if the device already exists, if not, it is created."""
    logger.info("a device has been detected")
    deviceId = data['source_addr_long'].encode("HEX")
    if deviceId not in devices:  # if we haven't seen this deviceId yet, check if we need to create a new device for it
        devices[deviceId] = {}
        logger.info("Check if device already known in IOT")
        if gateway.deviceExists(deviceId) == False:             # as we only keep deviceId's locally in memory, it could be that we already created the device in a previous run. We only want to create it 1 time.
            logger.info("creating new device")
            gateway.addDevice(deviceId, deviceId, "XBEE device")
            for key, value in data['samples'][0]:
                if str(key) == 'adc-7':
                    gateway.addAsset(key, deviceId, "battery", "battery", False, 'integer')
                else:
                    gateway.addAsset(key, deviceId, key, key, False, 'integer')