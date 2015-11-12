## main file for the gateway application that manages the plugins.

import time

import config
import modules
from cloud import Cloud

config.load()
cloud = Cloud()
cloud.connect(config)
modules.load(config.modules, cloud)
modules.run()
while True:
    time.sleep(3)


