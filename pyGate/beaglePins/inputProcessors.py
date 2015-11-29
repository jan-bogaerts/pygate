# defines the classes that are used to read input from the pins

import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC

class PushButton(object):
    """processes the input of a digital pin as if it was a push button (1 = true, 0 = false)"""

    def __init__(self, pin):
        self._pin = pin
        return super(PushButton, self).__init__()

    def processInput(self):
        '''reads the input of the pin and returns the corresponding value, if it was different then the previous one.
           if there is no change, None will be returned to indicate that no value has to be updated.'''
        value = GPIO.input(self._pin)
        if not self._prevValue or self._prevValue != value:
            self._prevValue = value
            return value
        return None


class ToggleButton(PushButton):
    """processes the input of a digital pin as if it was a toggle button (only toggle value upon digital input 1 (=true))
       The only difference with the push button is that a toggle button will regulate how it controls the outputs that are associated with it.
    """
    def __init__(self, pin):
        return super(ToggleButton, self).__init__(pin)

    def valueConverter(currentValue, newValue):
        '''makes certain that this object behaves like a toggle button -> check the current value of the actuator, inverse it's value
        currentValue: current value of actuator that is associated to this one
        newValue: the value of this sensor'''
        if newValue == True:
            return not currentValue


class Knob(object):

    def __init__(self, pin):
        self._pin = pin
        return super(Knob, self).__init__()

    def processInput(self):
        '''read the input of the analog pin'''
        value = ADC.read(self._pin)                     #due to bug in adc lib, values have to be read 2 times to get the latest value.
        value = ADC.read(self._pin)
        return value