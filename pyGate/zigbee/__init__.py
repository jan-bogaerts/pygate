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
devices = []                                           #contains the list of devices already connected to the
_isRunning = True

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global gateway, serial_port, zb

    if not config.configs.has_option('zigbee', 'port'):
        logger.error('zwave configuration missing: port')
        return
    if not config.configs.has_option('zigbee', 'baud rate'):
        logger.error('zwave configuration missing: logLevel')
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
            data = zb.wait_read_frame() #Get data for later use
            if _isRunning:
                logger.info("found data: " + str(data))
                deviceId = data['source_addr_long'].encode("HEX")
                if deviceId not in devices:                     										#if we haven't seen this deviceId yet, check if we need to create a new device for it
                    devices.append(deviceId)
                    logger.info("Check if device already known in IOT")
                    if gateway.deviceExists(deviceId) == False:     										#as we only keep deviceId's locally in memory, it could be that we already created the device in a previous run. We only want to create it 1 time.
                        logger.info("creating new device")
                        gateway.addDevice(deviceId, deviceId, "XBEE device")
                        for key, value in data['samples'][0]:
                            if str(key) == 'adc-7':
                                gateway.addAsset(key, deviceId, "battery", "battery", False, 'integer')
                            else:
                                gateway.addAsset(key, deviceId, key, key, False, 'integer')
                for key, value in data['samples'][0]:
                    if str(key) == 'adc-7':
                        value = value * 1200 / 1023
                    gateway.send(value, deviceId, key)									#adjust according to your needs
        except Exception as e:                                                      				#in case of an xbee error: print it and try to continue
            logger.exception("value error occured")
