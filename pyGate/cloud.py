import logging
import att_iot_gateway.att_iot_gateway as IOT                              #provide cloud support
import threading
import time
from uuid import getnode as get_mac

import config

_sensorCallback = None                                                          #callback for pyGate module, called when sensor data is sent out.
_actuatorCallback = None                                                          #callback for pyGate module, called when actuator data came in and needs to be redistributed to the correct module.
_httpLock = threading.Lock()                                                    # makes http request thread save (only 1 plugin can call http at a time, otherwise we get confused.
_mqttLock = threading.Lock()                                                    # makes mqtt send requests thread save

def onActuate(device, actuator, value):
    '''called by att_iot_gateway when actuator command is received'''
    if _actuatorCallback:                                     # need a callback, otherwise there is no handler for the command (yet).
        if device:                                          # its an actuator for a specific device
            devid = device.split('_')                       # device id contains module name
            _actuatorCallback(devid[0], devid[1], actuator, value)
        else:                                               # it's an actuator at the level of the gateway.
            splitPos = actuator.find('_')
            module = actuator[:splitPos]          #get the module name from the actuator
            _actuatorCallback(module, None, actuator[splitPos + 1:], value)



def connect(actuatorcallback, sensorCallback):
    """set up the connection with the cloud from the specified configuration
       actuatorcallback: the callback function for actuator commands
                    format: onActuate(module, device, actuator, value)
       sensorCallback: the callback function that will be called when sensor data is sent to the cloud"""
    global _sensorCallback, _actuatorCallback
    _actuatorCallback = actuatorcallback
    _sensorCallback = sensorCallback
    IOT.on_message = onActuate 
    success = False
    while not success:
        try:
            IOT.connect(config.apiServer)           
            if _authenticate():
                IOT.subscribe(config.broker)              							#starts the bi-directional communication   "att-2.cloudapp.net"
                success = True
            else:
                logging.error("Failed to authenticate with IOT platform")
                time.sleep(2)                                           # wait a little until we try again.
        except:
            logging.exception("failed to connect")
            time.sleep(2)

def _authenticate():
    '''if authentication had previously succeeded, loads credentials and validates them with the platform
       if not previously authenticated: register as gateway and wait until user has claimed it
       params:
    '''
    if not config.gatewayId:
        uid = _getUid();
        IOT.createGateway("pyGate", uid)
        while True:                                     # we try to finish the claim process until success or app quits, cause the app can't continue without a valid and claimed gateway
            if IOT.finishclaim("pyGate", uid):
                _storeConfig()
                time.sleep(2)                                # give the platform a litle time to set up all the configs so that we can subscribe correctly to the topic. If we don't do this, the subscribe could fail
                return True
            else:
                time.sleep(1)
        return False                                # if we get here, didn't succeed in time to finish the claiming process.
    else:
        IOT.GatewayId = config.gatewayId
        IOT.ClientId = config.clientId
        IOT.ClientKey = config.clientKey
        if IOT.authenticate():
            logging.info('Authenticated')
            return True
        else:
            logging.error('failed to authenticate')
            return False

def _getUid():
    'extract the mac address in order to identify the gateway in the cloud'
    mac = 0
    while True:                                                                     # for as long as we are getting a fake mac address back, try again (this can happen if the hw isn't ready yet, for instance usb wifi dongle)
        mac = get_mac()
        if mac & 0x10000000000 == 0:
            break
        time.sleep(1)                                                                    # wait a bit before retrying.

    result = hex(mac)[2:-1]                                                         # remove the 0x at the front and the L at the back.
    while len(result) < 12:                                                         # it could be that there were missing '0' in the front, add them manually.
        result = "0" + result
    result = result.upper()                                                         # make certain that it is upper case, easier to read, more standardized
    logging.info('mac address: ' + result)
    return result

def _storeConfig():
    '''stores the cloud config data in the config object'''
    config.gatewayId = IOT.GatewayId
    config.clientId = IOT.ClientId
    config.clientKey = IOT.ClientKey
    config.save()

def addAsset(module, deviceId, id, name, description, isActuator, assetType, style = "Undefined"):
    """add asset"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        IOT.addAsset(id, devId, name, description, isActuator, assetType, style)
    finally:
        _httpLock.release()

def deleteAsset(module, deviceId, asset):
    """delete the asset"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        return IOT.deleteAsset(devId, asset)
    finally:
        _httpLock.release()

def addGatewayAsset(module, id, name, description, isActuator, assetType, style = "Undefined"):
    """add asset to gateway"""
    id = module + '_' + id
    _httpLock.acquire()
    try:
        IOT.addGatewayAsset(id, name, description, isActuator, assetType, style)
    finally:
        _httpLock.release()

def addDevice(module, deviceId, name, description):
    """add device"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        IOT.addDevice(devId, name, description)
    finally:
        _httpLock.release()

def getDevices():
    """get all the devices listed for this gateway as a json structure."""
    _httpLock.acquire()
    try:
        gateway = IOT.getGateway(True)
        if gateway:
            return gateway['devices']
        return []
    finally:
        _httpLock.release()


def deviceExists(module, deviceId):
    """check if device exists"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        return IOT.deviceExists(devId)
    finally:
        _httpLock.release()

def deleteDevice(module, deviceId):
    """delete device"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        return IOT.deleteDevice(devId)
    finally:
        _httpLock.release()

def deleteDeviceFullName(name):
    """delete device. Only use this if you know the full name (module + deviceId) of the device
    and it's internal structure. In other words, if you have an id (name) that came directly from the cloud
    """
    _httpLock.acquire()
    try:
        return IOT.deleteDevice(name)
    finally:
        _httpLock.release()

def getAssetState(module, deviceId, assetId):
    """get value of asset"""
    devId = getDeviceId(module, deviceId)
    _httpLock.acquire()
    try:
        return IOT.getAssetState(assetId, devId)
    finally:
        _httpLock.release()


def send(module, device, asset, value):
    '''send value to the cloud
    thread save: only 1 thread can send at a time'''
    if device:                                                      # could be that there is no device: for gateway assets.
        device = getDeviceId(module, device)
    else:
        asset = getDeviceId(module, asset)
    _mqttLock.acquire()
    try:
        IOT.send(value, device, asset)
    finally:
        _mqttLock.release()
    if _sensorCallback:
        _sensorCallback(module, device, asset, value)

def getModuleName(value):
    """extract the module name out of the string param."""
    return value[:value.find('_')]

def stripDeviceId(value):
    """extract the module name out of the string param."""
    return value[value.find('_') + 1:]

def getDeviceId(module, device):
    return module + '_' + str(device)
