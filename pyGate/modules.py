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
            mod.connectToGateway(key)

def syncGatewayAssets():
    '''allows the modules to sync with the cloud, the assets that should come at the level of the gateway'''
    for key, value in modules.iteritems():
        if value.syncGatewayAssets:
            logging.info("syncing gateway assets for " +  key)
            value.syncGatewayAssets()

def syncDevices():
    """allow the modules to sync the devices with the cloud"""
    deviceList = syncDeviceList()
    for key, value in modules.iteritems():
        if value.syncDevices:
            logging.info("syncing devices for " +  key)
            value.syncDevices(deviceList.filter(key))


def run():
    """run the main function of each module in it's own thread"""
    logging.info("starting up all plugins")
    if modules:
        map(lambda x:thread.start_new_thread(x.run, ()), [mod for key, mod in modules.iteritems() if mod.run])



class syncDeviceList(object):
    """gets the full list of devices 1 time from the cloud and then allows filtered queries on the list"""

    def __init__(self):
        self._list = []
    
    def filter(self, key):
        """return a sublist, first make certain that we have the list."""
        if not self._list:
            self._list = cloud.getDevices()
            self.stripDeviceIds()
        return [x for x in self._list if  cloud.getModuleName(x.Name) == key]

    def stripDeviceIds(self):
        '''goes over the list items and converts the 'deviceIds' to local versions (strip module '''
        for x in self._list:
            x['id'] = cloud.getDeviceId(x['id'])

