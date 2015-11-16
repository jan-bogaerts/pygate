## main file for the gateway application that manages the plugins.

import logging
logging.getLogger().setLevel(logging.INFO)                                                                          #before doing anything else, set the desired logging level, so all modules log correctly.

import time

import config
import modules
import cloud


def onActuate(module, device, actuator, value):
    '''called when an actuator command arrives from the cloud'''
    mod = modules.modules[module];
    if device:
        if mod.onDeviceActuate:                                     # it's a gateway
            mod.onDeviceActuate(device, actuator, value)
        elif mod.onActuate:                                         # it'sa regular device
            mod.onActuate(actuator, value)
    else:
        if mod.onActuate:
            mod.onActuate(actuator, value)


config.load()
cloud.connect(config, onActuate)
modules.load(config.modules)
modules.syncGatewayAssets()
modules.syncDevices()
modules.run()
while True:
    time.sleep(3)

