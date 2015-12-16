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
import time
from louie import dispatcher, All
import json

from gateway import Gateway;
import config

_gateway = None                             # provides access to the cloud
_network = None                             # provides access to the zwave network
_readyEvent = threading.Event()             # signaled when the zwave network has been fully started.

_discoveryStateId = 'discoverState'   #id of asset
_hardResetId = 'hardReset'   #id of asset
_softResetId = 'softReset'   #id of asset
_assignRouteId = 'assignRoute'
_cancelCommandId = 'cancelCommand'


def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _gateway
    _gateway = Gateway(moduleName)
    _setupZWave()


def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.
    '''
    if _readyEvent.wait():                         # wait for 5 seconds to get the network ready, otherwise we contintue
        for key, node in _network.nodes.iteritems():
            if node.node_id != 1:
                found = next((x for x in existing if x['id'].encode('ascii','ignore') == str(node.node_id)), None)
                if not found:
                    _addDevice(node)
                else:
                    existing.remove(found)              # so we know at the end which ones have to be removed.
        for dev in existing:                        # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
            _gateway.deleteDevice(dev['id'])
    else:
        logging.error('failed to start the network in time, continuing')


def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    '''
    #don't need to wait for the zwave server to be fully ready, don't need to query it for this call.
    _gateway.addGatewayAsset(_discoveryStateId, 'discovery state', 'add/remove devices to the network', True,  '{"type" :"string", "enum": ["off","include","exclude"]}')
    _gateway.addGatewayAsset(_hardResetId, 'hard reset', 'reset the controller to factory default', True, 'boolean')
    _gateway.addGatewayAsset(_softResetId, 'soft reset', 'reset the controller, but keep network configuration settings', True, 'boolean')
    _gateway.addGatewayAsset(_assignRouteId, 'assign route', 'assign a network return route from a node to another one', True, '{"type":"object", "properties": {"from":{"type": "integer"}, "to":{"type": "integer"} } }')
    _gateway.addGatewayAsset(_cancelCommandId, 'cancel command', 'cancel the previously issued command', True, 'boolean')


def run():
    ''' required
        main function of the plugin module'''
    _readyEvent.wait()


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''
    node = _network.nodes[device]
    if node:
        val = node.values[actuator]
        if val:
            cc = val.command_class                  # get the command class for
            print "to do: send actual command"
        else:
            logging.error("failed to set asset value: can't find asset " + actuator + " for device " + node)
    else:
        logging.error("failed to  to set asset value: can't find device " + device)

def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    if actuator == _discoveryStateId:               #change discovery state
        if value == 'include':
            _network.controller.begin_command_add_device()
        elif value == 'exclude':
            _network.controller.begin_command_remove_device()
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
    elif actuator == _cancelCommandId:
        logging.info("cancelling operation")
        _network.controller.cancel_command()
        _gateway.send('off', None, _discoveryStateId)
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
    _connectSignals()
    _readyEvent.set()

def _connectSignals():
    '''connect to all the louie signals (for values and nodes)'''
    dispatcher.connect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.connect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.connect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)

def _disconnectSignals():
    '''disconnects all the louie signals (for values and nodes). This is used
    while reseting the controllers.
    '''
    dispatcher.disconnect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.disconnect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.disconnect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.disconnect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.disconnect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.disconnect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)

def _buildZWaveOptions():
    '''create the options object to start up the zwave server'''
    if not config.configs.has_option('zwave', 'port'):
        logging.error('zwave configuration missing: port')
        return
    if not config.configs.has_option('zwave', 'logLevel'):
        logging.error('zwave configuration missing: logLevel')
        return
    if not config.configs.has_option('zwave', 'config'):
        logging.error('zwave path to configuration files missing: config')
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


def _addDevice(node):
    '''adds the specified node to the cloud as a device. Also adds all the assets.'''
    _gateway.addDevice(node.node_id, node.product_name, node.type)
    for key, val in node.values.iteritems() :
        try:
            _gateway.addAsset(key, node.node_id, val.label.encode('ascii','ignore'), val.help.encode('ascii','ignore'), not val.is_read_only, _getAssetType(node, val), _getStyle(node, val))
            _gateway.send(node.values[val].data_as_string, node.node_id, val)
        except:
            logging.exception('failed to sync device ' + str(node.node_id) + ' for module ' + _gateway._moduleName + ', asset: ' + str(key) + '.')
    if node.is_sleeping:
        _gateway.addAsset('failed', node.node_id, 'failed', 'true when the battery device is no longer responding and the controller has labeled it as a failed device.', False, 'boolean', 'Secondary')


def _getAssetType(node, val):
    '''extract the asset type from the command class'''

    logging.info("node type: " + val.type)            # for debugging

    type = "{'type': "
    if val.type == 'Bool':
        type += "'string'"
    elif val.type == 'Decimal':
        type += "'number'"
    elif val.type == 'Integer':
        type += "'integer'"
    else:
        type = "{'type': 'string'"                              #small hack for now.
    if val.max and val.max != val.min:
        type += ', "maximum": ' + val.max
    if val.min and val.max != val.min:
        type += ', "minimum": ' + val.min
    if val.units:
        type += ', "unit": ' + val.units
    return type + "}"

def _getStyle(node, val):
    '''check the value type, if it is the primary cc for the device, set is primary, if it is battery...'''
    #todo: finish this off.
    return "Undefined"

def _nodeAdded(node):
    _addDevice(node)

def _nodeRemoved(node):
    _gateway.deleteDevice(node.node_id)

def _assetAdded(node, val):
    _gateway.addAsset(val, node.node_id, node.values[val].label, node.values[val].label.help, not node.values[val].is_read_only, getAssetType(node, val), getStyle(node, val))
    _gateway.send(node.values[val].data_as_string, node.node_id, val)

def _assetRemoved(node, val):
    _gateway.deleteAsset(node.node_id, val)

def _assetValueChanged(node, val):
    _gateway.send(node.values[val].data_as_string, node.node_id, val)