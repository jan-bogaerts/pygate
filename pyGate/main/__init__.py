__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

##################################################
# manages the gateway functionality like refresh
# this is done through gateway assets that don't belong to any other plugin
##################################################

import logging

import cloud
import modules

_moduleName = None
refreshGatewayId = '1'

logger = logging.getLogger('main')

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _moduleName
    _moduleName = moduleName


def syncGatewayAssets():
    cloud.addGatewayAsset(_moduleName, refreshGatewayId , 'refresh', 'refresh all the devices and assets', True, 'boolean')

#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id == refreshGatewayId:
        modules.syncGatewayAssets(True)
        modules.syncDevices(True)
    else:
        logger.error("unknown actuator: " + id)