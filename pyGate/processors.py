##########################################################
# manage all the dynamically loaded modules of the gateway.
# a module manages devices and or assets

__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging

processors = {}


def load(processorNames):
    """Loads all the gateway modules"""
    global processors
    logging.info("loading processors")
    processors = dict(zip(processorNames, map(__import__, processorNames)))       # load the modules and put them in a dictionary, key = the name of the module.


def onAssetValueChanged(module, device, asset, value):
    for key, mod in processors.iteritems():
        if mod.onAssetValueChanged:
            logging.info("running processor " +  key)
            try:
                mod.onAssetValueChanged(module, device, asset, value)
            except:
                logging.exception('failed to run procesor ' + key + ' to gateway.')