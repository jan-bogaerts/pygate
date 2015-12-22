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
from louie import dispatcher

import json

import config
import deviceEvents as events
import manager
import networkMonitor

#_readyEvent = threading.Event()             # signaled when the zwave network has been fully started.


_hardResetId = 'hardReset'   #id of asset
_softResetId = 'softReset'   #id of asset
_assignRouteId = 'assignRoute'


def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    manager.init(moduleName)
    _setupZWave()


def syncDevices(existing, Full = False):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.
       :param Full: when false, if device already exists, don't update, including assets. When true,
        update all, including assets
    '''
    #if _readyEvent.wait(10):                         # wait for a max amount of timeto get the network ready, otherwise we contintue
    #    manager.syncDevices(existing, Full)
    #else:
    #    logging.error('failed to start the network in time, continuing')
    manager.syncDevices(existing, Full)


def syncGatewayAssets(Full = False):
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    :param Full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    '''
    #don't need to wait for the zwave server to be fully ready, don't need to query it for this call.
    manager.gateway.addGatewayAsset(manager.discoveryStateId, 'zwave discovery state', 'add/remove devices to the network', True,  '{"type" :"string", "enum": ["off","include","exclude"]}')
    manager.gateway.addGatewayAsset(_hardResetId, 'zwave hard reset', 'reset the controller to factory default', True, 'boolean')
    manager.gateway.addGatewayAsset(_softResetId, 'zwave soft reset', 'reset the controller, but keep network configuration settings', True, 'boolean')
    manager.gateway.addGatewayAsset(_assignRouteId, 'zwave assign route', 'assign a network return route from a node to another one', True, '{"type":"object", "properties": {"from":{"type": "integer"}, "to":{"type": "integer"} } }')
    manager.gateway.addGatewayAsset(manager.controllerStateId, 'zwave controller state', 'the state of the controller', False, '{"type":"string", "enum": ["Normal", "Starting", "Cancel", "Error", "Waiting", "Sleeping", "InProgress", "Completed", "Failed", "NodeOk", "NodeFailed"] }')


def run():
    ''' required
        main function of the plugin module'''
    #_readyEvent.wait()
    events.connectSignals()
    networkMonitor.connectNetworkSignals()
    manager.start()


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''
    node = manager.network.nodes[int(device)]          # the device Id is received as a string, zwave needs ints...
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
    if actuator == manager.discoveryStateId:               #change discovery state
        if value == 'include':
            events.sendAfterWaiting = events.DataMessage(value, actuator)
            manager.network.controller.add_node()
        elif value == 'exclude':
            events.sendAfterWaiting = events.DataMessage(value, actuator)
            manager.network.controller.remove_node()
        else:
            events.sendOnDone = events.DataMessage('off', actuator)
            manager.network.controller.cancel_command()
    elif actuator == _hardResetId:                  #reset controller
        _doHardReset()
    elif actuator == _softResetId:                  #reset controller
        logging.info("soft-resetting network")
        manager.network.controller.soft_reset()
    elif actuator == _assignRouteId:
        params = json.loads(value)
        logging.info("re-assigning route from: " + params['from'] + ", to: " + params['to'])
        manager.network.controller.begin_command_assign_return_route(params['from'], params['to'])
    else:
        logging.error("zwave: unknown gateway actuator command: " + actuator)


def _doHardReset():
    '''will send a hardware reset command to the controller.
    opzenzwave generates a lot of events during this operation, so louie signals
    (for nodes & value signals) have to be detached during this operation
    '''
    logging.info("resetting network")
    events.disconnectSignals()
    dispatcher.connect(_networkReset, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    manager.network.controller.hard_reset()

def _networkReset():
    '''make certain that all the signals are reconnected.'''
    dispatcher.disconnect(_networkReset, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)  # no longer need to monitor this?
    events.connectSignals()
    logging.info("network reset")

def _setupZWave():
    '''iniializes the zwave network driver'''
    options = _buildZWaveOptions()
    manager.network = ZWaveNetwork(options, log=None)

#def _waitForStartup():
#    '''
#    waits until the zwave network has been properly initialized (can take a while)
#    This is called from another thread, while the zwave is initializing, the rest can continue.
#    Once the zwave has been started up, a signal is set so that the main thread.
#    At some point, the main thread will do a call to syncGatewayAssets or syncDevices (or run).
#    These functions will wait until that signal has been set so that they are certain that the zwave
#    server has been init.
#    '''
#    manager.waitForAwake()
#    manager.waitForReady()
#    _readyEvent.set()


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

