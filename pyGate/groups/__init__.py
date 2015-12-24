__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import json
from time import sleep                             #pause the app

import device
import cloud
import modules
import config

GROUPDEF_ID = 'groupDefs'                                                            #the id of the button, don't uses spaces. required for the att platform

_device = None
_groups = {}
_actuators = {}


def onAssetValueChanged(module, device, asset, value):
    """callback for the processor part: check if the value of an actuator has changed, if so, update the group's value"""
    name = _getActName(module, device, asset)
    if name in _actuators:
        grp = _actuators[name]
        if grp.value != value:
            if grp.value:                       # previous values were all the same, so they went different.
                grp.value = None
                _device.send("", grp.id)
            else:
                grp.value = grp.getValueFromActuators()     # check if they are all the same again.
                if grp.value:
                    _device.send(grp.value, grp.id)


#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id == GROUPDEF_ID:
        loadGroups(json.loads(value))
    elif id in _groups:
        _setValue(id, _groups[id], value)
    else:
        print("unknown actuator: " + id)

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _device
    _device = device.Device(moduleName, 'groups')

def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.'''
    if not existing:
        _device.createDevice('groups managaer', 'manage your device groups with single controls')
        loadGroups(config.loadConfig('groups.json', True))

def _setValue(id, group, value):
    """send the new value to each actuator. Make certain that the electrical system doesn't get over burndend, so pause a little betweeen each actuator."""
    for actuator in group.acuators:
        modules.actuate(actuator['module'], actuator['device'], actuator['asset'], value)
        sleep(group.sleep)
    group.value = value
    _device.send(value, id)


def _getActName(module, device, asset):
    return module + "_" + str(device) + "_" + str(asset)

def loadGroups(value):
    """load the groupings from a json structure, so that it's easy to execute the groups and store/update the value of the group
        This will also update the assets for each group in the cloud.
    """
    for group in value:
        grp = Group(group['id'], group['actuators'], group['sleep'])        # also calculates the value for the group and builds the reverese list
        _groups[group['id']] = grp
        for actuator in group['actuators']:                     # build the reverse map, for fast changing of group values.
            actName = _getActName(actuator['module'], actuator['device'], actuator['asset'])
            if actName in _actuators:
                _actuators[actName].add(grp)
            else:
                _actuators[actName] = [grp]
        _device.addAsset(group['id'], group['name'], group['description'], True, group['profile'])


class Group:
    def __init__(self, id, actuators, sleep):
        """
        :type actuators: list of json objects containing fields: module, device, asset
        :param actuators: the list of actuators that belong in this group.
        """
        self.id = id
        self.acuators = actuators
        self.sleep = sleep
        self.value = self.getValueFromActuators()

    def getValueFromActuators(self):
        """walk over each actuator, request it's value (from the cloud?) """

        prevVal = None
        for actuator in self.acuators:
            value = cloud.getAssetState(actuator['module'], actuator['device'], actuator['asset'])
            if prevVal:
                if value != prevVal:
                    return None
            else:
                prevVal = value
        return prevVal