# main entry for the pyGate plugin that provides support for zwave devices




def connectToGateway(cloud):
    '''optional
        called when the system connects to the cloud.
    '''

def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list. 
       existing: the list of devices that are already known in the cloud for this module.
    '''

def run():
    ''' required
        main function of the plugin module'''


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''