#allows a device to manage it's cloud presence.

import cloud

class Device(object):
    '''allows a device to manage it's cloud presence'''

    def __init__(self, moduleName, deviceId):
        result = super(Device, self).__init__()
        self._deviceId = deviceId
        self._moduleName = moduleName
        return result

    def addAsset(self, id, name, description, isActuator, assetType, style = "Undefined"):
        """add asset"""
        cloud.addAsset(self._moduleName, self._deviceId, id, name, description, isActuator, assetType, style)

    def createDevice(self, name, description):
        """add device"""
        cloud.addDevice(self._moduleName, self._deviceId, name, description)

    def send(self, value, actuator):
        cloud.send(self._moduleName, self._deviceId, actuator, value)