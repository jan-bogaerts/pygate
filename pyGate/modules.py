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
import thread
import threading
import sys

import cloud
import config
import processors

modules = {}                                    # the list of dynamically loaded modules.
_modulesName = 'modules'
_activepluginsName = 'activeplugins'

def load(moduleNames):
    """Loads all the gateway modules"""
    global modules
    logging.info("loading modules")
    modules = dict(zip(moduleNames, map(__import__, moduleNames)))       # load the modules and put them in a dictionary, key = the name of the module.
    for key, mod in modules.iteritems():
        if mod.connectToGateway:
            logging.info("connecting " +  key + " to gateway")
            try:
                mod.connectToGateway(key)
            except:
                logging.exception('failed to connect module ' + key + ' to gateway.')

def syncGateway(full = False):
    content = cloud.getGateway()
    syncGatewayAssets(content['assets'])
    syncDevices(content['devices'], full)

def syncGatewayAssets(currentAssets):
    '''allows the modules to sync with the cloud, the assets that should come at the level of the gateway
    :param full: recreate all assets,
    '''
    assetsDict = {x['name']: x for x in currentAssets}          # convert existing assets to dict, so that cloud module can easily remove gateway assets that have been recreated.
    try:
        cloud.existingGatewayAssets = assetsDict
        for key, value in modules.iteritems():
            if hasattr(value, 'syncGatewayAssets'):
                logging.info("syncing gateway assets for " +  key)
                try:
                    value.syncGatewayAssets()
                except:
                    logging.exception('failed to sync gateway assets for module {}.'.format(key))
        cloud.addGatewayAsset(_modulesName, _activepluginsName, 'active plugins', 'The list of currently active plugins', True, '{"type": "array", "items":{"type":"string"}}')
        processors.syncGatewayAssets()
        for key, value in assetsDict:
            cloud.deleteGatewayAsset(key)
    except:
        logging.exception('failed to sync gateway')
    finally:
        cloud.existingGatewayAssets = None


def syncDevices(devices, full = False):
    """allow the modules to sync the devices with the cloud
    :param full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    """
    deviceList = syncDeviceList(devices)
    for key, value in modules.iteritems():
        if hasattr(value, 'syncDevices'):
            logging.info("syncing devices for " +  key)
            try:
                subList = deviceList.filter(key)
                deviceList.remove(subList)              # remove the sublist, so we can see at the end of the ride which 'modules' where present last time, but not anymore, so we can also remove those devices. Do before asking module to sync, cause it could modify the list.
                value.syncDevices(subList, full)
            except:
                logging.exception('failed to sync devices for module ' + key + '.')
    for x in deviceList._list:                          # remove all devices related to modules which are no longer available.
        try:
            cloud.deleteDeviceFullName(x['id'])
        except:
            logging.exception('failed to clean up device with unrelated module: ' + str(x))

def run():
    """run the main function of each module in it's own thread"""
    cloud.send(_modulesName, None, _activepluginsName, config.modules)      # we are only now certain of the network connection, so let cloud know current state of settings.
    logging.info("starting up all plugins")
    if modules:
        #map(lambda x:thread.start_new_thread(x.run, ()), [mod for key, mod in modules.iteritems() if hasattr(mod, 'run')])
        for x in [RunModule(mod, key) for key, mod in modules.iteritems() if hasattr(mod, 'run')]:
            x.start()

def stop():
    """lets every module that wants to, perform the necessary cleanups."""
    for key, value in modules.iteritems():
        if hasattr(value, 'stop'):
            logging.info("stopping module " +  key)
            try:
                value.stop()
            except:
                logging.exception('failed to stop module ' + key + '.')

def Actuate(module, device, actuator, value):
    '''Can be used as a generir method to send a command to an actuator managed by the specified module.
    The function will figure out the most appropriate callback, depending on the presence of a device or not
    - module can be a string (name of the module), or the module object itself.'''
    # zwaveGateway.onActuate(zwaveGateway._discoveryStateId, 'include')
    if module == _modulesName:
        if actuator == _activepluginsName:
            switchPlugins(value)
        else:
            logging.error("invalid actuator request for modules-module: {}, value: {}".format(actuator, value))
    if isinstance(module, basestring):
        if module in modules:
            mod = modules[module]
        elif module in processors.processors:
            mod = processors.processors[module]
        else:
            logging.error('actuator request for unknown module: {}, dev: {}, actuator: {}, value: {}'.format(module, device, actuator, value))
            return
    else:
        mod = module
    try:
        if device:
            if hasattr(mod, 'onDeviceActuate'):                                     # it's a gateway
                mod.onDeviceActuate(device, actuator, value)
            elif hasattr(mod, 'onActuate'):                                         # it'sa regular device
                mod.onActuate(actuator, value)
        elif hasattr(mod, 'onActuate'):
                mod.onActuate(actuator, value)
    except:
        if device:
            logging.exception('error processing actuator request: module: {}, dev: {}, actuator: {}, value: {}'.format(str(module), str(device), str(actuator), str(value)))
        else:
            logging.exception('error processing actuator request: module: {}, dev: none, actuator: {}, value: {}'.format(module, actuator, value))


def switchPlugins(newModules):
    logging.warning("list of plugins has been modified to: {}, stopping system, the shell should restart the application".format(newModules))
    config.configs.set('general', 'modules', ';'.join(newModules))
    config.save()
    thread.interrupt_main()

def stripDeviceIds(list):
    '''goes over the list items and converts the 'deviceIds' to local versions (strip module '''
    for x in list:
        x['id'] = cloud.stripDeviceId(x['name'])

class syncDeviceList(object):
    """gets the full list of devices 1 time from the cloud and then allows filtered queries on the list"""

    def __init__(self, devices):
        self._list = devices

    def filter(self, key):
        """return a sublist, first make certain that we have the list."""
        result = [x for x in self._list if cloud.getModuleName(x['name']) == key]
        stripDeviceIds(result)       # only do for the requested list so that we have 'full' names for modules that have been removed
        return result


    def remove(self, list):
        """remove a sublist from the current list"""
        self._list = [x for x in self._list if x not in list]


class RunModule(threading.Thread):
    def __init__(self, module, name):
        threading.Thread.__init__(self)
        self.module = module
        self.name = name

    def run(self):
        try:
            self.module.run()
        except:
            logging.exception('error in run for module: ' + self.name)

