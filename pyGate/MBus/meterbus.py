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
from mbus.MBusFrameData import MBusFrameData
import mbus.MBusLowLevel as mbusLow
import datetime

from core import config
import ctypes
import binConverter

MBUS_CONTROL_MASK_REQ_UD2 = 0x5B
MBUS_CONTROL_MASK_DIR_M2S = 0x40
MBUS_CONTROL_MASK_FCV = 0x10
MBUS_CONTROL_MASK_FCB = 0x20


isScanningId = "isscanning"
lastError = "lasterror"
baudrate = 'baudrate'
scanPos = 'scanPos'

DefaultSamplingFrequency = 300
'the default sampling frequency, in case that there is no frequency specified for a device.'

def _tryGetCalculation(asset):
    """checks if hte asset has a 'calculation' field in the profile, if so, the string is returned.
    otherwise None"""
    if asset:
        if 'profile' in asset:
            profile = asset['profile']
            if 'calculation' in profile:
                return profile['calculation']
    return None

def _isAccumulative(asset):
    """checks if an asset is accumulative."""
    if asset:
        if 'profile' in asset:
            profile = asset['profile']
            if 'accumulative' in profile:
                return profile['accumulative']
    return False

def _calculateAccumulative(record, device, id):
    """calculate the accumulative value
    :param record: the record as reported by the mbus protocol
    :param device: the device definition, which contains the previous value
    :param id: the id of the asset (index nr)
    """
    cur = record["Value"]
    val = None
    if id in device.prevValues:
        prev = device.prevValues[id]
        logger.info("cur val: {}, prev val: {}, id: {}".format(cur, prev, id))
        if cur >= prev:
            val = cur - prev
        else:
            logger.info("encoding: " + record["Encoding"].name)
            max = record["Encoding"].getMax()
            if max:
                val = cur + (max - prev)
            else:
                logger.error("trying to calculate a delta for a value that does not have a max, can't support round-robbin values")
    device.prevValues[id] = cur
    return val

class Mbus:
    """"manages a single mbus-connector device"""

    def __init__(self, gateway):
        self._gateway = gateway
        self._mbus = None
        self._setupMbus()
        if self._mbus:
            self._mbus.connect()
            baudRate = config.getConfig('mbus', 'baudrate', None)
            if baudRate:
                self._mbus._libmbus.serial_set_baudrate(self._mbus.handle, int(baudRate))
        self._devicesLock = threading.Lock()
        self._devices = {}  # the devices that need to be queried, key = devId, value = DeviceConfig object

    def _setupMbus(self):
        """create the mbus connection"""
        try:
            path = config.getConfig('mbus', 'libpath', None)
            if not config.configs.has_option('mbus', 'device'):
                if not config.configs.has_option('mbus', 'host'):
                    logger.error('mbus configuration missing: device or host')
                    return
                else:
                    if config.configs.has_option('mbus', 'port'):
                        self._mbus = MBus(host=config.configs.get('mbus', 'host'), port=config.configs.get('mbus', 'port'), libpath=path)
                    else:
                        self._mbus = MBus(host=config.configs.get('mbus', 'host'), libpath=path)
            else:
                self._mbus = MBus(device=config.configs.get('mbus', 'device'), libpath=path)
        except:
            logger.exception("failed to setup mbus")

    def stop(self):
        if self._mbus:
            self._mbus.disconnect()


    def sample(self):
        """
        walk over all the devices. This is done thread save, so a scan can be performed from another thread
        without worrying about sampling at the same time
        :rtype: the next time that we need to sample 1 or more devices"""
        nextRunAt = datetime.datetime.max
        self._devicesLock.acquire()
        try:
            for devId, dev in self._devices.iteritems():
                try:
                    runAt = datetime.datetime.now()
                    if dev.nextRunAt <= runAt:                      # only query the devices that need to be run in this time slot, each device has a different query frequency
                        reply = self.getRecords(devId, False)
                        if reply:
                            for asset in dev.definition['assets']:      # we start from the definition found on the cloud, this contains all the assets that we need to support
                                if asset['name'].isdigit():               # we only need to process assets that have an int as id, these represent the data records
                                    id = int(asset['name'])
                                    if _isAccumulative(asset):
                                        value = _calculateAccumulative(reply["DataRecord"][id], dev, id)
                                    else:
                                        value = reply["DataRecord"][id]["Value"]
                                    if value != None:
                                        calculation = _tryGetCalculation(asset)
                                        if calculation:
                                            value = eval(calculation)
                                        self._gateway.send(value, devId, str(id))
                        dev.lastRunAt = runAt
                    if nextRunAt > dev.nextRunAt:
                        nextRunAt = dev.nextRunAt
                except:
                    logger.exception("failed to process device: {}".format(devId))
        finally:
            self._devicesLock.release()
        if nextRunAt != datetime.datetime.max:
            return (nextRunAt - datetime.datetime.now()).total_seconds()
        else:
            return DefaultSamplingFrequency                     # if there was no device in this time range (ex: no devices yet), then do the next run at the default time interval, so that don't block after the first run when there are no devices yet, if we don't do this, we never query after the first device was added.

    def _getRequestFrame(self, address):
        """build an mbusframe object that can be used to request the data from a device."""
        frame = MBusFrame()
        frame.type = mbusLow.MBUS_FRAME_TYPE_SHORT
        frame.start1 = mbusLow.MBUS_FRAME_SHORT_START
        frame.stop = mbusLow.MBUS_FRAME_STOP

        frame.control = MBUS_CONTROL_MASK_REQ_UD2 | MBUS_CONTROL_MASK_DIR_M2S | MBUS_CONTROL_MASK_FCV | MBUS_CONTROL_MASK_FCB
        frame.address = address
        logger.info("address = {}".format(frame.address))
        return frame

    def _cleanFrames(self, data):
        """frame data contains pointers that need to be deleted (C data)"""
        try:
            for x in data:
                if x.data_var.record:
                    self._mbus._libmbus.data_record_free(x.data_var.record)  # need to clean this up, it's a C pointer
        except:
            logger.exception("failed to clean up data")

    def getRecords(self, address, full):
        """gets all the data records from the device at the speciied address
        :param address: the address to get the records for
        :param full: when true, parse all the data, otherwise only the values
        :return: a dict containing all the data that was found
        :type full: boolean

        """
        mbHandle = self._mbus.handle
        mb = self._mbus._libmbus
        retry = 0
        reply = MBusFrame()
        replies = []
        frame = self._getRequestFrame(address)
        more_frames = True

        try:
            while more_frames:
                if retry > 3:
                    return None
                if mb.send_frame(mbHandle, frame) == -1:
                    raise Exception("failed to send mbus frame")
                result = mb.recv_frame(mbHandle, reply)
                if result == mbusLow.MBUS_RECV_RESULT_OK:
                    logger.info("found response")
                    retry = 0
                    mb.purge_frames(mbHandle)
                elif result == mbusLow.MBUS_RECV_RESULT_TIMEOUT:
                    retry += 1
                    continue
                elif result == mbusLow.MBUS_RECV_RESULT_INVALID:
                    logger.warning("received invalid m-bus response frame")
                    retry += 1
                    mb.purge_frames(mbHandle)
                    continue
                else:
                    logger.error("Failed to receive m-bus response frame")
                    return None

                reply_data = MBusFrameData()
                logger.info(reply)
                if mb.frame_data_parse(reply, reply_data) == -1:
                    logger.error("m-bus data parse error")
                    return None
                else:
                    replies.append(reply_data)

                more_frames = False
                if reply_data.type == mbusLow.MBUS_DATA_TYPE_VARIABLE:
                    if reply_data.data_var.more_records_follow:
                        more_frames = True
                        next = MBusFrame()
                        reply = next
                        frame.control ^= mbusLow.MBUS_CONTROL_MASK_FCB
            return binConverter.toDict(replies, full)
        finally:
            self._cleanFrames(replies)              # need to cleam memory to prevent mem leak


    def getRecordstest(self, address, full):
        """for testing"""
        if address == 6:
            mb = self._mbus._libmbus
            frames = []
            import csv
            try:
                with open("test/data.csv", 'rb') as file:
                    reader = csv.reader(file, delimiter=',')
                    for row in reader:
                        frame = MBusFrame()
                        frame.start1 = int(row[0])
                        frame.length1 = int(row[1])
                        frame.length2 = int(row[2])
                        frame.start2 = int(row[3])
                        frame.control = int(row[4])
                        frame.address = int(row[5])
                        frame.control_infomation = int(row[6])
                        frame.checksum = int(row[7])
                        frame.stop = int(row[8])
                        tempType = ctypes.c_uint8 * 252
                        frame.data = tempType()
                        list = [int(x) for x in row[9].strip().split(' ')]
                        for x in range(0, len(list)):
                            frame.data[x] = list[x]
                        frame.data_size = int(row[10])
                        frame.type = int(row[11])
                        frame.timestamp = int(row[12])
                        logger.info(frame)

                        reply_data = MBusFrameData()
                        if mb.frame_data_parse(frame, reply_data) == -1:
                            logger.error("m-bus data parse error")
                        else:
                            frames.append((reply_data))
                    res = binConverter.toDict(frames, True)
                    return res
            finally:
                self._cleanFrames(frames)

    def loadDevicesFromCloud(self, existing):
        """load the devices from the cloud, together with the config"""
        self._devicesLock.acquire()
        try:
            for dev in existing:
                rec = DeviceConfig(datetime.datetime.now())
                rec.definition = dev
                asset = next((x for x in dev['assets'] if x['name'].encode('ascii', 'ignore') == "sample_frequency"), None)
                if asset and asset['state'] and 'value' in asset['state']:                               # if no asset defined, we use the default of 5 minutes
                    rec.sampleFreq = asset['state']['value']
                logger.info("sample frequency for {} = {}".format(dev["id"], rec.sampleFreq))
                self._devices[int(dev['id'])] = rec                                                     # id of device has been localized to gateway.
        finally:
            self._devicesLock.release()

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
        self.stop = False

    def run(self):
        try:
            self.mbus._gateway.send("true", None, isScanningId)
            result = {}
            newDevices = {}                             # we make a copy of the devices list and assign this to _devices again after the operation. this is to make certain that we don't work with partial objects in the 'sample' function
            self.mbus._devicesLock.acquire()
            try:
                if not self.full:  # when we rescan for all devices, then we need to make certain taht we start with an empty list
                    newDevices = self.mbus._devices.copy()
            finally:
                self.mbus._devicesLock.release()
            for address in range(0, mbusLow.MBUS_MAX_PRIMARY_SLAVES + 1):
                if self.stop: break                                             # if the user requested to stop the operation, then stop as soon as possible
                try:
                    self.mbus._gateway.send(str(mbusLow.MBUS_MAX_PRIMARY_SLAVES - address), None, scanPos)  # so the user can follow where the scan is currently
                    runAt = datetime.datetime.now()
                    dev = self.mbus.getRecords(address, True)
                    if dev:
                        self.mbus._devicesLock.acquire()
                        try:
                            if self.full or address not in self.mbus._devices:  # only process and store the result if really required: new device or doing a full scan.
                                toAdd = DeviceConfig(runAt)  # this will use the default sampling frequency by default,
                                toAdd.raw = dev
                                result[address] = toAdd
                                newDevices[address] = toAdd
                                if not self.existing:                   # if we are not synchronizing the entire list, then stop at the first device that we find.
                                    self.mbus._gateway.send(str(0), None, scanPos)  # we are stopping cause we are done, so make certain that we set the scan pos is set back to 0
                                    break
                        finally:
                            self.mbus._devicesLock.release()
                except:
                    logger.exception('error while pinging mbus device id: {}, moving on to next device'.format(address))
            if self.callback:
                self.callback(self.existing, self.full, result)
            self.mbus._devicesLock.acquire()
            try:
                self.mbus._devices = newDevices  # when done, put the new list of devices back, so we start using that one.
            finally:
                self.mbus._devicesLock.release()
        finally:
            self.mbus._gateway.send("false", None, isScanningId)


class DeviceConfig(object):
    """a class that stores all the configurations for a particular device"""

    def __init__(self, lastRunAt):
        self._sampleFreq = DefaultSamplingFrequency      #by default, sample every 5 minutes.
        self._lastRunAt = lastRunAt                      # allows us to calculate when the next run should be
        self.nextRunAt = lastRunAt + datetime.timedelta(seconds=DefaultSamplingFrequency)
        self.prevValues = {}                            # stores the previous values for the accumulative calculation

    @property
    def lastRunAt(self):
        return self._lastRunAt

    @lastRunAt.setter
    def lastRunAt(self, value):
        self._lastRunAt = value
        self.nextRunAt = value + datetime.timedelta(seconds=self._sampleFreq)

    @property
    def sampleFreq(self):
        return self._sampleFreq

    @sampleFreq.setter
    def sampleFreq(self, value):
        """allows us to easily recalculate the next run when the user changes the sampling frequency."""
        self._sampleFreq = value
        self.nextRunAt = self._lastRunAt + datetime.timedelta(seconds=value)