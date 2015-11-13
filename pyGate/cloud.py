class Cloud(object):
    """provides access to the cloud"""

    def connect(self, config):
        """set up the connection with the cloud from the specified configuration"""

    def addAsset(self, id, deviceId, name, description, isActuator, assetType, style = "Undefined"):
        """add asset"""

    def addDevice(self, deviceId, name, description):
        """add device"""

    def getDevices(self):
        """get all the devices listed for this gateway."""

    def deviceExists(self, deviceId):
        """check if device exists"""

    def deleteDevice(self, deviceId):
        """delete device"""

    def getAssetState(self, assetId, deviceId):
        """get value of asset"""

    def getModuleName(self, value):
        """extract the module name out of the string param."""
        return value[:value.find('_')]