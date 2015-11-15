#allows a gateway plugin to manage it's cloud presence.

import cloud

class Gateway(object):
    '''allows a gateway to manage it's cloud presence'''

    def __init__(self, moduleName):
        result = super(Gateway, self).__init__()
        self._moduleName = moduleName
        return result

    def addAsset(self, id, deviceId, name, description, isActuator, assetType, style = "Undefined"):
        """add asset"""
        cloud.addAsset(self, self._moduleName, deviceId, id, name, description, isActuator, assetType, style)

    def addGatewayAsset(self, id, name, description, isActuator, assetType, style = "Undefined"):
        cloud.addGatewayAsset(self, self._moduleName, id, name, description, isActuator, assetType, style)

    def addDevice(self, deviceId, name, description):
        """add device"""
        cloud.addDevice(self, self._moduleName, deviceId, name, description)

    def send(self, value, deviceId, actuator):
        cloud.send(self._moduleName, deviceId, actuator, value)
