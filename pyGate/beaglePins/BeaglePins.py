# this plugin module provides access to the pins of a beaglebone
# the config file 'beaglePins.config' defines which pins should be used and how.

import logging
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC

import config
import device
from inputProcessors import *


_device = None                                          # we are a single device, not a full gateway, so use this wrapper to manage
_pinLayouts = None
_inputProcessors = {}                                     # a dictionary of objects that manage the input pins. This allows us to make the processing of an input signal, variable.Ex, some pins have push buttons, others have toggles,...
_outputProcessors = {}                                  # a dictionary of outputs

def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
        Always called first (before updateAssets) '''
    global _cloud, _pinLayouts
    _device = device.Device(moduleName, 'beagle')
    configs = config.loadConfig('beaglePins', True)
    _pinLayouts = configs['pinLayouts']
    ADC.setup()                                        # need to start the ADC driver as well
    setupGPIO()

def syncDevices(existing):
    '''optional
       allows a module to synchronize it's device list. 
       existing: the list of devices that are already known in the cloud for this module.'''
    if not existing:
        _device.createDevice('beagle pins', 'all the pins on the beagle bone')
    for pin in _pinLayouts:
        _device.addAsset(pin['id'], pin['name'], pin['description'], pin['isActuator'], pin['type'])
    
         
def run():
    ''' required
        main function of the plugin module
        loop over all the input pins and do a readout'''
    for key, value in _pinLayouts.iteritems():
        result = value.processInput()
        if result:
            _device.send(result, key)


def onActuate(actuator, value):
    """called when an actuator command was received (either internally from the plugin system or from the cloud)"""
    subject = _outputProcessors[actuator]
    if subject:
        value = subject.set(value)
        if value:
            _device.send(value, actuator)                #provide feedback to the cloud that the operation was succesful
    else:
        logging.error('asset: ' + actuator + " not registered as an actuator, can't set value: " + value)

def getValueConverter(device, asset):
    '''check if the specified asset is a toggle button, if so, we need to use a value converter'''
    found = _inputProcessors[asset]
    if found:
        return found.valueConverter
    return None

def setupGPIO():
    '''init all the pins and set up the correct processing objects for them '''
    for pinDef in _pinLayouts:
        dataType = pinDef['type'].lower()
        if dataType == 'boolean':
            setupDigitalGPIO()
        elif dataType == 'integer' or dataType == 'number':
            setupADCGPIO()


def setupDigitalGPIO():
    if pinDef['isActuator'] == True:
        GPIO.setup(pinDef['pin'], GPIO.OUT)
        _outputProcessors[pinDef['id']] = Led(pinDef['pin'])
    else:
        GPIO.setup(pinDef['pin'], GPIO.IN)
        if pinDef['inputProcessor']:
            processor = pinDef['inputProcessor']
        else:
            processor = 'push-button'                           # default value in case no processor was specified.
        if processor == 'push-button':
            _inputProcessors[pinDef['id']] = PushButton(pinDef['pin'])
        elif processor == 'toggle-button':
            _inputProcessors[pinDef['id']] = ToggleButton(pinDef['pin'])
        else:
            logging.error('unknown input processor: ' + processor + ' for pin: ' + pinDef['pin'] + ", id: " + pinDef['id'])

def setupADCGPIO():
    if pinDef['isActuator'] == True:
        logging.error('Beagle bone does not support ADC acatuators')
    else:
        if pinDef['inputProcessor']:
            processor = pinDef['inputProcessor']
        else:
            processor = 'knob'                           # default value in case no processor was specified.
        if processor == 'knob':
            _inputProcessors[pinDef['id']] = Knob(pinDef['pin'])
        else:
            logging.error('unknown input processor: ' + processor + ' for pin: ' + pinDef['pin'] + ", id: " + pinDef['id'])