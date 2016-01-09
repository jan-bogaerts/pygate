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
import cloud

modules = {}                                    # the list of dynamically loaded modules.


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

    
def syncGatewayAssets(full = False):
    '''allows the modules to sync with the cloud, the assets that should come at the level of the gateway
    :param full: recreate all assets,
    '''
    for key, value in modules.iteritems():
        if hasattr(value, 'syncGatewayAssets'):
            logging.info("syncing gateway assets for " +  key)
            try:
                value.syncGatewayAssets()
            except:
                logging.exception('failed to sync gateway assets for module ' + key + '.')


def syncDevices(full = False):
    """allow the modules to sync the devices with the cloud
    :param full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    """
    deviceList = syncDeviceList()
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

def runModule(module):
    """executes the run method of a single module, in a safe manner"""
    try:
        thread.start_new_thread(module.run, ())
    except:
        logging.exception('error while running module')

def run():
    """run the main function of each module in it's own thread"""
    logging.info("starting up all plugins")
    if modules:
        #map(lambda x:thread.start_new_thread(x.run, ()), [mod for key, mod in modules.iteritems() if hasattr(mod, 'run')])
        map(lambda x: x.run(), [RunModule(mod, key) for key, mod in modules.iteritems() if hasattr(mod, 'run')])


def Actuate(module, device, actuator, value):
    '''Can be used as a generir method to send a command to an actuator managed by the specified module.
    The function will figure out the most appropriate callback, depending on the presence of a device or not
    - module can be a string (name of the module), or the module object itself.'''
    # zwaveGateway.onActuate(zwaveGateway._discoveryStateId, 'include')
    if isinstance(module, basestring):
        if module in modules:
            mod = modules[module]
        else:
            logging.error('actuator request for unknown module: %s, dev: %s, actuator: %s, value: %s' % str(module), str(device), str(actuator), str(value))
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
            logging.exception('error processing actuator request: module: %s, dev: none, actuator: %s, value: %s' % str(module), str(actuator), str(value))


def stripDeviceIds(list):
    '''goes over the list items and converts the 'deviceIds' to local versions (strip module '''
    for x in list:
        x['id'] = cloud.stripDeviceId(x['name'])

class syncDeviceList(object):
    """gets the full list of devices 1 time from the cloud and then allows filtered queries on the list"""

    def __init__(self):
        self._list = cloud.getDevices()

    def filter(self, key):
        """return a sublist, first make certain that we have the list."""
        result = [x for x in self._list if  cloud.getModuleName(x['name']) == key]
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
        except Exception:
            logging.error('error in run for module: ' + self.name)

