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
    if serial_port:
        serial_port.close()

def run():
    try:
        while True:
            data = zb.wait_read_frame() #Get data for later use
            logger.info("found data: " + str(data))
            deviceId = data['source_addr_long'].encode("HEX")
            if deviceId not in devices:                     										#if we haven't seen this deviceId yet, check if we need to create a new device for it
                devices.append(deviceId)
                logger.info("Check if device already known in IOT")
                if gateway.deviceExists(deviceId) == False:     										#as we only keep deviceId's locally in memory, it could be that we already created the device in a previous run. We only want to create it 1 time.
                    logger.info("creating new device")
                    gateway.addDevice(deviceId, deviceId, "XBEE Plantsensor" )		#adjust according to your needs
                gateway.addAsset(1, deviceId, 'light', 'Light', False, 'integer')	#adjust according to your needs
                gateway.addAsset(2, deviceId, "temp", "Temperature", False, "integer")	#adjust according to your needs
                gateway.addAsset(3, deviceId, "moisture", "moisture", False, "integer")	#adjust according to your needs
                gateway.addAsset(4, deviceId, "Battery", "Battery Level (mv)", False, "integer") #adjust according to your needs
            temp = ((data['samples'][0]['adc-2']*1200/1023)-500)/10
            batt = (data['samples'][0]['adc-7']*1200/1023)
            gateway.send(data['samples'][0]['adc-1'], deviceId, 1)									#adjust according to your needs
            gateway.send(temp, deviceId, 2)									#adjust according to your needs
            gateway.send(data['samples'][0]['adc-3'], deviceId, 3)									#adjust according to your needs
            gateway.send(batt, deviceId, 4)
    except Exception as e:                                                      				#in case of an xbee error: print it and try to continue
        logger.exception("value error occured")
