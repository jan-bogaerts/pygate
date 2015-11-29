import Adafruit_BBIO.GPIO as GPIO
import logging

class Led(object):
    '''manage an output pin as if it were a led'''

    def set(actuator, value):
        '''set the value. this will always be a string
        return the value that was actually set'''
        if value == "true":
            GPIO.output(actuator, GPIO.HIGH)
            return value
        elif value == "false":
            GPIO.output(actuator, GPIO.LOW)
            return value
        else:
            logging.error("unknown value for led output processor (actuator = " + actuator + "): " + value)