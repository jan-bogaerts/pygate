# main entry for the pyGate plugin that provides support for zwave devices

import logging
import thread
import threading
import openzwave

from gateway import Gateway;
import config

_gateway = None                             # provides access to the cloud
_network = None                             # provides access to the zwave network
_readyEvent = threading.Event()             # signaled when the zwave network has been fully started.

_discoveryStateId = 'discovery_state'   #id of asset

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
    _readyEvent.wait()
    for node in _network.nodes:
        found = next(x for x in existing if x['id'] == node.node_id)
        if not found:
            _addDevice(node)
        else:
            existing.remove(found)              # so we know at the end which ones have to be removed.
    for dev in existing:                        # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
        _gateway.deleteDevice(dev['id'])

def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    '''
    #don't need to wait for the zwave server to be fully ready, don't need to query it for this call.
    _gateway.addGatewayAsset(_discoveryStateId, 'discovery state', 'add/remove devices to the network', '{"enum":["off"|"include"|"exclude"]}')

def run():
    ''' required
        main function of the plugin module'''
    _readyEvent.wait()


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''


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
    dispatcher.connect(_nodeAdded, ZWaveNetwork.SIGNAL_NODE_ADDED)     #set up callback handling -> for when node is added/removed or value changed.
    dispatcher.connect(_nodeRemoved, ZWaveNetwork.SIGNAL_NODE_REMOVED)
    dispatcher.connect(_assetAdded, ZWaveNetwork.SIGNAL_VALUE_ADDED)
    dispatcher.connect(_assetRemoved, ZWaveNetwork.SIGNAL_VALUE_REMOVED)
    dispatcher.connect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_CHANGED)
    dispatcher.connect(_assetValueChanged, ZWaveNetwork.SIGNAL_VALUE_REFRESHED)
    _readyEvent.set()

def _buildZWaveOptions(): 
    '''create the options object to start up the zwave server'''
    port = config.configs.get('zwave', 'port')
    logging.info('zwave server on port: ' + port)
    logLevel = config.configs.get('zwave', 'logLevel')
    logging.info('zwave log level: ' + logLevel)

    options = ZWaveOption(port, config_path=config.configPath, user_path=".", cmd_line="")
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
    for i in range(0,300):
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
    _gateway.addDevice(node.node_id, node.product_name, "")
    for cmd in network.nodes[node].command_classes:
        for val in network.nodes[node].get_values_for_command_class(cmd) :
            _gateway.addAsset(val, node.node_id, node.values[val].label, node.values[val].label.help, not node.values[val].is_read_only, getAssetType(node, val), getStyle(node, val))
            _gateway.send(node.values[val].data_as_string, node.node_id, val)
    

def _getAssetType(node, val):
    '''extract the asset type from the command class'''

    print "node type: " + node.values[val].type            # for debugging

    type = "{'type': 'string'"                              #small hack for now.

    if node.values[val].max:
        type += ', "maximum": ' + node.values[val].max
    if node.values[val].min:
        type += ', "minimum": ' + node.values[val].min
    if node.values[val].units:
        type += ', "unit": ' + node.values[val].units
    
    return type + "}"
    

def _nodeAdded(network, node):
    _addDevice(node)

def _nodeRemoved(network, node):
    _gateway.deleteDevice(node.node_id)

def _assetAdded(network, node, val):
    _gateway.addAsset(val, node.node_id, node.values[val].label, node.values[val].label.help, not node.values[val].is_read_only, getAssetType(node, val), getStyle(node, val))
    _gateway.send(node.values[val].data_as_string, node.node_id, val)

def _assetRemoved(network, node, val):
    _gateway.deleteAsset(node.node_id, val)