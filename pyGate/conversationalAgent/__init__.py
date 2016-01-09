__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

##################################################
# provides a language interface for the gateway
##################################################


import logging

import cloud
import modules

_moduleName = None
conversationId = '1'

logger = logging.getLogger('c-agent')

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _moduleName
    _moduleName = moduleName


def syncGatewayAssets():
    cloud.addGatewayAsset(_moduleName, conversationId , 'converstaion', 'talk to the gateway', True, 'string')

#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id == conversationId:
        processInput(value)
    else:
        logger.error("unknown actuator: " + id)



def processInput(value):
    """check the text input and do something with it"""
    words = value.lower().split()
    module, device = getDevice(words)
    if device:
        actuator, value = getAction(device, words)
        modules.Actuate(module, device.node_id, actuator, value)

def getDevice(words):
    """look up the device, currently simple"""
    zwave = modules['zwave']

    for key, node in zwave.manager.network.nodes.iteritems():
        if node.location in words:
            return zwave, node
    return none

def getAction(device, words):
    if 'omhoog' in words or 'open' in words:
        actuator = [act for act in node.values.iteritems() if act.label == 'Open']
        return actuator, True
    elif 'beneden' in words or 'toe' in words or 'sluiten' in words:
        """close something"""
        actuator = [act for act in node.values.iteritems() if act.label == 'Close']
        return actuator, True