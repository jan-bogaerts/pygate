__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('liato')

from core.gateway import Gateway
from core import assetStateCache as Cache

_gateway = None
_devices = []
_wearables = []
_ErrorId = 'error'

_COL_RIGHT = 8
_COL_MIDDLE = 6
_COL_LEFT = 4

_COL_BATTERY_WEARABLE = 9

def connect(name):
    """
    set up the gateway object
    :param name: the name to use for the gateway object
    :return:
    """
    global _gateway
    _gateway = Gateway(name)

def sendError(msg):
    """
    send a message to the error topic.
    :param msg: the error message to stend (string)
    :return: None
    """
    _gateway.send(msg, None, _ErrorId)


def createGatewayAssets():
    _gateway.addGatewayAsset(_ErrorId, 'liato last error', 'last error produced by the liato plugin', False, 'string')

def storeDevices(items):
    """
    store the already known devices in an area, so we don't try to recreate devices that already exist.
    :param items: list of json dicts.
    :return: None
    """
    _devices = [str(x['id']) for x in items]

def PrepareDeviceInCloud(id, type):
    'makes certain that the device is known in the cloud and that we have loaded everything that was previously defined in the cloud for this device (device local settings, like its neighbours)'
    if id not in _devices and id not in _wearables:   #if we haven't seen this deviceId yet, check if we need to create a new device for it
        logger.info("Check if device already known in IOT")
        deviceExists = _gateway.deviceExists(id)    										        #as we only keep deviceId's locally in memory, it could be that we already created the device in a previous run. We only want to create it 1 time.
        if type.startswith('LS'):
            if not deviceExists:
                logger.info("creating new device")
                _gateway.addDevice(id, "3-pir " + id, "a 3 pir device", True )		#adjust according to your needs
            # always update the assets, it could be from a previous version, an there are assets missing...
            # note: the next asset is id 4, so it's always inline with when doing simple/single value assets
            _gateway.addAsset('raw', id, 'raw', 'raw data', 'sensor', '{"title": "raw 3 pir data","type": "object","properties": {"left": {"type": "integer"},"middle": {"type": "integer"},"right": {"type": "integer"}},"required": ["left", "middle", "right"]}')  # adjust according to your needs
            _gateway.addAsset('battery', id, 'battery', 'battery level in %', 'sensor', 'number')
            _gateway.addAsset('location', id, 'location', 'the name of the room that the device is located at', 'config', 'string')
            _gateway.addAsset('firmware', id, 'firmware version', 'The version number of the firmware running on the device', 'sensor', 'string')
            _gateway.addAsset('rssi', id, 'RSSI', 'determines the connection strength', 'sensor', '{"type": "integer", "minimum": -255, "maximum":0}')
            _gateway.addAsset('type', id, 'type', 'pir type', 'config', 'string')
            _gateway.send(type[2:], id, 'firmware')
            #_gateway.addAsset(1, id, 'raw', 'raw data', False,'{"title": "raw 3 pir data","type": "object","properties": {"left": {"type": "int"},"middle": {"type": "int"},"right": {"type": "int"}},"required": ["left", "middle", "right"]}')  # adjust according to your needs
            #IOT.addAsset(4, id, 'area', 'area of interest', False, '{"title": "3 pir area detection","type": "object","properties": {"value": {"type": "int"},"level": {"type": "int"}},"required": ["value", "level"]}')
            #IOT.addAsset(6, id, 'battery', 'battery level in %', False, 'double')
            #IOT.addAsset(7, id, 'temperature', 'temperature of the device surrounding', False, 'int')
            #IOT.addAsset(8, id, 'location', 'the name of the room that the device is located at', True, 'string')
            #IOT.addAsset(9, id, 'neighbours', "the (local) device id's that are located adjacent to this device", True, '{ "type": "array", "items": { "type": "string"}, "minItems": 0, "uniqueItems": true}')
            #IOT.addAsset(10, id, 'area 1', 'the designated name of the area that pir 1 of the device is monitoring', True, 'string')
            #IOT.addAsset(11, id, 'area 2', 'the designated name of the area that pir 2 of the device is monitoring', True, 'string')
            #IOT.addAsset(12, id, 'area 3', 'the designated name of the area that pir 3 of the device is monitoring', True, 'string')
            #IOT.addAsset(13, id, 'exit/entry point', '-1 device does not monitor an exit-entry point, 0-2: the pir sensor assigned to the exit/entry point, 3 = entire device monitors the exit/entry point', True, '{ "type": "integer", "labels": [{ "name": "none", "value": -1}, { "name": "area 0", "value": 0}, { "name": "area 1", "value": 1}, { "name": "area 2", "value": 2}, { "name": "device", "value": 3}]}')
            #IOT.addAsset(14, id, 'PIR cutoff', 'the level below which pir measurements are considered to be 0', True, 'int')
            #IOT.addAsset(15, id, 'firmware version', 'The version number of the firmware running on the device', False, 'string')
            #IOT.addAsset(16, id, 'RSSI', 'determines the connection strength', False, '{"type": "integer", "minimum": -255, "maximum":0}')                                                                          #so the system knows the firmware version of hte device.
        elif type.startswith('LM'):
            if not deviceExists:
                logger.info("creating new device")
                _gateway.addDevice(id, "wear " + id, "wearable sensor", True )		#adjust according to your needs
            # always update the assets, it could be from a previous version, an there are assets missing...
            _gateway.addAsset('raw', id, 'raw', 'raw data', 'sensor', '{"title": "Example Schema","type": "object","properties": {"x": {"type": "int"},"y": {"type": "int"},"z": {"type": "int"}},"required": ["x", "y", "z"]}')	#adjust according to your needs
            _gateway.addAsset('firmware', id, 'firmware version', 'The version number of the firmware running on the device', 'sensor', 'string')
            _gateway.addAsset('battery', id, 'battery', 'battery level in %', 'sensor', 'double')
            if len(type) > 2:                                                         # for now, the version number is not yet included.
                _gateway.send(type[:2], id, 'firmware')

def send(t, deviceId, name):
    if name.startswith('LS'):
        # _prevArea
        _sendRawLSData(t, deviceId)
        _sendBatteryAndRSSI(t, deviceId)
    elif name.startswith('LM'):
        _gateway.send(_getJSonValueWearable(t), deviceId, 'raw')
        _sendBatteryWearable(t, deviceId)

def procLine(i):
    name = i[1]
    if name is not None:
        if len(name) >= 2 and name[:2] in ['LS', 'LM']:                                                        # if it's an unkown device type, don't process it.
            PrepareDeviceInCloud(i[2], name)
            send(i[2:], i[2], name)


def _sendRawLSData(t, deviceId):
    'send out the raw sample data, but only if its above the treshhold, otherwise its not interesting'
    device = _devices[deviceId]
    if not device:
        raise Exception('unknown device: ' + deviceId + ", can't send raw data to cloud")
    _gateway.send(_getJSonValue(t), deviceId, 'raw')

def _getJSonValue(t):
    'convert the data to a json struct that can be sent to the cloud (for 3-pir)'
    return {'left': t[_COL_LEFT], 'middle': t[_COL_MIDDLE], 'right': t[_COL_RIGHT]}


def _sendBatteryAndRSSI(t, deviceId):
    'if the temp/battery level is different from the previous reading, send the new value to the platform'
    prev = Cache.getValue('battery', deviceId)
    if prev != t[10]:
        temp = (int(t[10]) * 7.25) / 256                                                # calculation supplied by Jacob. converts it into available volts. Still has to be converted into % based on max - min allowed voltage levels.
        _gateway.send(temp, deviceId, 'battery')
    prev = Cache.getValue('battery', deviceId)
    if prev != t[1]:
        _gateway.send(t[1], deviceId, 'rssi')


def _getJSonValueWearable(t):
    """
    build the json result
    :param t:
    :return:
    """
    return {}

def _sendBatteryWearable(t, deviceId):
    prev = Cache.getValue('battery', deviceId)
    if prev != t[_COL_BATTERY_WEARABLE]:
        temp = (int(t[_COL_BATTERY_WEARABLE]) * 7.25) / 256                                                # calculation supplied by Jacob. converts it into available volts. Still has to be converted into % based on max - min allowed voltage levels.
        _gateway.send(temp, deviceId, 'battery')