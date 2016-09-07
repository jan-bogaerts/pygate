__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

_gateway = None
_VersionId = 'version'

def sendFirmwareVersion():
    """sends the firmware version of the gateway to the platform
        This way, maintainers know the currently installed application that's running on the gateway.
    """
    try:
        with open('version.txt', 'r') as ver_file:
            content = ver_file.read()
    except:
        content = "unknown version"
    IOT.send(content, _globalData, 2)

def syncGatewayAssets():
    _gateway.addGatewayAsset(_VersionId, 'Version', 'Use this actuator to initiate a version change in the gateway software. The new version will be downloaded from the appropriate server',
                 True, 'string')
    sendFirmwareVersion()