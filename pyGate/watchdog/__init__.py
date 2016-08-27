__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
import datetime
logger = logging.getLogger('watchdog')
from threading import Event

import cloud
import config

WatchDogAssetId = 'networkWatchDog'    #the asset id used by the watchdog. Change this if it interfers with your own asset id's.
PingFrequency = 300                 #the frequency in seconds, that a ping is sent out (and that the system expects a ping back)

_moduleName = None
_nextPingAt = None      # the moment in time that the next ping should be sent.
_pingCounter = 0        # the count of the ping, increments every time a ping is sent.
_lastReceived = 0       # the ping counter that was last received.
_device = None
_wakeUpEvent = Event()
_isRunning = True


#callback: handles values sent from the cloudapp to the device
def onActuate(id, value):
    global _lastReceived
    if id == str(WatchDogAssetId):
        _lastReceived = long(value)
        logger.info("received ping: " + str(_lastReceived))
        cloud.send(_moduleName, None, WatchDogAssetId, _lastReceived) # send back to cloud so that there is feedback.
    else:
        print("unknown actuator: " + id)

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.'''
    global _moduleName
    _moduleName = moduleName

def syncGatewayAssets():
    cloud.addGatewayAsset(_moduleName, WatchDogAssetId, 'network watchdog', 'monitor the network and restart if required', True, 'integer')


def ping():
    """send a ping to the server"""
    global _nextPingAt
    _nextPingAt = datetime.datetime.now() + datetime.timedelta(0, PingFrequency)
    cloud.sendCommand(config.gatewayId,  _moduleName, None, WatchDogAssetId, _pingCounter)

def checkPing():
    """check if we need to resend a ping and if we received the previous ping in time"""
    global _pingCounter
    if _nextPingAt <= datetime.datetime.now():
        if _lastReceived != _pingCounter:
            logging.error("ping didn't arrive in time, resetting connection")
            cloud.IOT._mqttClient.close()               # make certain taht the connection is closed
            cloud.IOT._mqttClient.reconnect()
            return False
        else:
            _pingCounter += 1
            ping()

    return True

def stop():
    """"called when the application terminates.  Allows us to clean up the hardware correctly, so we cn be restarted without (cold) reboot"""
    global _isRunning
    _isRunning = False
    _wakeUpEvent.set()  # wake up the thread if it was sleeping
    logger.info("stopping watchdog")

def run():
    global _isRunning
    ping()
    try:
        while _isRunning:
            checkPing()
            _wakeUpEvent.wait(PingFrequency / 15)      # ping every x minutes, so check every x/15 minutes
    except Exception as e:  # in case of an xbee error: print it and try to continue
        logger.exception("watchdog failure")