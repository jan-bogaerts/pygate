__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('mbus')
import time
from datetime import datetime
from mbus import Mbus, MBusScanner

from gateway import Gateway
import config


_gateway = None
_mbus = None
_isScanningId = "isscanning"
_isRunning = True
_sampleEvery = 300                         # the frequency in seconds that the system needs to request data from the devices.

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _gateway, _mbus, _sampleEvery
    _gateway = Gateway(moduleName)
    _mbus = Mbus(_gateway)
    if config.configs.has_option('mbus', 'sample frequency'):
        _sampleEvery = config.configs.get('mbus', 'sample frequency')

def syncDevices(existing, full=False):
    '''optional
        allows a module to synchronize it's device list.
        :param existing: the list of devices that are already known in the cloud for this module.
        :param full: when false, if device already exists, don't update, including assets. When true,
         update all, including assets
     '''
    scanner = MBusScanner(_mbus, existing, full, _syncDevices)
    scanner.start()


def syncGatewayAssets(full=False):
    _gateway.addGatewayAsset(_isScanningId, 'mbus is scanner', 'activate/stop scanning mode on mbus for discovering new devices', True, 'boolean')

def stop():
    """"called when the application terminates.  Allows us to clean up the hardware correctly, so we cn be restarted without (cold) reboot"""
    global _isRunning
    _isRunning = False
    logger.info("stopping mbus network")
    _mbus.stop()

def run():
    while _isRunning:
        try:
            startTime = datetime.now()
            _mbus.sample()
            sleepTime = _sampleEvery - (datetime.now() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)
        except Exception as e:  # in case of an xbee error: print it and try to continue
            logger.exception("value error occured")


def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    if actuator == _isScanningId:  # change discovery state
        if bool(value) == True:
            scanner = MBusScanner(_mbus, None, True, _syncDevices)
            scanner.start()
    else:
        logger.error("mbus: unknown gateway actuator command: " + actuator)

def _syncDevices(existing, full, found):
    """go over the list of device id's that were found, if the device does
    not yet exist in the platform, create it
    This is a callback for the mbus object's scan method. It is called from anotehr thread
    :param existing: the list of already known to exist devices. If None, cloud will be
     queried for existance.
    :param full: When true, all assets will also be (re)created (data packet needs to be retrieved
    :param found: a dictionary of devices  that was found  key = device id, value = (manufacturoer, medium, assets, all is included)
    """
    for key, dev in found:
        existingDev = next((x for x in existing if x['id'].encode('ascii', 'ignore') == str(key)), None)
        if not found:
            addDevice(key, dev)
        else:
            existing.remove(existingDev)  # so we know at the end which ones have to be removed.
            if full:
                addDevice(key, dev)  # this will also refresh it
    for dev in existing:  # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
        try:
            _gateway.deleteDevice(dev['id'])
        except:
            logger.error("failed to delete device on cloud: {}".format(dev))

def addDevice(id, device):
    """adds the device and all it's assets to the cloud"""
    try:
        name = "{} {} meter".format(device.manufacturer, device.medium_type)
        desc = "{}, version: {}".format(name, device.version)
        _gateway.addDevice(id, name, desc)

        _gateway.addAsset('status', id, 'status', 'status', False, 'number')
        _gateway.send(device.status, 'status', id)

        _gateway.addAsset('manufacturer', id, 'manufacturer', 'manufacturer', False, 'string')
        _gateway.send(device.manufacturer, 'manufacturer', id)

        _gateway.addAsset('version', id, 'version', 'version', False, 'string')
        _gateway.send(device.version, 'version', id)

        _gateway.addAsset('id_bcd', id, 'id_bcd', 'id_bcd', False, 'string')
        _gateway.send(device.id_bcd, 'id_bcd', id)

        for asset in device.record:
            if asset.is_numeric:
                _gateway.addAsset(asset.storage_number, id, asset.unit,asset.unit, False, 'number')
            else:
                _gateway.addAsset(asset.storage_number, id, asset.unit, asset.unit, False, 'string')
            _gateway.send(asset.value, asset.storage_number, id)
    except:
        logger.exception("failed to add device id: {}, value: ".format(id, device))