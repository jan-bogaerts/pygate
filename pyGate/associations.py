
import logging
logger = logging.getLogger('associations')
import json
import config
import modules
import cloud

_associations = {}

_assiociationsDefId = "assiociationdefs"

def load():
    '''load all the associations'''
    global _associations
    _associations = config.loadConfig('associations.json', True)

def syncGatewayAssets():
    """gives a processor the opertunity to add assets to the gateway which are specific to this processor
       (config stuff for instance)
    """
    cloud.addGatewayAsset("associations", _assiociationsDefId, 'associations', 'The list of currently active associations', True, 'object', 'Config')

def onActuate(actuator, value):
    """called when the associtions config param has changed."""
    if actuator == _assiociationsDefId:
        global _associations
        logger.warning("replacing associations, old value: {}, new value: {}".format(_associations, value))
        _associations = jsonVal = json.loads(value)
    else:
        logger.error("invalid actuator for assocations: {}, value: {}".format(actuator, value))

def onAssetValueChanged(module, device, asset, value):
    '''called when a sensor or actuator has updated it's value (which triggered a sent to the cloud) .'''
    try:
        if _associations:                                                                   # could be that none were defined.
            id = cloud.getDeviceId(module, device) + '_' + asset
            if id in _associations:
                defs = _associations[id]
                if defs:
                    initiatingMod = modules.modules[module]
                    if hasattr(initiatingMod, 'getValueConverter'):
                        valueConverter = initiatingMod.getValueConverter(device, asset)
                    else:
                        valueConverter = None
                    for association in defs:
                        try:
                            mod = modules.modules[association.module]                                  # first get the current value of the associated actuator, so we can optionally let the initiator decide how to set the value (ex: toggle buttons will change the value of the actuator according to the state of the actuator, not of the button)
                            if valueConverter:
                                curVal = mod.getAssetValue(association.device, association.asset)
                                modules.Actuate(mod, association.device, association.asset, valueConverter(curVal, value))
                            else:
                                modules.Actuate(mod, association.device, association.asset, value)
                        except:
                            logger.exception("failed to process associations for module: {}, device: {}, asset: {}, value: {}, for: {}".format(module, device, asset, value, association))
    except:
        logger.exception("general error while processing associations")
