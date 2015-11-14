import logging
from ConfigParser import *
import json
import os.path

modules = []                                    #all the mmodule names that should be loaded
rootConfigFileName = '../config/pygate.config'


def load():
    """Load config data"""
    global modules
    c = ConfigParser()
    if c.read(rootConfigFileName):
        logging.info("loading " + rootConfigFileName)
        modules = c.get('general', 'modules')
        logging.info("modules: " + str(modules))
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

