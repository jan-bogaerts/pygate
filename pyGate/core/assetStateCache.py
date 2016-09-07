__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


###############################################
# This module is responsible for keeping the last known state of assets, so that the system doesn't always
# have to request it from the cloud, but can update the value from it's internal engine.
# only assets who's state has previously been requested, are buffered.
# this is used by modules such as groups or liato
###############################################

import att_iot_gateway.att_iot_gateway as IOT                              #provide cloud support

_buffer = {}

def getValue(assetId, devId):
    key = str(devId) + "_" + str(assetId)
    if key in _buffer:
        return _buffer[key]
    else:
        value = IOT.getAssetState(assetId, devId)
        if value and 'value' in value:
            value = value['value']
        else:
            value = None
        _buffer[key] = value
        return value

def tryUpdateValue(module, device, asset, value):
    key = str(module) + "_" + str(device) + "_" + str(asset)
    if key in _buffer:
        _buffer[key] = value