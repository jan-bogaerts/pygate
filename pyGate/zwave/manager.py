__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


import logging
import time

from gateway import Gateway
import deviceClasses

logger = logging.getLogger('zwave')

gateway = None                             # provides access to the cloud
network = None                             # provides access to the zwave network

_CC_Battery = 0x80
_CC_Wakeup = 0x84
_CC_MultiLevelSwitch = 0x26
controllerStateId = 'controllerState'
discoveryStateId = 'discoverState'   #id of asset
networkStateId = 'networkState'
deviceStateId = 'deviceState'
refreshDeviceId = 'refreshDevice'
_discoveryMode = "Off"                      # the current discovery mode that the system is in, so we can determine when to add/refresh devices.

def init(moduleName):
    """initialize all objext"""
    global gateway
    gateway = Gateway(moduleName)

def start():
    network.start()
    logger.info(gateway._moduleName + ' running')

def syncDevices(existing, Full):
    for key, node in network.nodes.iteritems():
        if str(node.node_id) != '1':                    # for some reason, this compare doesn't work without convertion.
            found = next((x for x in existing if x['id'].encode('ascii','ignore') == str(node.node_id)), None)
            if not found:
                addDevice(node)
            else:
                existing.remove(found)              # so we know at the end which ones have to be removed.
                addDevice(node, Full)                # this will also refresh it
    for dev in existing:                        # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
        gateway.deleteDevice(dev['id'])


def addDevice(node, createDevice = True):
    """adds the specified node to the cloud as a device. Also adds all the assets.
    :param node: the device details
    :param createDevice: when true, addDevice will be called. when false, only the assets will be updated/created
    This is for prevention of overwriting the name.
    """
    try:
        if node.product_name:                       #newly included devices arent queried fully yet, so create with dummy info, update later
            name = node.product_name
        else:
            name = 'unknown'
        if createDevice:                              # for an update, we don't need to do anyhthing for the device, only the assets
            gateway.addDevice(node.node_id, name, node.type)
        items = dict(node.values)                                         # take a copy of the list cause if the network is still refreshing/loading, the list could get updated while in the loop
        gateway.addAsset('location', node.node_id, 'location', 'the physical location of the device', True, 'string', 'Config')
        for key, val in items.iteritems():
            try:
                if val.command_class and not str(val.genre).lower() == 'system':                # if not related to a command class, then all other fields are 'none' as well, can't t much with them. System values are not interesting, it's about frames and such (possibly for future debugging...)
                    addAsset(node, val)
            except:
                logger.exception('failed to sync device ' + str(node.node_id) + ' for module ' + gateway._moduleName + ', asset: ' + str(key) + '.')
        #if _CC_Battery in node.command_classes:
        #    gateway.addAsset('failed', node.node_id, 'failed', 'true when the battery device is no longer responding and the controller has labeled it as a failed device.', False, 'boolean', 'Secondary')
        gateway.addAsset('failed', node.node_id, 'failed', 'true when the device is no longer responding and the controller has labeled it as a failed device.', False, 'boolean', 'Secondary')
        # todo: potential issue: upon startup, there might not yet be an mqtt connection, send may fail
        gateway.send(node.is_failed, 'failed', node.node_id)
        gateway.addAsset(refreshDeviceId, node.node_id, 'refresh', 'Refresh all the assets and their values', True, 'boolean', 'Undefined')
        gateway.addAsset('manufacturer_name', node.node_id, 'manufacturer name', 'The name of the manufacturer', False, 'string', 'Undefined')
        gateway.addAsset('product_name', node.node_id, 'product name', 'The name of the product', False, 'string', 'Undefined')
        #todo: potential issue: upon startup, there might not yet be an mqtt connection, send may fail
        gateway.send(node.manufacturer_name, 'manufacturer_name', node.node_id)
        gateway.send(node.product_name, 'product_name', node.node_id)
    except:
        logger.exception('error while adding device: ' + str(node))


def addAsset(node, value):
    lbl = value.label.encode('ascii', 'ignore').replace('"', '\\"')        # make certain that we don't upload any illegal chars, also has to be ascii
    hlp = value.help.encode('ascii', 'ignore').replace('"', '\\"')         # make certain that we don't upload any illegal chars, also has to be ascii
    gateway.addAsset(value.value_id, node.node_id, lbl, hlp, not value.is_read_only, _getAssetType(node, value), _getStyle(node, value))
    # dont send the data yet, we have a seperate event for this

def _getAssetType(node, val):
    '''extract the asset type from the command class'''

    logger.info("node type: " + val.type)            # for debugging
    dataType = str(val.type)

    type = "{'type': "
    if dataType == 'Bool' or dataType == 'Button':
        type += "'boolean'"
    elif dataType == 'Decimal':
        type += "'number'"
    elif dataType == 'Integer' or dataType == "Byte" or dataType == 'Int' or dataType == "Short":
        type += "'integer'"
    else:
        type = '{"type": "string"'                              #small hack for now.

    if dataType == 'Decimal' or dataType == 'Integer' or dataType == "Byte" or dataType == 'Int' or dataType == "Short":
        if (val.max or val.min) and val.max != val.min:
            type = addMinMax(type, node, val)
    if val.units:
        type += ', "unit": "' + val.units + '"'
    if val.data_items and isinstance(val.data_items, set):
        type += ', "enum": [' + ', '.join(['"' + y + '"' for y in val.data_items]) + ']'
    return type + "}"

def addMinMax(type, node, val):
    if val.command_class == _CC_MultiLevelSwitch:
        return type + ', "maximum": 99, "minimum": 0'
    elif val.command_class == _CC_Wakeup:
        return type + ', "maximum": 16777215, "minimum": 0'
    else:
        return type + ', "maximum": ' + str(val.max) + ', "minimum": ' + str(val.min)

def _getStyle(node, val):
    '''check the value type, if it is the primary cc for the device, set is primary, if it is battery...'''
    if str(val.genre) == 'Config':
        return 'Config'
    elif val.command_class == _CC_Battery:
        return 'Battery'
    else:
        primaryCCs = deviceClasses.getPrimaryCCFor(node.generic, node.specific)
        if primaryCCs:                              # if the dev class has a list of cc's than we can determine primary or secondary, otherwise, it's unknown.
            if val.command_class in primaryCCs:
                return 'Primary'
            return 'Secondary'
    return "Undefined"                  # if we get here, we don't know, so it is undefined.
