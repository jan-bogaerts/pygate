__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

##################################################
# manages the gateway functionality like refresh
# and provides an application identity to the gateway (for auto discovery of gateways in an account)
# this is done through gateway assets that don't belong to any other plugin
##################################################

import logging

from core import cloud, modules

_moduleName = None
refreshGatewayId = '1'
ApplicationId = 'applicationId'

logger = logging.getLogger('main')

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _moduleName
    _moduleName = moduleName


def syncGatewayAssets():
    cloud.addGatewayAsset(_moduleName, refreshGatewayId, 'refresh', 'refresh all the devices and assets', True, 'boolean')
    cloud.addGatewayAsset(_moduleName, ApplicationId, 'application Id', 'Identifies the software running on the gateway', False, 'string')

#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id == refreshGatewayId:
        modules.syncGatewayAssets()
        modules.syncDevices(True)
    else:
        logger.error("unknown actuator: " + id)


def run():
    ''' optional
        main function of the plugin module
        init the assets'''
    cloud.send(_moduleName, None, ApplicationId, "ATT-pyGate")