# -*- coding: utf-8 -*-

#important: before running this demo, make certain that you import the library
#'paho.mqtt.client' into python (https://pypi.python.org/pypi/paho-mqtt)

import device
from time import sleep                             #pause the app

In1Name = "Put the name of your sensor"                                #name of the button
In1Id = 1                                                            #the id of the button, don't uses spaces. required for the att platform
Out1Name = "Put the name of your actuator"
Out1Id = 2

_device = None


#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id.endswith(str(Out1Id)) == True:
        value = value.lower()                        #make certain that the value is in lower case, for 'True' vs 'true'
        if value == "true":
            print("true on " + Out1Name)
            IOT.send("true", Out1Id)                #provide feedback to the cloud that the operation was succesful
        elif value == "false":
            print("false on " + Out1Name)
            IOT.send("false", Out1Id)                #provide feedback to the cloud that the operation was succesful
        else:
            print("unknown value: " + value)
    else:
        print("unknown actuator: " + id)

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _device
    _device = device.Device(moduleName, 'windowsTest1')

def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list. 
       existing: the list of devices that are already known in the cloud for this module.'''
    if not existing:
        _device.createDevice('windows test device', 'just something to test the framework')
        _device.addAsset(In1Id, In1Name, "put your description here", False, "boolean")
        _device.addAsset(Out1Id, Out1Name, "put your description here", True, "boolean")


def run():
    nextVal = True;
    #main loop: run as long as the device is turned on
    while True:
        if nextVal == True:
            print(In1Name + " activated")
            _device.send("true", In1Id)
            nextVal = False
        else:
            print(In1Name + " deactivated")
            _device.send("false", In1Id)
            nextVal = True
        sleep(5)