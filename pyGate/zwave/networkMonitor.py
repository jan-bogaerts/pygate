__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

import logging
from louie import dispatcher #, All

from openzwave.network import ZWaveNetwork


def _networkFailed():
    """handle event"""

def _networkStarted():
    """handle event"""

def _networkReady():
    """handle event"""

def _networkStopped():
    """handle event"""

def _networkResetted():
    """handle event"""

def _networkAwaked():
    """handle event"""

def _essentialsQueried():
    """handle event"""

def _awakeQueried():
    """handle event"""

def _allQueried():
    """handle event"""


def disconnectNetworkSignals():
    dispatcher.disconnect(_networkFailed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
    dispatcher.disconnect(_networkStarted, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
    dispatcher.disconnect(_networkReady, ZWaveNetwork.SIGNAL_NETWORK_READY)
    dispatcher.disconnect(_networkStopped, ZWaveNetwork.SIGNAL_NETWORK_STOPPED)
    dispatcher.disconnect(_networkResetted, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    dispatcher.disconnect(_networkAwaked, ZWaveNetwork.SIGNAL_NETWORK_AWAKED)

    dispatcher.disconnect(_essentialsQueried, ZWaveNetwork.SIGNAL_ESSENTIAL_NODE_QUERIES_COMPLETE)
    dispatcher.disconnect(_awakeQueried, ZWaveNetwork.SIGNAL_NODE_QUERIES_COMPLETE)
    dispatcher.disconnect(_allQueried, ZWaveNetwork.SIGNAL_ALL_NODES_QUERIED)


def connectNetworkSignals():
    dispatcher.connect(_networkFailed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
    dispatcher.connect(_networkStarted, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
    dispatcher.connect(_networkReady, ZWaveNetwork.SIGNAL_NETWORK_READY)
    dispatcher.connect(_networkStopped, ZWaveNetwork.SIGNAL_NETWORK_STOPPED)
    dispatcher.connect(_networkResetted, ZWaveNetwork.SIGNAL_NETWORK_RESETTED)
    dispatcher.connect(_networkAwaked, ZWaveNetwork.SIGNAL_NETWORK_AWAKED)

    #todo: possible issue here: these might have to be dicsonncected for a reset, like other node events
    dispatcher.connect(_essentialsQueried, ZWaveNetwork.SIGNAL_ESSENTIAL_NODE_QUERIES_COMPLETE)
    dispatcher.connect(_awakeQueried, ZWaveNetwork.SIGNAL_AWAKE_NODES_QUERIED)
    dispatcher.connect(_allQueried, ZWaveNetwork.SIGNAL_ALL_NODES_QUERIED)