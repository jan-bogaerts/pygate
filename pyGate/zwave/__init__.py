# main entry for the pyGate plugin that provides support for zwave devices

import logging
import thread
import threading
import openzwave
from openzwave.node import ZWaveNode
from openzwave.value import ZWaveValue
from openzwave.scene import ZWaveScene
from openzwave.controller import ZWaveController
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption
from openzwave.controller import ZWaveController
import time
from louie import dispatcher, All
import json

from gateway import Gateway;
import config
import deviceClasses

_gateway = None                             # provides access to the cloud
_network = None                             # provides access to the zwave network
_readyEvent = threading.Event()             # signaled when the zwave network has been fully started.

_discoveryStateId = 'discoverState'   #id of asset
_hardResetId = 'hardReset'   #id of asset
_softResetId = 'softReset'   #id of asset
_assignRouteId = 'assignRoute'
_controllerStateId = 'controllerState'
_CC_Battery = 0x80


def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _gateway
    _gateway = Gateway(moduleName)
    _setupZWave()


def syncDevices(existing, Full = False):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.
       :param Full: when false, if device already exists, don't update, including assets. When true,
        update all, including assets
    '''
    if _readyEvent.wait(10):                         # wait for a max amount of timeto get the network ready, otherwise we contintue
        for key, node in _network.nodes.iteritems():
            if node.node_id != 1:
                found = next((x for x in existing if x['id'].encode('ascii','ignore') == str(node.node_id)), None)
                if not found:
                    _addDevice(node)
                else:
                    existing.remove(found)              # so we know at the end which ones have to be removed.
                    if Full:
                        _addDevice(node)                # this will also refresh it
        for dev in existing:                        # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
            _gateway.deleteDevice(dev['id'])
    else:
        logging.error('failed to start the network in time, continuing')


def syncGatewayAssets(Full = False):
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    :param Full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    '''
    #don't need to wait for the zwave server to be fully ready, don't need to query it for this call.
    _gateway.addGatewayAsset(_discoveryStateId, 'zwave discovery state', 'add/remove devices to the network', True,  '{"type" :"string", "enum": ["off","include","exclude"]}')
    _gateway.addGatewayAsset(_hardResetId, 'zwave hard reset', 'reset the controller to factory default', True, 'boolean')
    _gateway.addGatewayAsset(_softResetId, 'zwave soft reset', 'reset the controller, but keep network configuration settings', True, 'boolean')
    _gateway.addGatewayAsset(_assignRouteId, 'zwave assign route', 'assign a network return route from a node to another one', True, '{"type":"object", "properties": {"from":{"type": "integer"}, "to":{"type": "integer"} } }')
    _gateway.addGatewayAsset(_controllerStateId, 'zwave controller state', 'the state of the controller', False, '{"type":"string", "enum": ["Normal", "Starting", "Cancel", "Error", "Waiting", "Sleeping", "InProgress", "Completed", "Failed", "NodeOk", "NodeFailed"] }')


def run():
    ''' required
        main function of the plugin module'''
    _readyEvent.wait()
    _connectSignals()
    _network.start()
    logging.info(_gateway._moduleName + ' running')


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''
    node = _network.nodes[int(device)]          # the device Id is received as a string, zwave needs ints...
    if node:
        val = node.values[long(actuator)]
        if val:
            dataType = str(val.type)
            if dataType == 'Bool':
                value = value.lower() == 'true'
            elif dataType == 'Decimal':
                value = float(value)
            elif dataType == 'Integer':
                value = int(value)
            newValue = val.check_data(value)        #checks and possibly does some convertions
            if newValue != None:
                val.data = newValue
            else:
                logging.error('failed to set actuator: ' + actuator + " for device: " + device + ", unknown data type: " + dataType)
        else:
            logging.error("failed to set actuator: can't find actuator " + actuator + " for device " + node)
    else:
        logging.error("failed to  to set actuator: can't find device " + device)

def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    if actuator == _discoveryStateId:               #change discovery state
        if value == 'include':
            _network.controller.add_node()
        elif value == 'exclude':
            _network.controller.remove_node()
        else:
            _network.controller.cancel_command()
            value = 'off'
        _gateway.send(value, None, actuator)
    elif actuator == _hardResetId:                  #reset controller
        _doHardReset()
    elif actuator == _softResetId:                  #reset controller
        logging.info("soft-resetting network")
        _network.controller.soft_reset()
    elif actuator == _assignRouteId:
        params = json.loads(value)
        logging.info("re-assigning route from: " + params['from'] + ", to: " + params['to'])
        _network.controller.begin_command_assign_return_route(params['from'], params['to'])
    else:
        logging.error("zwave: unknown gateway actuator command: " + actuator)


def _doHardReset():
    '''will send a hardware reset command to the controller.
    opzenzwave generates a lot of events during this operation, so louie signals
    (for nodes & value signals) have to be detached during this operation
    '''
    logging.info("resetting network")
    _disconnectSignals()
    dispatcher.connect(_networkReset, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    _network.controller.hard_reset()

def _networkReset():
    '''make certain that all the signals are reconnected.'''
    dispatcher.disconnect(_networkReset, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)  # no longer need to monitor this?
    _connectSignals()
    logging.info("network reset")

def _discoveryCompleted():
    '''called when the discovery process is done'''
    logging.info('discovery done')
    _gateway.send('off', None, _discoveryStateId)

def _setupZWave():
    '''iniializes the zwave network driver'''
    global _network
    options = _buildZWaveOptions()
    _network = ZWaveNetwork(options, log=None)
    thread.start_new_thread(_waitForStartup, ())

def _waitForStartup():
    '''
    waits until the zwave network has been properly initialized (can take a while)
    This is called from another thread, while the zwave is initializing, the rest can continue.
    Once the zwave has been started up, a signal is set so that the main thread.
    At some point, the main thread will do a call to syncGatewayAssets or syncDevices (or run).
    These functions will wait until that signal has been set so that they are certain that the zwave
    server has been init.
    '''
    _waitForAwake()
    _waitForReady()
    _readyEvent.set()

def _connectSignals():
    '''connect to all the louie signals (for values and nodes)'''
    dispatcher.connect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.connect(_nodeEvent, ZWaveNetwork.SIGNAL_NODE_EVENT)
    dispatcher.connect(_nodeNaming, ZWaveNetwork.SIGNAL_NODE_NAMING)
    #dispatcher.connect(_nodeNew, ZWaveNetwork.SIGNAL_NODE_NEW)    #not working
    #dispatcher.connect(_nodeReady, ZWaveNetwork.SIGNAL_NODE_READY)  #not working
    dispatcher.connect(_nodeProtocolInfo, ZWaveNetwork.SIGNAL_NODE_PROTOCOL_INFO)  # not useful
    dispatcher.connect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.connect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    #dispatcher.connect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(_assetValueRefreshed, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.connect(_assetValue, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.connect(_discoveryCompleted, ZWaveController.STATE_COMPLETED)
    dispatcher.connect(_queriesDone, ZWaveNetwork.SIGNAL_NODE_QUERIES_COMPLETE)
    dispatcher.connect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
    dispatcher.connect(_controllerCommand, ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND)

def _disconnectSignals():
    '''disconnects all the louie signals (for values and nodes). This is used
    while reseting the controllers.
    '''
    dispatcher.disconnect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.disconnect(_nodeEvent, ZWaveNetwork.SIGNAL_NODE_EVENT)
    dispatcher.disconnect(_nodeNaming, ZWaveNetwork.SIGNAL_NODE_NAMING)
    #dispatcher.disconnect(_nodeNew, ZWaveNetwork.SIGNAL_NODE_NEW)
    #dispatcher.disconnect(_nodeReady, ZWaveNetwork.SIGNAL_NODE_READY)
    dispatcher.disconnect(_nodeProtocolInfo, ZWaveNetwork.SIGNAL_NODE_PROTOCOL_INFO)
    dispatcher.disconnect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.disconnect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.disconnect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    #dispatcher.disconnect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.disconnect(_assetValueRefreshed, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    dispatcher.disconnect(_assetValue, ZWaveNetwork.SIGNAL_VALUE)
    dispatcher.disconnect(_discoveryCompleted, ZWaveController.STATE_COMPLETED)
    dispatcher.disconnect(_queriesDone, ZWaveNetwork.SIGNAL_NODE_QUERIES_COMPLETE)
    dispatcher.disconnect(_msgCompete, ZWaveNetwork.SIGNAL_MSG_COMPLETE)
    dispatcher.disconnect(_controllerCommand, ZWaveNetwork.SIGNAL_CONTROLLER_COMMAND)

def _buildZWaveOptions():
    '''create the options object to start up the zwave server'''
    if not config.configs.has_option('zwave', 'port'):
        logging.error('zwave configuration missing: port')
        return
    if not config.configs.has_option('zwave', 'logLevel'):
        logging.error('zwave configuration missing: logLevel')
        return
    if not config.configs.has_option('zwave', 'config'):
        logging.error("zwave 'path to configuration files' missing: config")
        return

    port = config.configs.get('zwave', 'port')
    logging.info('zwave server on port: ' + port)
    logLevel = config.configs.get('zwave', 'logLevel')
    logging.info('zwave log level: ' + logLevel)

    options = ZWaveOption(port, config_path=config.configs.get('zwave', 'config'), user_path=".", cmd_line="")
    options.set_log_file("OZW_Log.log")
    options.set_append_log_file(False)
    options.set_console_output(True)
    options.set_save_log_level(logLevel)
    options.set_logging(False)
    options.lock()
    return options

def _waitForAwake():
    '''waits until the zwave network is awakened'''
    time_started = 0
    logging.info("zwave: Waiting for network awaked")
    for i in range(0,300):
        if _network.state >= _network.STATE_AWAKED:
            logging.info("zwave: network awake")
            break
        else:
            time.sleep(1.0)
    if _network.state < _network.STATE_AWAKED:
        logging.error("zwave: Network is not awake but continue anyway")
    logging.info("zwave: Use openzwave library : %s" % _network.controller.ozw_library_version)
    logging.info("zwave: Use python library : %s" % _network.controller.python_library_version)
    logging.info("zwave: Use ZWave library : %s" % _network.controller.library_description)
    logging.info("zwave: Network home id : %s" % _network.home_id_str)
    logging.info("zwave: Controller node id : %s" % _network.controller.node.node_id)
    logging.info("zwave: Controller node version : %s" % (_network.controller.node.version))
    logging.info("zwave: Nodes in network : %s" % _network.nodes_count)

def _waitForReady():
    '''waits until the zwave network is ready'''
    logging.info("zwave: Waiting for network ready")
    for i in range(0,30):
        if _network.state >= _network.STATE_READY:
            logging.info("zwave: network ready")
            break
        else:
            time.sleep(1.0)
    if not _network.is_ready:
        logging.info("zwave: Network is not ready but continue anyway")
    logging.info("zwave: Controller capabilities : %s" % _network.controller.capabilities)
    logging.info("zwave: Controller node capabilities : %s" % _network.controller.node.capabilities)
    logging.info("zwave: Nodes in network : %s" % _network.nodes_count)
    logging.info("zwave: Driver statistics : %s" % _network.controller.stats)

def _getData(cc):
    """get the data value in the correct format for the specified command class"""
    dataType = str(cc.type)
    if dataType == "Bool":
        return str(cc.data_as_string).lower()   # for some reason, data_as_string isn't always a string, but a bool or somthing else.
    else:
        return cc.data_as_string

def _addDevice(node):
    """adds the specified node to the cloud as a device. Also adds all the assets.
    """
    if node.product_name:                       #newly included devices arent queried fully yet, so create with dummy info, update later
        _gateway.addDevice(node.node_id, node.product_name, node.type)
    else:
        _gateway.addDevice(node.node_id, 'unknown', node.type)
    for key, val in node.values.iteritems() :
        try:
            if val.command_class and not str(val.genre) == 'System':                # if not related to a command class, then all other fields are 'none' as well, can't t much with them. System values are not interesting, it's about frames and such (possibly for future debugging...)
                _addAsset(node, val)
        except:
            logging.exception('failed to sync device ' + str(node.node_id) + ' for module ' + _gateway._moduleName + ', asset: ' + str(key) + '.')
    if _CC_Battery in node.command_classes:
        _gateway.addAsset('failed', node.node_id, 'failed', 'true when the battery device is no longer responding and the controller has labeled it as a failed device.', False, 'boolean', 'Secondary')


def _addAsset(node, value):
    lbl = value.label.encode('ascii', 'ignore').replace('"', '\\"')        # make certain that we don't upload any illegal chars, also has to be ascii
    hlp = value.help.encode('ascii', 'ignore').replace('"', '\\"')         # make certain that we don't upload any illegal chars, also has to be ascii
    _gateway.addAsset(value.value_id, node.node_id, lbl, hlp, not value.is_read_only, _getAssetType(node, value), _getStyle(node, value))
    # dont send the data yet, we have a seperate event for this

def _getAssetType(node, val):
    '''extract the asset type from the command class'''

    logging.info("node type: " + val.type)            # for debugging
    dataType = str(val.type)

    type = "{'type': "
    if dataType == 'Bool' or dataType == 'Button':
        type += "'boolean'"
    elif dataType == 'Decimal':
        type += "'number'"
    elif dataType == 'Integer' or dataType == "Byte" or dataType == 'Int' or dataType == "Short":
        type += "'integer'"
    else:
        type = '{"type": "string"'                              #small hack for now.

    if dataType == 'Decimal' or dataType == 'Integer':
        if val.max and val.max != val.min:
            type += ', "maximum": ' + str(val.max)
        if val.min and val.max != val.min:
            type += ', "minimum": ' + str(val.min)
    if val.units:
        type += ', "unit": "' + val.units + '"'
    if val.data_items and isinstance(val.data_items, set):
        type += ', "enum": [' + ', '.join(['"' + y + '"' for y in val.data_items]) + ']'
    return type + "}"

def _getStyle(node, val):
    '''check the value type, if it is the primary cc for the device, set is primary, if it is battery...'''
    if str(val.genre) == 'Config':
        return 'Config'
    elif val.command_class == _CC_Battery:
        return 'Battery'
    else:
        primaryCCs = deviceClasses.getPrimaryCCFor(node.generic, node.specific)
        if primaryCCs:                              # if the dev class has a list of cc's than we can determine primary or secondary, otherwise, it's unknown.
            if val.command_class in primaryCCs:
                return 'Primary'
            return 'Secondary'
    return "Undefined"                  # if we get here, we don't know, so it is undefined.


def _queriesDone(node):
    logging.info('queries done ')
    _addDevice(node)
    _network.controller.cancel_command()        # we also stop discovery after 1 item has been added.

def _msgCompete():
    logging.info('msg done ')

def _controllerCommand(state):
    #logging.info('controller command + ' + str(state))
    _gateway.send(state, None, _controllerStateId)


def _nodeAdded(node):
    logging.info('node added: ' + str(node))
    _addDevice(node)

def _nodeEvent(node, value):
    logging.info('node event: ' + str(node) + ', event: ' + str(value))
    dump(node)

def _nodeNaming(node):
    logging.info('node naming: ' + str(node))
    _addDevice(node)   #we add here agai, cause it seems that from this point on, we have enough info to create the object completely

#def _nodeNew(node):
#    logging.info('node new: ' + str(node))
#    dump(node)

#def _nodeReady(node):
#    logging.info('node ready: ' + str(node))
#    dump(node)

def _nodeProtocolInfo(node):
    logging.info('node protocol info: ' + str(node))
    name= _network.manager.GetNodeType(node.home_id, node.node_id)
    logging.info('node protocol info: ' + name)

def _nodeRemoved(node):
    try:
        logging.info('node removed')
        _gateway.deleteDevice(node.node_id)
    except:
        logging.exception('failed to remove node ' + str(node.node_id) )

def _assetAdded(node, value):
    logging.info('asset added: ' + str(value.value_id))
    #dump(value)
    _addAsset(node, value)

def _assetRemoved(node, value):
    logging.info('asset removed: ' + str(value.value_id))
    dump(node)
    _gateway.deleteAsset(node.node_id, value)

def _assetValue(network, node, value):
    logging.info('asest value: ' + str(value.value_id))
    _gateway.send(_getData(value), node.node_id, value.value_id)

#def _assetValueChanged(network, node, value):
#    logging.info('asset value changed: ' + str(value.value_id))
#    _gateway.send(_getData(value), node.node_id, value.value_id)

def _assetValueRefreshed(network, node, value):
    logging.info('asset value refreshed: ' + str(value.value_id))
    _gateway.send(_getData(value), node.node_id, value.value_id)


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