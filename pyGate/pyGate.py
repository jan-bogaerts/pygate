## main file for the gateway application that manages the plugins.

import logging                                                                         #before doing anything else, set the desired logging level, so all modules log correctly.
import logging.config
logging.config.fileConfig('../config/logging.config')

import time
import signal
import sys

import config
import modules
import cloud
import processors
import webServer

def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)

try:
    signal.signal(signal.SIGTERM, sigterm_handler)
    config.load()
    cloud.connect(modules.Actuate, processors.onAssetValueChanged)
    processors.load(config.processors)
    modules.load(config.modules)
    modules.syncGatewayAssets()
    modules.syncDevices()
    modules.run()
    webServer.run()
    while True:
        time.sleep(3)
except:
    logging.exception('unrecoverable error' )
finally:
    logging.info("pyGate shutting down...")
    modules.stop()



