__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


import logging
logger = logging.getLogger('virtual devices')
from apscheduler.schedulers.background import BackgroundScheduler

from core.gateway import Gateway
from core import config
from virtualDevice import VirtualDevice

gateway = None
scheduler = BackgroundScheduler()
devices = {}

virtualDevicesConfigId = 'config'
VDEF_FILE = 'virtualdevices.json'

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global gateway
    gateway = Gateway(moduleName)


def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    :param full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    '''
    #don't need to wait for the zwave server to be fully ready, don't need to query it for this call.
    gateway.addGatewayAsset(virtualDevicesConfigId, 'virtual devices config', 'configure your virtual devices', True,  '{"type" :"object"}')

def syncDevices(existing, full=False):
    '''optional
       allows a module to synchronize it's device list.
       :param existing: the list of devices that are already known in the cloud for this module.
       :param full: when false, if device already exists, don't update, including assets. When true,
        update all, including assets
    '''
    definitions = config.loadConfig(VDEF_FILE, True)
    for definition in definitions:
        name = str(definition['name'])
        device = VirtualDevice(definition['service'], definition['params'], name)
        devices[name] = device
        found = next((x for x in existing if x['id'].encode('ascii', 'ignore') == name), None)
        if found:
            if full:
                device.updateDevice(gateway)
            existing.remove(found)
        else:
            device.addDevice(gateway)
    for dev in existing:  # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
        gateway.deleteDevice(dev['id'])

def run():
    ''' optional
        main function of the plugin module'''
    for key, device in devices:
        scheduleAt = device.refreshRate.split(':')
        if len(scheduleAt) != 3:
            logger.error("invalid time interval: {} in device: {}".format(scheduleAt, device.id))
        else:
            scheduler.add_job(device.run, 'date', days=scheduleAt[0], hours=scheduleAt[1], minutes=scheduleAt[2], id=key, args=[gateway])
    scheduler.start()

def stop():
    """"called when the application terminates.  Allows us to clean up the hardware correctly, so we cn be restarted without (cold) reboot"""
    scheduler.shutdown()


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''
    logger.error("actuators on virtual devices not yet supported")


def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    if actuator == virtualDevicesConfigId:
        loadDevices(value)