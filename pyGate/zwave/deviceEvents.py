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

class DataMessage:
    """use this class to create objects for sendAfterWaiting and sendAfterDone"""
    def __init__(self, value, asset):
        """
        :param value: the value to send
        :param asset: the asset to send the value for
        """
        self.value = value
        self.asset = asset

sendAfterWaiting = None                             # this data structure contains the asset + it's value that should be sent to to the cloud when the controller's state becomes 'waiting'
sendOnDone = None                                   # this data structure contains the asset + it's value that should be sent to to the cloud when the controller's state becomes 'Completed', Cancel, Error or Failed

def _queriesDone(node):
    logging.info('queries done ')
    manager.addDevice(node)
    manager.network.controller.cancel_command()        # we also stop discovery after 1 item has been added.

def _msgCompete():
    logging.info('msg done ')

def _controllerCommand(state):
    try:
        #logging.info('controller command + ' + str(state))
        global sendOnDone, sendAfterWaiting
        manager.gateway.send(state, None, manager.controllerStateId)
        if state == 'Waiting' and sendAfterWaiting:
            'send after waiting'
            manager.gateway.send(sendAfterWaiting.value, None, sendAfterWaiting.asset)
            sendAfterWaiting = None
        elif sendOnDone and state in ['Completed', 'Cancel', 'Error', 'Failed']:
            'send after done'
            manager.gateway.send(sendOnDone.value, None, sendOnDone.asset)
            sendOnDone = None
        #if state == 'Error':
        #    networkMonitor.restartNetwork()
    except:
        logging.exception('failed to process controller command ' + state )


def _nodeAdded(node):
    try:
        global sendOnDone
        if node.node_id != 1:                                                               # after a hard reset, an event is raised to add the 1st node, which is the controller, we don't add that as a device, too confusing for the user, that is the gateway.
            logging.info('node added: ' + str(node))
            manager.addDevice(node)                                                         # add from here, could be that we never get 'nodeNaming' event and that this is the only 'addDevice' that gets called
            sendOnDone = DataMessage('off', manager.discoveryStateId)
            manager.network.controller.cancel_command()                                     # we need to stop the include process cause a device has been added
    except:
        logging.exception('failed to add node ' + str(node) )

def _nodeNaming(node):
    try:
        logging.info('node naming: ' + str(node))
        manager.addDevice(node)                         #we add here again, cause it seems that from this point on, we have enough info to create the object completely. Could be that 'nodeAdded' was not called?
    except:
        logging.exception('failed to remove node ' + str(node) )

def _nodeRemoved(node):
    try:
        global sendOnDone
        logging.info('node removed: ' + str(node))
        sendOnDone = DataMessage('off', manager.discoveryStateId)
        manager.network.controller.cancel_command()                                     # we need to stop the include process cause a device has been removed
        manager.gateway.deleteDevice(str(node.node_id))
    except:
        logging.exception('failed to remove node ' + str(node) )

def _assetAdded(node, value):
    try:
        logging.info('asset added: ' + str(value))
        #dump(value)
        manager.addAsset(node, value)
    except:
        logging.exception('failed to add asset for node: ' + str(node) + ', asset: ' + str(value) )

def _assetRemoved(node, value):
    try:
        logging.info('asset removed: ' + str(value.value_id))
        # dump(node)
        manager.gateway.deleteAsset(node.node_id, value)
    except:
        logging.exception('failed to remove asset for node: ' + str(node) + ', asset: ' + str(value) )

def _assetValue(node, value):
    try:
        logging.info('asest value: ' + str(value))
        manager.gateway.send(_getData(value), node.node_id, value.value_id)
    except:
        logging.exception('failed to process asset value for node: ' + str(node) + ', asset: ' + str(value) )

def _assetValueRefreshed(node, value):
    try:
        logging.info('asset value refreshed: ' + str(value))
        manager.gateway.send(_getData(value), node.node_id, value.value_id)
    except:
        logging.exception('failed to process asset value refresh for node: ' + str(node) + ', asset: ' + str(value) )

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
            logging.exception('failed to print device ' )


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
    dispatcher.connect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
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
    dispatcher.disconnect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
    dispatcher.disconnect(_controllerCommand, ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND)


def _getData(cc):
    """get the data value in the correct format for the specified command class"""
    dataType = str(cc.type)
    if dataType == "Bool":
        return str(cc.data_as_string).lower()   # for some reason, data_as_string isn't always a string, but a bool or somthing else.
    else:
        return cc.data_as_string

