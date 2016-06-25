__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import json
from time import sleep                             #pause the app
from scene import Scene

import device
import cloud
import modules
import config

SCENEDEF_ID = 'sceneDefs'                                                            #the id of the button, don't uses spaces. required for the att platform
SCENEDEF_FILE = 'scenes.json'

_device = None
_scenes = {}
_actuators = {}


#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    if id == SCENEDEF_ID:
        jsonVal = json.loads(value)
        loadScenes(jsonVal, True)           # always do a full load cause the list of groups has changed, so the assets need to be updated in the cloud.
        saveScenes(value)
        _device.send(jsonVal, id)
    elif id in _scenes:
        # value not really important: if we get a command for a scene, we activate it.
        _activateScene(id, _scenes[id])
    else:
        print("unknown actuator: " + id)

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _device
    _device = device.Device(moduleName, 'scenes')


def syncDevices(existing, full):
    '''optional
       allows a module to synchronize it's device list.
       existing: the list of devices that are already known in the cloud for this module.'''
    if not existing:
        _device.createDevice('scene manager', 'manage your scenes')
        _device.addAsset(SCENEDEF_ID, 'scene definitions', 'define all the scenes', True, 'object')
    if full:
        global _scenes
        _scenes = _buildScenesDict(existing['assets'])
    loadScenes(config.loadConfig(SCENEDEF_FILE, True), full)                                          # alwaye need to load these, otherwise there is no mapping loaded in memory

def _buildScenesDict(assets):
    for asset in assets:
        _scenes[asset['name']] = None  # we don't need an actual object in the dict, just a reference that the group exists

def loadScenes(value, syncCloud):
    """load the scenes from a json structure, so that it's easy to execute the scenes and store/update the value of the scene
        This will also update the assets for each scene in the cloud.
        :param value: a json object that contains the scene definitions
        :param syncCloud: when true, the cloud is synced: assets are created and deleted.
        When false, only the internal state of the engine is updated (quicker).
    """
    global _scenes
    newScenes = {}
    _actuators.clear()
    for scene in value:
        toAdd = Scene(scene['id'], scene['actuators'], scene['sleep'])        # also calculates the value for the group and builds the reverese list
        newScenes[scene['id']] = toAdd
        for actuator in scene['actuators']:                     # build the reverse map, for fast changing of group values.
            actName = cloud.getUniqueName(actuator['module'], actuator['device'], actuator['asset'])
            if actName in _actuators:
                _actuators[actName].add(toAdd)
            else:
                _actuators[actName] = [toAdd]
        if syncCloud:
            if scene['id'] not in _scenes:
                _device.addAsset(scene['id'], scene['name'], scene['description'], True, "boolean")
            else:
                _scenes.pop(scene['id'])  # the group still exists, so remove it from the old list (otherwise it gets deleted from the clodu)
    if syncCloud:
        for key, value in _scenes:
            _device.deleteAsset(key)
    _scenes = newScenes


#def onAssetValueChanged(module, device, asset, value):
#    """callback for the processor part: check if the value of an actuator has changed, if so, update the group's value"""
#    name = cloud.getUniqueName(module, device, asset)
#    if name in _actuators:
#        scenes = _actuators[name]
#        for scene in scenes:
#            newVal = scene.getValueFromActuators()
#            if newVal != scene.value:
#                scene.value = newVal
#                _device.send(scene.value, scene.id)

def _activateScene(id, scene):
    """send the new value to each actuator. Make certain that the electrical system doesn't get over burndend, so pause a little betweeen each actuator."""
    for actuator in scene.acuators:
        modules.Actuate(actuator['module'], actuator['device'], actuator['asset'], actuator['value'])
        sleep(scene.sleep)
    _device.send('true', id)

def saveScenes(value):
    """save the scenes back to the config"""
    with open(config.configPath + SCENEDEF_FILE, 'w') as f:
        f.write(value)

