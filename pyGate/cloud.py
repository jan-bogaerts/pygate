import logging
import att_iot_gateway as IOT                              #provide cloud support
import threading


_pyGateCallback = None                                                          #callback for pyGate module, which hanldes distribution of the callback over the modules (and possible plugins)
_httpLock = threading.Lock()                                                    # makes http request thread save (only 1 plugin can call http at a time, otherwise we get confused.
_mqttLock = threading.Lock()                                                    # makes mqtt send requests thread save

def onActuate(device, actuator, value):
    '''called by att_iot_gateway when actuator command is received'''
    devid = device.split('_')                       # device id contains module name
    if _pyGateCallback:
        _pyGateCallback(devid[0], devid[1], actuator, value)


def connect(config, callback):
    """set up the connection with the cloud from the specified configuration
       callback: the callback function for actuator commands
                    format: onActuate(module, device, actuator, value)"""
    IOT.on_message = onActuate 
    success = False
    while not success:
        try:
            IOT.connect()           #"att-capp-2.cloudapp.net"
            if _authenticate(config):
                IOT.subscribe()              							#starts the bi-directional communication   "att-2.cloudapp.net"
                success = True
            else:
                logging.error("Failed to authenticate with IOT platform")
        except:
            logging.exception("failed to connect")

def _authenticate(config):
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
                sleep(2)                                # give the platform a litle time to set up all the configs so that we can subscribe correctly to the topic. If we don't do this, the subscribe could fail
                return True
            else:
                sleep(1)
        return False                                # if we get here, didn't succeed in time to finish the claiming process.
    else:
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
        sleep(1)                                                                    # wait a bit before retrying.

    result = hex(mac)[2:-1]                                                         # remove the 0x at the front and the L at the back.
    while len(result) < 12:                                                         # it could be that there were missing '0' in the front, add them manually.
        result = "0" + result
    result = result.upper()                                                         # make certain that it is upper case, easier to read, more standardized
    logging.info('mac address: ' + result)
    return result

def _storeConfig(config):
    '''stores the cloud config data in the config object'''
    config.gatewayId = IOT.GatewayId
    config.clientId = IOT.ClientId
    config.clientKey = IOT.ClientKey
    config.save()

def addAsset(module, deviceId, id, name, description, isActuator, assetType, style = "Undefined"):
    """add asset"""
    devId = module + '_' + deviceId
    _httpLock.acquire()
    try:
        IOT.addAsset(id, devId, name, description, isActuator, assetType, style)
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
    devId = module + '_' + deviceId
    _httpLock.acquire()
    try:
        IOT.addDevice(devId, name, description)
    finally:
        _httpLock.release()

def getDevices(self):
    """get all the devices listed for this gateway as a json structure."""
    _httpLock.acquire()
    try:
        return IOT.getGateway(True)
    finally:
        _httpLock.release()


def deviceExists(module, deviceId):
    """check if device exists"""
    devId = module + '_' + deviceId
    _httpLock.acquire()
    try:
        return IOT.deviceExists(devId)
    finally:
        _httpLock.release()

def deleteDevice(module, deviceId):
    """delete device"""
    devId = module + '_' + deviceId
    _httpLock.acquire()
    try:
        return IOT.deleteDevice(devId)
    finally:
        _httpLock.release()

def getAssetState(module, deviceId, assetId):
    """get value of asset"""
    devId = module + '_' + deviceId
    _httpLock.acquire()
    try:
        return IOT.getAssetState(assetId, devId)
    finally:
        _httpLock.release()


def send(module, device, actuator, value):
    '''send value to the cloud
    thread save: only 1 thread can send at a time'''
    devId = module + '_' + deviceId
    _mqttLock.acquire()
    try:
        IOT.send(value, devId, actuator)
    finally:
        _mqttLock.release()

def getModuleName(value):
    """extract the module name out of the string param."""
    return value[:value.find('_')]
