__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import cloud

class Scene:
    def __init__(self, id, actuators, sleep):
        self.id = id
        self.acuators = actuators
        self.sleep = sleep
        self.value = self.getValueFromActuators()

    def getValueFromActuators(self):
        """walk over each actuator, request it's value (from the cloud?), check if it's the same as the value in the scene.
         If all actuator values match that of the scene, then the scene is active, and True is returned, otherwise 'false'"""

        for actuator in self.acuators:
            value = cloud.getAssetState(actuator['module'], actuator['device'], actuator['asset'])
            # note: if this is not correct, then the implementation in groups is also incorrect.
            if value != actuator['value']:
                return False
        return True