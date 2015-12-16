##########################################################
# manage all the dynamically loaded modules of the gateway.

import logging
import thread
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

    
def syncGatewayAssets():
    '''allows the modules to sync with the cloud, the assets that should come at the level of the gateway'''
    for key, value in modules.iteritems():
        if hasattr(value, 'syncGatewayAssets'):
            logging.info("syncing gateway assets for " +  key)
            try:
                value.syncGatewayAssets()
            except:
                logging.exception('failed to sync gateway assets for module ' + key + '.')

def syncDevices():
    """allow the modules to sync the devices with the cloud"""
    deviceList = syncDeviceList()
    for key, value in modules.iteritems():
        if hasattr(value, 'syncDevices'):
            logging.info("syncing devices for " +  key)
            try:
                value.syncDevices(deviceList.filter(key))
            except:
                logging.exception('failed to sync devices for module ' + key + '.')


def run():
    """run the main function of each module in it's own thread"""
    logging.info("starting up all plugins")
    if modules:
        map(lambda x:thread.start_new_thread(x.run, ()), [mod for key, mod in modules.iteritems() if mod.run])


import zwaveGateway

def Actuate(module, device, actuator, value):
    '''Can be used as a generir method to send a command to an actuator managed by the specified module.
    The function will figure out the most appropriate callback, depending on the presence of a device or not
    - module can be a string (name of the module), or the module object itself.'''
    # zwaveGateway.onActuate(zwaveGateway._discoveryStateId, 'include')
    if isinstance(module, basestring):
        if module in modules:
            mod = modules[module]
        else:
            logging.error('actuator request for unknown module: ' + str(module))
            return
    else:
        mod = module
    if device:
        if hasattr(mod, 'onDeviceActuate'):                                     # it's a gateway
            mod.onDeviceActuate(device, actuator, value)
        elif hasattr(mod, 'onActuate'):                                         # it'sa regular device
            mod.onActuate(actuator, value)
    elif hasattr(mod, 'onActuate'):
            mod.onActuate(actuator, value)


class syncDeviceList(object):
    """gets the full list of devices 1 time from the cloud and then allows filtered queries on the list"""

    def __init__(self):
        self._list = []
    
    def filter(self, key):
        """return a sublist, first make certain that we have the list."""
        if not self._list:
            self._list = cloud.getDevices()
            self.stripDeviceIds()
        return [x for x in self._list if  cloud.getModuleName(x['name']) == key]

    def stripDeviceIds(self):
        '''goes over the list items and converts the 'deviceIds' to local versions (strip module '''
        for x in self._list:
            x['id'] = cloud.stripDeviceId(x['name'])

