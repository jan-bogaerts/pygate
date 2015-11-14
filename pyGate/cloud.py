import logging
import att_iot_gateway as IOT                              #provide cloud support


def connect(config, callback):
    """set up the connection with the cloud from the specified configuration
    callback: the callback function for actuator commands
                    format: onActuate(device, actuator, value)"""
    IOT.on_message = on_message

def addAsset(module, deviceId, id, name, description, isActuator, assetType, style = "Undefined"):
    """add asset"""

def addDevice(module, deviceId, name, description):
    """add device"""

def getDevices(self):
    """get all the devices listed for this gateway."""


def deviceExists(module, deviceId):
    """check if device exists"""

def deleteDevice(module, deviceId):
    """delete device"""

def getAssetState(module, assetId, deviceId):
    """get value of asset"""

def send(module, device, actuator, value):
    '''send value to the cloud
    thread save: only 1 thread can send at a time'''

def getModuleName(value):
    """extract the module name out of the string param."""
    return value[:value.find('_')]


