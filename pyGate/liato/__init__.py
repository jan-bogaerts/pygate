__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


import logging
logger = logging.getLogger('liato')

from core import config
import engine

BLE = None
_isRunning = True

def connectToGateway(moduleName):
    """
    optional
        called when the system connects to the cloud.
    :param moduleName: name that should be used for this module
    :return:
    """
    global BLE
    longRangeBle = config.getConfig("liato", "long range BLE", True)
    if longRangeBle == True:
        BLE = __import__("WR_BLE_Communication")
        logging.info("using wide range bluetooth communication")
    else:
        BLE = __import__("BLE_Communication")
        logging.info("using regular bluetooth communication")

    BLE.loadBLESettings()
    BLE.connect()
    engine.connect(moduleName)

def syncDevices(existing, full=False):
    """
        optional
        allows a module to synchronize it's device list.
        :param existing: the list of devices that are already known in the cloud for this module.
        :param full: when false, if device already exists, don't update, including assets. When true,
         update all, including assets
    :param existing: list of existing devices
    :param full: Should there be a full refresh or just a quick scan that all is ok.
    :return:
    """
    engine.storeDevices(existing)

def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    '''
    engine.createGatewayAssets()

def run():
    ''' optional
        main function of the plugin module'''
    while _isRunning:
        try:
            ob = BLE.get_report()
            if ob is not None:
                engine.procLine(ob)
            error = BLE.get_error()
            if error:
                engine.sendError(error)
                while error:
                    error = BLE.get_error()
        except Exception as e:
            logging.exception("failed to process incoming BLE line")
            engine.sendError(str(e))

def stop():
    """ optional
        called when the application is stopped. Perform all the necessary cleanup here"""
    global _isRunning
    _isRunning = False

def onActuate(actuator, value):
    '''optional
    callback routine for plugins that behave as devices or for plugins that behave as gateways, when the actuator is on the gateway itself.'''
    logger.error("actuators not yet supported: {}, value: {}".format(actuator, value))


def onDeviceActuate(device, actuator, value):
    '''optional callback routine for plugins that behave as gateways'''
    logger.error("actuators not yet supported on devices: {}, actuator: {},  value: {}".format(device, actuator, value))