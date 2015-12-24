## main file for the gateway application that manages the plugins.

import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

import time

import config
import modules
import cloud
import processors
import webServer


config.load()
cloud.connect(modules.Actuate, processors.onAssetValueChanged)
webServer.run()                                             # we need web support before we can activate devices -> some might need it.
processors.load(config.processors)
modules.load(config.modules)
modules.syncGatewayAssets()
modules.syncDevices()
modules.run()
while True:
    time.sleep(3)

