## main file for the gateway application that manages the plugins.

import logging                                                                         #before doing anything else, set the desired logging level, so all modules log correctly.
import logging.config
logging.config.fileConfig('../config/logging.config')

import time

import config
import modules
import cloud
import processors
import webServer

try:
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



