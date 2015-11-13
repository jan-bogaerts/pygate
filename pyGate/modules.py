##########################################################
# manage all the dynamically loaded modules of the gateway.

import thread

modules = {}                                    # the list of dynamically loaded modules.

def load(moduleNames, cloud):
    """Loads all the gateway modules"""
    global modules
    modules = dict(zip(moduleNames, map(__import__, moduleNames)))       # load the modules and put them in a dictionary, key = the name of the module.
    for mod in modules.iteritems:
        if mod.connectToGateway:
            mod.connectToGateway(cloud)

def syncDevices(cloud):
    """allow the modules to sync the devices with the cloud"""
    deviceList = syncDeviceList(cloud)
    for key, value in modules:
        if value.syncDevices:
            value.syncDevices(deviceList.filter(key))


def run():
    """run the main function of each module in it's own thread"""
    map(lambda x:thread.start_new_thread(x.run, ()), modules.iteritems)



class syncDeviceList(object):
    """gets the full list of devices 1 time from the cloud and then allows filtered queries on the list"""

    def __init__(self, cloud):
        self._cloud = cloud
    
    def filter(self, key):
        """return a sublist, first make certain that we have the list."""
        if not self._list:
            self._list = self_cloud.getDevices()
        return [x for x in self._list if  self._cloud.getModuleName(x.Name) == key]
