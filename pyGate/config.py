import logging
from ConfigParser import *
import json
import os.path

configs = None                                      #provides access to the configParser object for plug in modules

modules = []                                        #all the mmodule names that should be loaded
gatewayId = None                                    # the id of the gateway 
clientId = None                                     #authentication value
clientKey = None                                    #authentication value

configPath = '../config/'                           # the path to the folder that contains all the configs
rootConfigFileName = configPath + 'pygate.config'   # the path and filename of the main config file


def load():
    """Load config data"""
    global configs, modules, gatewayId, clientId,clientKey
    configs = ConfigParser()
    if configs.read(rootConfigFileName):
        logging.info("loading " + rootConfigFileName)
        
        if configs.has_option('general', 'modules'):
            modulesStr = configs.get('general', 'modules')
            logging.info("modules: " + str(modulesStr))
            modules = modulesStr.split(';')
        if configs.has_option('general', 'gatewayId'):
            gatewayId = configs.get('general', 'gatewayId')
            logging.info("gatewayId: " + gatewayId)
        if configs.has_option('general', 'clientId'):
            clientId = configs.get('general', 'clientId')
            logging.info("clientId: " + clientId)
        if configs.has_option('general', 'clientKey'):
            clientKey = configs.get('general', 'clientKey')
            logging.info("clientKey: " + clientKey)
    else:
        logging.error('failed to load ' + rootConfigFileName)

def loadConfig(fileName, asJson = False):
    """loads the config file from the correct directory and returns a ConfigParser object that can be used to load
       config data"""
    fileName = '../config/' + fileName
    if not os.path.isfile(fileName):
        logging.error('file not found ' + fileName)
    if not asJson:
        c = ConfigParser()
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
    global configs
    configs = ConfigParser()
    configs.add_section('general')
    configs.set('general', 'modules', modules)
    configs.set('general', 'gatewayId', gatewayId)
    configs.set('general', 'clientId', clientId)
    configs.set('general', 'clientKey', clientKey)
    with open(rootConfigFileName, 'w') as f:
        configs.write(f)
