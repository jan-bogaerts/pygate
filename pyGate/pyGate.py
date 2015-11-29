## main file for the gateway application that manages the plugins.

import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

import time

import config
import modules
import cloud
import associations


config.load()
associations.load()
cloud.connect(modules.Actuate, associations.onAssetUpdated)
modules.load(config.modules)
modules.syncGatewayAssets()
modules.syncDevices()
modules.run()
while True:
    time.sleep(3)

