import logging
from ConfigParser import *
import json
import os.path

modules = []                                    #all the mmodule names that should be loaded
gatewayId = None                                # the id of the gateway 
clientId = None                                 #authentication value
clientKey = None                                #authentication value
rootConfigFileName = '../config/pygate.config'


def load():
    """Load config data"""
    global modules, gatewayId, clientId,clientKey
    c = ConfigParser()
    if c.read(rootConfigFileName):
        logging.info("loading " + rootConfigFileName)
        
        modules = c.get('general', 'modules')
        logging.info("modules: " + str(modules))
        
        gatewayId = c.get('general', 'gatewayId')
        logging.info("gatewayId: " + gatewayId)

        clientId = c.get('general', 'clientId')
        logging.info("clientId: " + clientId)

        clientKey = c.get('general', 'clientKey')
        logging.info("clientKey: " + clientKey)
    else:
        logging.error('failed to load ' + rootConfigFileName)

def load(fileName, asJson = False):
    """loads the config file from the correct directory and returns a ConfigParser object that can be used to load
       config data"""
    c = ConfigParser()
    fileName = '../config/' + fileName
    if not os.path.isfile(fileName):
        logging.error('file not found ' + fileName)
    if not asJson:
        if c.read(fileName):
            logging.info("loading " + fileName)
            return c
        else:
            logging.error('failed to load ' + fileName)
            return None
    else:
        with open(fileName) as json_file:
            logging.info("loading " + fileName)
            json_data = json.load(json_file)
            return json_data

def save():
    '''
    saves the global config data to the global config file. Called when config params have
    been changed, like the gatewayId
    '''
    c = ConfigParser()
    c.add_section('general')
    c.set('general', 'modules', modules)
    c.set('general', 'gatewayId', gatewayId)
    c.set('general', 'clientId', clientId)
    c.set('general', 'clientKey', clientKey)
    with open(rootConfigFileName, 'w') as f:
        c.write(f)
