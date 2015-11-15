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
    print "Waiting for network awaked"
    for i in range(0,300):
        if network.state>=network.STATE_AWAKED:
            print(" done")
            break
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1.0)
    if network.state<network.STATE_AWAKED:
        print "Network is not awake but continue anyway"

def _waitForReady():
    '''waits until the zwave network is ready'''