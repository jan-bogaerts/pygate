__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
import os.path
import threading

from core import config


class DeviceCounter:
    """provides an application secure counter for gateways"""

    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()

    def getValue(self):
        """increments the counter and stores the value in the config dir
        before returning it"""
        self.lock.acquire()
        try:
            if not hasattr(self, '_value'):
                self._tryLoadValue()
            self._value += 1
            self._storeValue()
            return self._value
        finally:
            self.lock.release()

    def _tryLoadValue(self):
        """checks if there is a config stored for this counter, if so, load the value"""
        fileName = config.configPath + self.name + '.counter'
        if os.path.isfile(fileName):
            with open(fileName) as file:
                valueStr = file.readline()
                logging.info("loaded " + valueStr + " from " + fileName)
                self._value = int(valueStr)
        else:
            self._value = 0

    def _storeValue(self):
        """store the value to disk so that it something goes wrong, we always have a unique value by reading from disk and adding 1"""
        fileName = config.configPath + self.name + '.counter'
        with open(fileName, 'w') as file:
            valueStr = str(self._value)
            logging.info("saving " + valueStr + " to " + fileName)
            file.write(valueStr)
