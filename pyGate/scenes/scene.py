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