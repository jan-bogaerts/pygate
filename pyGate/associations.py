import config
import modules
import cloud

_associations = {}

def load():
    '''load all the associations'''
    global _associations
    _associations = config.loadConfig('associations.json', True)



def onAssetUpdated(module, device, asset, value):
    '''called when a sensor or actuator has updated it's value (which triggered a sent to the cloud) .'''
    if _associations:                                                                   # could be that none were defined.
        id = cloud.getDeviceId(module, device) + '_' + asset
        defs = _associations[id]
        if defs:
            initiatingMod = modules.modules[module];
            if hasattr(initiatingMod, 'getValueConverter'):
                valueConverter = initiatingMod.getValueConverter(device, asset)
            for association in defs:
                mod = modules.modules[association.module];                                  # first get the current value of the associated actuator, so we can optionally let the initiator decide how to set the value (ex: toggle buttons will change the value of the actuator according to the state of the actuator, not of the button)
                curVal = mod.getAssetValue(association.device, association.asset)
                if valueConverter:
                    modules.Actuate(mod, association.device, association.asset, valueConverter(curVal, value))
                else:
                    modules.Actuate(mod, association.device, association.asset, value)
