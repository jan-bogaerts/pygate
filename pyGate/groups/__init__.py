__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import json
from time import sleep                             #pause the app

from core import config, cloud, device, modules

GROUPDEF_ID = 'groupDefs'                                                            #the id of the button, don't uses spaces. required for the att platform
GROUPDEF_FILE = 'groups.json'

_device = None
_groups = {}
_actuators = {}


def onAssetValueChanged(module, device, asset, value):
    """callback for the processor part: check if the value of an actuator has changed, if so, update the group's value"""
    name = cloud.getUniqueName(module, device, asset)
    if name in _actuators:
        grps = _actuators[name]
        for grp in grps:
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
        jsonVal = json.loads(value)
        loadGroups(jsonVal, True)           # always do a full load cause the list of groups has changed, so the assets need to be updated in the cloud.
        saveGroups(value)
        _device.send(jsonVal, id)
    elif id in _groups:
        _setValue(id, _groups[id], value)
    else:
        print("unknown actuator: " + id)

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _device
    _device = device.Device(moduleName, 'groups')


def syncDevices(existing, full):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.'''
    if not existing:
        _device.createDevice('group manager', 'manage your device groups with single controls')
        _device.addAsset(GROUPDEF_ID , 'group definitions', 'define all the groups', True, 'object')
    if full:
        global _groups
        _groups = _buildGroupsDict(existing['assets'])
    loadGroups(config.loadConfig(GROUPDEF_FILE, True), full)                                          # alwaye need to load these, otherwise there is no mapping loaded in memory

def _buildGroupsDict(assets):
    for asset in assets:
        _groups[asset['name']] = None       # we don't need an actual object in the dict, just a reference that the group exists

def _setValue(id, group, value):
    """send the new value to each actuator. Make certain that the electrical system doesn't get over burndend, so pause a little betweeen each actuator."""
    for actuator in group.acuators:
        modules.Actuate(actuator['module'], actuator['device'], actuator['asset'], value)
        sleep(group.sleep)
    group.value = value
    _device.send(value, id)

def loadGroups(value, syncCloud):
    """load the groupings from a json structure, so that it's easy to execute the groups and store/update the value of the group
        This will also update the assets for each group in the cloud.
        :param value: a json object that contains the group definitions
        :param syncCloud: when true, the cloud is synced: assets are created and deleted.
        When false, only the internal state of the engine is updated (quicker).
    """
    global _groups
    newGroups = {}
    _actuators.clear()
    for group in value:
        grp = Group(group['id'], group['actuators'], group['sleep'])        # also calculates the value for the group and builds the reverese list
        newGroups[group['id']] = grp
        for actuator in group['actuators']:                     # build the reverse map, for fast changing of group values.
            actName = cloud.getUniqueName(actuator['module'], actuator['device'], actuator['asset'])
            if actName in _actuators:
                _actuators[actName].add(grp)
            else:
                _actuators[actName] = [grp]
        if syncCloud:
            if group['id'] not in _groups:
                _device.addAsset(group['id'], group['name'], group['description'], True, str(group['profile']))
            else:
                _groups.pop(group['id'])  # the group still exists, so remove it from the old list (otherwise it gets deleted from the clodu)

    if syncCloud:
        for key, value in _groups:
            _device.deleteAsset(key)
    _groups = newGroups

def saveGroups(value):
    """save the groups back to the config"""
    with open(config.configPath + GROUPDEF_FILE, 'w') as f:
        f.write(value)

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