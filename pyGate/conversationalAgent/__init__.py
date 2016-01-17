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
    cloud.addGatewayAsset(_moduleName, conversationId , 'conversation', 'talk to the gateway', True, 'string')

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
    zwave = modules.modules['zwave']

    for key, node in zwave.manager.network.nodes.iteritems():
        if str(node.location) in words:
            return 'zwave', node
    return None

def getAction(device, words):
    if 'omhoog' in words or 'open' in words:
        actuator = [act for key, act in device.values.iteritems() if act.label == 'Level']
        if actuator:
            actuator = actuator[0].value_id
        return actuator, 99
    elif 'beneden' in words or 'toe' in words or 'sluiten' in words or 'close' in words:
        """close something"""
        actuator = [act for key, act in device.values.iteritems() if act.label == 'Level']
        if actuator:
            actuator = actuator[0].value_id
        return actuator, 0