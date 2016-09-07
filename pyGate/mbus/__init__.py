__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('mbus')
from threading import Event
from meterbus import Mbus, MBusScanner
import thread                                   # to stop the application

from core.gateway import Gateway
from core import config

_gateway = None
_mbus = None
_wakeUpEvent = Event()
_isRunning = True
_scanner = None
'used to scan for new or removed devices'

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _gateway, _mbus
    _gateway = Gateway(moduleName)
    _mbus = Mbus(_gateway)
    meterbus.DefaultSamplingFrequency = int(
        config.getConfig("mbus", "sample frequency", meterbus.DefaultSamplingFrequency))
    logger.info("using default sample frequency: {}".format(meterbus.DefaultSamplingFrequency))

def syncDevices(existing, full=False):
    '''optional
        allows a module to synchronize it's device list.
        :param existing: the list of devices that are already known in the cloud for this module.
        :param full: when false, if device already exists, don't update, including assets. When true,
         update all, including assets
     '''
    if _mbus:
        if full == True:
            scanner = MBusScanner(_mbus, existing, full, _syncDevicesCallback)
            scanner.start()
        else:
            _mbus.loadDevicesFromCloud(existing)
    else:
        logger.error("failed to sync mbus devices: mbus was not initialized properly")


def syncGatewayAssets():
    _gateway.addGatewayAsset(meterbus.isScanningId, 'mbus is scanning', 'activate/stop scanning mode on mbus for discovering new devices', True, 'boolean')
    _gateway.addGatewayAsset(meterbus.scanPos, 'mbus scan position', 'current scanning position', False, '{"type" :"integer", "minimum": 0, "maximum":250}')
    _gateway.addGatewayAsset(meterbus.baudrate, 'mbus baudrate', 'the communication speed with the devices. Note: device will be rebooted after change', True, 'integer')
    _gateway.addGatewayAsset(meterbus.lastError, 'mbus last error', 'last error produced by the m-bus protocol', False, 'string')

def stop():
    """"called when the application terminates.  Allows us to clean up the hardware correctly, so we cn be restarted without (cold) reboot"""
    global _isRunning
    _isRunning = False
    _wakeUpEvent.set()                  # wake up the thread if it was sleeping
    logger.info("stopping mbus network")
    if _mbus:
        _mbus.stop()
    if _scanner:
        _scanner.stop = True

def run():
    global _isRunning
    _gateway.send("false", None, meterbus.isScanningId)
    baudRate = config.getConfig('mbus', 'baudrate', None)
    if baudRate:
        _gateway.send(baudRate, None, meterbus.baudrate)
    inError = False                                             # don't swamp the log with the same error
    while _isRunning:
        try:
            if _mbus:                                           # could be that something went wrong loading the mbus module, don't want to swamp the log
                sleepTime = _mbus.sample()
            else:
                sleepTime = meterbus.DefaultSamplingFrequency
                if inError == False:
                    logger.error("Failed to query mbus devices: mbus protocol was not properly intialized")
                    inError = True
            if sleepTime > 0:
                logger.info("sleep for: {}".format(sleepTime))
                _wakeUpEvent.wait(sleepTime)
            inError = False
        except:              # in case of a generic error: print it and try to continue
            if inError == False:
                logger.exception("Failed to query mbus devices")
            inError = True


def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    global _scanner
    if actuator == meterbus.isScanningId:  # change discovery state
        if value.lower() == 'true':
            if not _scanner:
                _scanner = MBusScanner(_mbus, None, False, _syncDevicesCallback)     # don't do a full scan, we only want to find new devices, existing devices should remain -> dont' want to loose prev values for existing stuff.
                _scanner.start()
            else:
                _gateway.send("Scanner is still running", None, meterbus.lastError)
        elif value.lower() == 'false' and _scanner:
            _scanner.stop = True
            _scanner = None
    elif actuator == meterbus.baudrate:
        config.configs.set('mbus', 'baudrate', value)
        config.save()
        thread.interrupt_main()                                                 # stop the application, we need to restart the entire app for this to work (full init required)
    else:
        logger.error("mbus: unknown gateway actuator command: " + actuator)

def onDeviceActuate(device, actuator, value):
    """process new value for device asset"""
    if actuator == "sample_frequency":
        _mbus._devicesLock.acquire()
        try:
            dev = _mbus._devices[int(device)]
            if dev:
                dev.sampleFreq = value
                _gateway.send(value, device, actuator)
        finally:
            _mbus._devicesLock.release()

def _syncDevicesCallback(existing, full, found):
    """go over the list of device id's that were found, if the device does
    not yet exist in the platform, create it
    This is a callback for the mbus object's scan method. It is called from anotehr thread
    :param existing: the list of already known to exist devices. If None, cloud will be
     queried for existance.
    :param full: When true, all assets will also be (re)created (data packet needs to be retrieved
    :param found: a dictionary of devices  that was found  key = device id, value = (manufacturoer, medium, assets, all is included)
    """
    for key, dev in found.iteritems():
        if existing:
            existingDev = next((x for x in existing if x['id'].encode('ascii', 'ignore') == str(key)), None)
        else:
            existingDev = None
        if not existingDev:
            addDevice(key, dev)
        else:
            if existing:
                existing.remove(existingDev)  # so we know at the end which ones have to be removed.
            if full:
                addDevice(key, dev)  # this will also refresh it
            else:
                dev.definition = existingDev['assets']

def addDevice(id, device):
    """adds the device and all it's assets to the cloud"""
    try:
        raw = device.raw
        if "Error" in raw:
            logger.error("m-bus communication error: {}".format(raw["Error"]))
            _gateway.send(raw["Error"], None, meterbus.lastError)
        else:
            templateId = "{}-{}-{}".format(raw['Manufacturer'], raw['Id'], raw['Version'])
            device.definition = _gateway.addDeviceFromTemplate(id, templateId)
            if not device.definition:
                addDeviceFromRaw(id, device)
            else:
                knownAssets = device.definition['assets']
                found = next((x for x in knownAssets if x['name'].encode('ascii', 'ignore') == "status"), None)
                if found:
                    _gateway.send(raw['Status'], id, 'status')
                found = next((x for x in knownAssets if x['name'].encode('ascii', 'ignore') == "manufacturer"), None)
                if found:
                    _gateway.send(raw['Manufacturer'], id, 'manufacturer')
                found = next((x for x in knownAssets if x['name'].encode('ascii', 'ignore') == "version"), None)
                if found:
                    _gateway.send(raw['Version'], id, 'version')
                found = next((x for x in knownAssets if x['name'].encode('ascii', 'ignore') == "sample_frequency"), None)
                if found and 'state' in found:                       # so we sample at the correct frequency for this device
                    val = found['state']
                    if val:
                        device.sampleFreq = int(val)
                    else:
                        _gateway.send(device.sampleFreq, id, 'sample_frequency')        # there was no sample frequency specified, so let the cloud know that wer are using the default value.
    except:
        logger.exception("failed to add device id: {}, value: ".format(id, device))

def addDeviceFromRaw(id, device):
    """add the device to the cloud using the raw data as reported by the device through the mbus protocol
    (vs from template)"""
    raw = device.raw
    assets = []
    device.definitions = {"assets": assets}
    name = "{} {} meter".format(raw['Manufacturer'], raw['Id'])
    desc = "{} {} meter".format(name, raw['Medium'])
    _gateway.addDevice(id, name, desc)

    _gateway.addAsset('status', id, 'status', 'status', False, 'number')
    _gateway.send(raw['Status'], id, 'status')

    _gateway.addAsset('manufacturer', id, 'manufacturer', 'manufacturer', False, 'string')
    _gateway.send(raw['Manufacturer'], id, 'manufacturer')

    _gateway.addAsset('version', id, 'version', 'version', False, 'string')
    _gateway.send(raw['Version'], id, 'version')

    _gateway.addAsset('sample_frequency', id, 'sample frequency',
                      'determines the period by which the device will be queried for new values, expressed in seconds',
                      True, 'integer')
    _gateway.send(str(meterbus.DefaultSamplingFrequency), id, 'sample_frequency')

    for asset in raw['DataRecord']:
        if asset['Function'] != 'More records follow':
            val = asset['Value']
            if isinstance(val, bool):
                assets.append(_gateway.addAsset(asset['Id'], id, asset['Unit'], asset['Unit'], False, 'boolean'))
            elif isinstance(val, int):
                assets.append(_gateway.addAsset(asset['Id'], id, asset['Unit'], asset['Unit'], False, 'integer'))
            elif isinstance(val, float):
                assets.append(_gateway.addAsset(asset['Id'], id, asset['Unit'], asset['Unit'], False, 'number'))
            else:
                assets.append(_gateway.addAsset(asset['Id'], id, asset['Unit'], asset['Unit'], False, 'string'))

