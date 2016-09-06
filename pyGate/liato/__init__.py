__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


import logging
logger = logging.getLogger('liato')

from gateway import Gateway
import config

BLE = None

_gateway = None


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

def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    '''

def run():
    ''' optional
        main function of the plugin module'''

def stop():
    """ optional
        called when the application is stopped. Perform all the necessary cleanup here"""

def onActuate(actuator, value):
    '''optional
    callback routine for plugins that behave as devices or for plugins that behave as gateways, when the actuator is on the gateway itself.'''


def onDeviceActuate(device, actuator, value):
    '''optional callback routine for plugins that behave as gateways'''