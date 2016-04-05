__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
logger = logging.getLogger('mbus')

import threading
from mbus.MBus import MBus
from mbus.MBusFrame import MBusFrame
import mbus.MBusLowLevel as mbusLow
import config

_accumulativeAsset = {}  # the assets that have accumulative values, for which the difference of the current and previous value has to be calculated

class Mbus:
    """"manages a single mbus-connector device"""

    def __init__(self, gateway):
        self._gateway = gateway
        self._mbus = None
        self._setupMbus()
        self._mbus.connect()
        self._devicesLock = threading.Lock()
        self._devices = set([])  # the devices that need to be queried



    def _setupMbus(self):
        """create the mbus connection"""
        if not config.configs.has_option('mbus', 'device'):
            if not config.configs.has_option('mbus', 'host'):
                logger.error('mbus configuration missing: device or host')
                return
            else:
                if config.configs.has_option('mbus', 'port'):
                    self._mbus = MBus(host=config.configs.get('mbus', 'host'), port=config.configs.has_option('mbus', 'port'))
                else:
                    self._mbus = MBus(host=config.configs.get('mbus', 'host'))
        else:
            self._mbus = MBus(device=config.configs.get('mbus', 'device'))


    def stop(self):
        self._mbus.disconnect()

    def sample(self):
        """walk over all the devices, """
        for devId in self._devices:
            self._mbus.send_request_frame(devId)
            reply = self._mbus.recv_frame()
            reply_data = self._mbus.frame_data_parse(reply)
            for asset in reply_data.records:
                if asset.storage_number in self._devices:
                    prev = self._devices[asset.storage_number]
                    if prev:
                        self._gateway.send(asset.value - prev, asset.storage_number, devId)
                    self._devices[asset.storage_number] = asset.value
                else:
                    self._gateway.send(asset.value, asset.storage_number, devId)



class MBusScanner(threading.Thread):
    """scans the network for mbus devices. used to run in another thread."""

    def __init__(self, mbus, existing, full, callback):
        """
        :param existing: the list of already known to exist devices. If None, cloud will be
         queried for existance.
        :param full: When true, all assets will also be (re)created (data packet needs to be retrieved
        :param found: a dictionary of devices  that was found  key = device id, value = (manufacturoer, medium, assets, all is included)
        """
        threading.Thread.__init__(self)
        self.existing = existing
        self.full = full
        self.callback = callback
        self.mbus = mbus


    def ping(self, address):
        for i in range(0, self.mbus.max_search_retry + 1):
            if self.mbus.send_request_frame():
                reply = MBusFrame()
                if self.mbus._libmbus.recv_frame(self.mbus.handle, reply) == 0:
                    return reply
            else:
                logger.error("failed to send request frame to: {}".format(address))

    def run(self):
        try:
            result = {}
            try:
                for address in range(0, mbusLow.MBUS_MAX_PRIMARY_SLAVES + 1):
                    try:
                        dev = self.ping(address)
                        if dev:
                            result[address] = dev
                            self.mbus._devicesLock.acquire()
                            try:
                                self.mbus._devices.add(address)
                            finally:
                                self.mbus._devicesLock.release()

                    except:
                        logger.exception('error while pinging mbus device id: {}, moving on to next device'.format(address))
            except:
                logger.exception('failed to scan for mbus devices')
            if self.callback:
                self.callback(self.existing, self.full, result)
        except:
            logger.exception('failed to scan for mbus devices')
