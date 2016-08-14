__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
from louie import dispatcher #, All
from openzwave.network import ZWaveNetwork

import manager
import networkMonitor

logger = logging.getLogger('zwave')

class DataMessage:
    """use this class to create objects for sendAfterWaiting and sendAfterDone"""
    def __init__(self, value, asset, device = None):
        """
        :param value: the value to send
        :param asset: the asset to send the value for
        """
        self.value = value
        self.asset = asset
        self.device = device

sendAfterWaiting = None                             # this data structure contains the asset + it's value that should be sent to to the cloud when the controller's state becomes 'waiting'
sendOnDone = None                                   # this data structure contains the asset + it's value that should be sent to to the cloud when the controller's state becomes 'Completed', Cancel, Error or Failed

def _queriesDone(node):
    logger.info('queries done for node: ' + str(node))
    if manager._discoveryMode == 'Include' and node.node_id != 1:          # when the controller is restarted, all devices are also queried, at that time, we don't need to add devices, it is already added during the sync period, and all assets have also been refreshed already. This call is only needed for adding devices (in case some assets were missed during discovery)
        manager.addDevice(node)                             #make certain that when the query is done, everything gets loaded again, it could be that we misssed some.
        _stopDiscovery()
    # don't try to stop any discovery mode at this stage, the query can potentially take hours (for battery devices),
    # by that time, the user might be doing another include already.

#def _msgCompete():
#    logger.info('msg done ')

_controllerState = None

def _controllerCommand(state):
    try:
        global sendOnDone, sendAfterWaiting, _controllerState
        _controllerState = state
        manager.gateway.send(state, None, manager.controllerStateId)
        if state == 'Waiting' and sendAfterWaiting:
            manager.gateway.send(sendAfterWaiting.value, sendAfterWaiting.device, sendAfterWaiting.asset)
            sendAfterWaiting = None
        elif sendOnDone and state in ['Completed', 'Cancel', 'Error', 'Failed']:
            manager.gateway.send(sendOnDone.value, sendOnDone.device, sendOnDone.asset)
            sendOnDone = None
        #if state == 'Error':
        #    networkMonitor.restartNetwork()
    except:
        logger.exception('failed to process controller command ' + state )

def _stopDiscovery():
    """turns the discovery mode off, if needed (discovery still running)"""
    global sendOnDone
    logger.info("stop discovery requested, current state: " + _controllerState)
    if _controllerState == 'InProgress':
        sendOnDone = DataMessage('off', manager.discoveryStateId)
        manager.network.controller.cancel_command()                                     # we need to stop the include process cause a device has been added
    manager._discoveryMode = "Off"

def _nodeAdded(node):
    try:
        if manager._discoveryMode == 'Include' and node.node_id != 1:                                                               # after a hard reset, an event is raised to add the 1st node, which is the controller, we don't add that as a device, too confusing for the user, that is the gateway.
            logger.info('node added: ' + str(node))
            manager.addDevice(node)                                                         # add from here, could be that we never get 'nodeNaming' event and that this is the only 'addDevice' that gets called
            _stopDiscovery()
    except:
        logger.exception('failed to add node ' + str(node) )

def _nodeNaming(node):
    try:
        global sendOnDone
        if node.node_id != 1:
            if manager._discoveryMode == 'Include':
                logger.info('node renamed: ' + str(node))
                manager.addDevice(node)                         #we add here again, cause it seems that from this point on, we have enough info to create the object completely. Could be that 'nodeAdded' was not called?
                _stopDiscovery()                                # if not already done
            elif sendOnDone:                                    # when the location asset has changed, we get this event, so let the cloud know that it was updated ok.
                logger.info('node prop changed: ' + str(node))
                manager.gateway.send(sendOnDone.value, sendOnDone.device, sendOnDone.asset)
                sendOnDone = None
            else:
                logger.info('node props queried (should only be during start): ' + str(node))

    except:
        logger.exception('failed to remove node ' + str(node) )

def _nodeRemoved(node):
    try:
        global sendOnDone
        logger.info('node removed: ' + str(node))
        if manager._discoveryMode == "Exclude":                                             # if we are still in exclude mode, stop it
            sendOnDone = DataMessage('off', manager.discoveryStateId)
            manager.network.controller.cancel_command()                                     # we need to stop the include process cause a device has been removed
            manager._discoveryMode = "Off"
        manager.gateway.deleteDevice(str(node.node_id))                                     # always delete teh device, it was destroyed anyway.
    except:
        logger.exception('failed to remove node ' + str(node) )

def _assetAdded(node, value):
    try:
        if node.is_ready == False and manager.network.state >= ZWaveNetwork.STATE_AWAKED:          # when starting, don't need to add assets of known devices. only when the device is not yet fully queried (ready) and when the network has started. Note battery devices take a long time before they report in, so don't wait for them, otherwise we can't include easy.
            logger.info('asset added: ' + str(value))
            manager.addAsset(node, value)
        else:
            logger.info('asset found: ' + str(value) + ", should only happen during startup, controller state: " + str(_controllerState) + ", node.isReady =" + str(node.is_ready))
    except:
        logger.exception('failed to add asset for node: ' + str(node) + ', asset: ' + str(value) )

def _assetRemoved(node, value):
    try:
        logger.info('asset removed: ' + str(value.value_id))
        # dump(node)
        manager.gateway.deleteAsset(node.node_id, value)
    except:
        logger.exception('failed to remove asset for node: ' + str(node) + ', asset: ' + str(value) )

def _assetValue(node, value):
    try:
        logger.info('asest value: ' + str(value))
        manager.gateway.send(_getData(value), node.node_id, value.value_id)
    except:
        logger.exception('failed to process asset value for node: ' + str(node) + ', asset: ' + str(value) )

def _assetValueRefreshed(node, value):
    try:
        logger.info('asset value refreshed: ' + str(value))
        manager.gateway.send(_getData(value), node.node_id, value.value_id)
    except:
        logger.exception('failed to process asset value refresh for node: ' + str(node) + ', asset: ' + str(value) )

def dump(obj):
    'for testing'
    for attr in dir(obj):
        try:
            if hasattr( obj, attr ):
                if getattr(obj, attr):
                    print( "obj.%s = %s" % (attr, getattr(obj, attr)))
                else:
                    print( "obj.%s = none" % (attr))
        except:
            logger.exception('failed to print device ' )


def connectSignals():
    '''connect to all the louie signals (for values and nodes)'''
    dispatcher.connect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.connect(_nodeNaming, ZWaveNetwork.SIGNAL_NODE_NAMING)
    dispatcher.connect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.connect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(_assetValueRefreshed, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.connect(_assetValue, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.connect(_queriesDone, ZWaveNetwork.SIGNAL_NODE_QUERIES_COMPLETE)
    #dispatcher.connect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
    dispatcher.connect(_controllerCommand, ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND)


def disconnectSignals():
    '''disconnects all the louie signals (for values and nodes). This is used
    while reseting the controllers.
    '''
    dispatcher.disconnect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.disconnect(_nodeNaming, ZWaveNetwork.SIGNAL_NODE_NAMING)
    dispatcher.disconnect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.disconnect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.disconnect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.disconnect(_assetValueRefreshed, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.disconnect(_assetValue, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.disconnect(_queriesDone, ZWaveNetwork.SIGNAL_NODE_QUERIES_COMPLETE)
    #dispatcher.disconnect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
    dispatcher.disconnect(_controllerCommand, ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND)


def _getData(cc):
    """get the data value in the correct format for the specified command class"""
    dataType = str(cc.type)
    if dataType == "Bool":
        return str(cc.data_as_string).lower()   # for some reason, data_as_string isn't always a string, but a bool or somthing else.
    else:
        return cc.data_as_string

