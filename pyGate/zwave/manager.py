__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2015, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"


import logging
import time

from gateway import Gateway;
import deviceClasses


gateway = None                             # provides access to the cloud
network = None                             # provides access to the zwave network

_CC_Battery = 0x80
controllerStateId = 'controllerState'
discoveryStateId = 'discoverState'   #id of asset


def init(moduleName):
    """initialize all objext"""
    global gateway
    gateway = Gateway(moduleName)

def start():
    network.start()
    logging.info(gateway._moduleName + ' running')

def syncDevices(existing, Full):
    for key, node in network.nodes.iteritems():
        if node.node_id != 1:
            found = next((x for x in existing if x['id'].encode('ascii','ignore') == str(node.node_id)), None)
            if not found:
                _addDevice(node)
            else:
                existing.remove(found)              # so we know at the end which ones have to be removed.
                if Full:
                    _addDevice(node)                # this will also refresh it
    for dev in existing:                        # all the items that remain in the 'existing' list, are no longer devices in this network, so remove them
        gateway.deleteDevice(dev['id'])


def addDevice(node):
    """adds the specified node to the cloud as a device. Also adds all the assets.
    """
    if node.product_name:                       #newly included devices arent queried fully yet, so create with dummy info, update later
        gateway.addDevice(node.node_id, node.product_name, node.type)
    else:
        gateway.addDevice(node.node_id, 'unknown', node.type)
    for key, val in node.values.iteritems() :
        try:
            if val.command_class and not str(val.genre) == 'System':                # if not related to a command class, then all other fields are 'none' as well, can't t much with them. System values are not interesting, it's about frames and such (possibly for future debugging...)
                addAsset(node, val)
        except:
            logging.exception('failed to sync device ' + str(node.node_id) + ' for module ' + gateway._moduleName + ', asset: ' + str(key) + '.')
    if _CC_Battery in node.command_classes:
        gateway.addAsset('failed', node.node_id, 'failed', 'true when the battery device is no longer responding and the controller has labeled it as a failed device.', False, 'boolean', 'Secondary')


def addAsset(node, value):
    lbl = value.label.encode('ascii', 'ignore').replace('"', '\\"')        # make certain that we don't upload any illegal chars, also has to be ascii
    hlp = value.help.encode('ascii', 'ignore').replace('"', '\\"')         # make certain that we don't upload any illegal chars, also has to be ascii
    gateway.addAsset(value.value_id, node.node_id, lbl, hlp, not value.is_read_only, _getAssetType(node, value), _getStyle(node, value))
    # dont send the data yet, we have a seperate event for this

def _getAssetType(node, val):
    '''extract the asset type from the command class'''

    logging.info("node type: " + val.type)            # for debugging
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

    if dataType == 'Decimal' or dataType == 'Integer':
        if val.max and val.max != val.min:
            type += ', "maximum": ' + str(val.max)
        if val.min and val.max != val.min:
            type += ', "minimum": ' + str(val.min)
    if val.units:
        type += ', "unit": "' + val.units + '"'
    if val.data_items and isinstance(val.data_items, set):
        type += ', "enum": [' + ', '.join(['"' + y + '"' for y in val.data_items]) + ']'
    return type + "}"

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

def waitForAwake():
    '''waits until the zwave network is awakened'''
    time_started = 0
    logging.info("zwave: Waiting for network awaked")
    for i in range(0,300):
        if network.state >= network.STATE_AWAKED:
            logging.info("zwave: network awake")
            break
        else:
            time.sleep(1.0)
    if network.state < network.STATE_AWAKED:
        logging.error("zwave: Network is not awake but continue anyway")
    logging.info("zwave: Use openzwave library : %s" % network.controller.ozw_library_version)
    logging.info("zwave: Use python library : %s" % network.controller.python_library_version)
    logging.info("zwave: Use ZWave library : %s" % network.controller.library_description)
    logging.info("zwave: Network home id : %s" % network.home_id_str)
    logging.info("zwave: Controller node id : %s" % network.controller.node.node_id)
    logging.info("zwave: Controller node version : %s" % (network.controller.node.version))
    logging.info("zwave: Nodes in network : %s" % network.nodes_count)

def waitForReady():
    '''waits until the zwave network is ready'''
    logging.info("zwave: Waiting for network ready")
    for i in range(0,30):
        if network.state >= network.STATE_READY:
            logging.info("zwave: network ready")
            break
        else:
            time.sleep(1.0)
    if not network.is_ready:
        logging.info("zwave: Network is not ready but continue anyway")
    logging.info("zwave: Controller capabilities : %s" % network.controller.capabilities)
    logging.info("zwave: Controller node capabilities : %s" % network.controller.node.capabilities)
    logging.info("zwave: Nodes in network : %s" % network.nodes_count)
    logging.info("zwave: Driver statistics : %s" % network.controller.stats)

