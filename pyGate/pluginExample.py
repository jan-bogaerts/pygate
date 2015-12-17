

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''

def syncDevices(existing, Full = False):
    '''optional
       allows a module to synchronize it's device list. 
       existing: the list of devices that are already known in the cloud for this module.
       :param Full: when false, if device already exists, don't update, including assets. When true,
       update all, including assets
    '''

def syncGatewayAssets(Full = False):
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    :param Full: when false, if device already exists, don't update, including assets. When true,
    update all, including assets
    '''

def run():
    ''' required
        main function of the plugin module'''

def onActuate(actuator, value):
    '''optional 
    callback routine for plugins that behave as devices or for plugins that behave as gateways, when the actuator is on the gateway itself.'''


def onDeviceActuate(device, actuator, value):
    '''optional callback routine for plugins that behave as gateways'''

def getValueConverter(device, asset):
    '''optional.
    called when this module has sent a value to the cloud which triggered other assets (associations). Allows the module to provide a value
    converter that changes the actuator data (ex: toggle buttons).
    '''
