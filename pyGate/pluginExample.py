

def connectToGateway(cloud):
    '''optional
        called when the system connects to the cloud.
    '''

def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list. 
       existing: the list of devices that are already known in the cloud for this module.
    '''

def syncGatewayAssets():
    '''
    optional. Allows a module to synchronize with the cloud, all the assets that should come at the level
    of the gateway.
    '''

def run():
    ''' required
        main function of the plugin module'''