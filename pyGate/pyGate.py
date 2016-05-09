## main file for the gateway application that manages the plugins.

import logging                                                                         #before doing anything else, set the desired logging level, so all modules log correctly.
import logging.config
logging.config.fileConfig('../config/logging.config')

import time
import signal
import sys
from threading import Event

import config
import modules
import cloud
import processors
import att_iot_gateway.att_iot_gateway as IOT                              #provide cloud support

def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)


def on_connected():
    _connectedEvent.set()

_connectedEvent = Event()

try:
    signal.signal(signal.SIGTERM, sigterm_handler)
    config.load()
    IOT.on_connected = on_connected  # so we can wait for starting to run the modules untill we are connected with the broker.
    cloud.connect(modules.Actuate, processors.onAssetValueChanged)
    processors.load(config.processors)
    modules.load(config.modules)
    modules.syncGateway()
    logging.info("waiting for mqtt connection before starting all plugins")
    _connectedEvent.wait()
    _connectedEvent = None  # when we are done we no longer need this event, so remove.Only needed to wait, so plugins can send init values
    modules.run()
    if config.configs.has_option('webServer', 'enabled') and config.configs.get('webServer', 'enabled') == True:    # only load webserver if activated. Not all plugins need this, not all gateways want have a webserver running ex: fifthplay
        import webServer
        webServer.run()
    while 1:
        time.sleep(3)
except (KeyboardInterrupt, SystemExit):
    pass
except:
    logging.exception('unrecoverable error' )
finally:
    logging.info("pyGate shutting down...")
    modules.stop()
    logging.info("pyGate shutdown complete")




