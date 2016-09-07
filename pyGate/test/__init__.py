__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


#plugin for testing out various things.

import logging
logger = logging.getLogger('test')
from threading import Event

from core.gateway import Gateway
import csv
from mbus.MBusFrame import MBusFrame
from mbus.MBusFrameData import MBusFrameData
import mbus.MBusLowLevel as mbusLow
import ctypes
import binConverter


_gateway = None
_wakeUpEvent = Event()
_isRunning = True

isScanningId = "isScanning"

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _gateway
    _gateway = Gateway(moduleName)

def syncDevices(existing, full=False):
    '''optional
        allows a module to synchronize it's device list.
        :param existing: the list of devices that are already known in the cloud for this module.
        :param full: when false, if device already exists, don't update, including assets. When true,
         update all, including assets
     '''



def syncGatewayAssets():
    _gateway.addGatewayAsset(isScanningId, 'test is scanning', 'activate/stop scanning mode on mbus for discovering new devices', True, 'boolean')

def stop():
    """"called when the application terminates.  Allows us to clean up the hardware correctly, so we cn be restarted without (cold) reboot"""
    global _isRunning
    _isRunning = False
    _wakeUpEvent.set()                  # wake up the thread if it was sleeping
    logger.info("stopping mbus network")

def run():
    global _isRunning
    _gateway.send("false", None, isScanningId)
    while _isRunning:
        try:
            sleepTime = 10
            if sleepTime > 0:
                _wakeUpEvent.wait(sleepTime)
        except Exception as e:              # in case of a generic error: print it and try to continue
            logger.exception("Failed to retrieve ")


def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    if actuator == isScanningId:  # change discovery state
        if value.lower() == 'true':
            try:
                loadData()
                res = _gateway.addDeviceFromTemplate("1", "ABB-269622-32")
                logger.info(res)
            except:
                logger.exception("failed to add device id: {}, value: ".format(id, 1))
    else:
        logger.error("mbus: unknown gateway actuator command: " + actuator)


def loadData():
    """load previously recorded mbus data"""
    frames = []
    _lib = mbusLow.MBusLib("/root/libmbus/mbus/.libs/libmbus.so.0")
    with open ("test/data.csv", 'rb') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            frame = MBusFrame()
            frame.start1 = int(row[0])
            frame.length1 = int(row[1])
            frame.length2 = int(row[2])
            frame.start2 = int(row[3])
            frame.control = int(row[4])
            frame.address = int(row[5])
            frame.control_infomation = int(row[6])
            frame.checksum = int(row[7])
            frame.stop = int(row[8])
            tempType = ctypes.c_uint8 * 252
            frame.data =  tempType()
            list = [int(x) for x in row[9].strip().split(' ')]
            for x in range(0, len(list)):
                frame.data[x] = list[x]
            frame.data_size = int(row[10])
            frame.type = int(row[11])
            frame.timestamp = int(row[12])
            logger.info(frame)

            reply_data = MBusFrameData()
            if _lib.frame_data_parse(frame, reply_data) == -1:
                logger.error("m-bus data parse error")
            else:
                frames.append((reply_data))
        res = binConverter.toDict(frames, True)
        cleanData(frames, _lib)
        logger.info(res)

def cleanData(data, lib):
    try:
        for x in data:
            if x.data_var.record:
                lib.data_record_free(x.data_var.record)  # need to clean this up, it's a C pointer
    except:
        logger.exception("failed to clean up data")