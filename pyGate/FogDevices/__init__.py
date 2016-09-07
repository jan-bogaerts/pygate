#!/usr/bin/env python
import json
import logging

import paho.mqtt.client as mqtt                # provides publish-subscribe messaging support
from flask import request

#import os
#import subprocess

from core.gateway import Gateway
from core.deviceCounter import DeviceCounter
from core import config, webServer, cloud

logger = logging.getLogger('main')

_mqttClient = None
gateway = None                             # provides access to the cloud
_counter = DeviceCounter('fog')
discoveryStateId = 'discoveryState'
_discoveryState = 'off'                    # keep track if we can add or remove devices at the moment.

@webServer.app.route('/')
def index():
    return 'not supported'


@webServer.app.route('/asset/<name>', methods=['PUT'])
def putAsset(name):
    """add or update the asset. If in discovery mode, this will also trigger an add/update for the device"""
    asset = json.loads(request.data)
    allOk = True
    if _discoveryState == 'include' and gateway.deviceExists(asset['deviceId']) == False:   # if in discovery mode, an asset value also triggers an add device.
        if request.headers.get('Auth-ClientId') == config.clientId:
            addDevice(asset['deviceId'], None, request.headers.get('Auth-ClientId'), request.headers.get('Auth-ClientKey'))
            _turnDiscoveryOff()
        else:
            logger.error('wifi device has invalid client id')
            allOk = False
    if allOk:
        url = '/device/' + asset['deviceId'] + '/asset/' + name
        asset.remove('deviceId')                                            # this field is no longer allowed in the body
        if cloud._sendData(url, str(asset), 'PUT'):
            return 'ok', 200
    return 'gateway problem', 400


@webServer.app.route('/device', methods=['POST'])
def postDevice():
    if _discoveryState == 'include':
        if request.headers.get('Auth-ClientId') == config.clientId:
            devParams = json.loads(request.data)
            id = _counter.getValue()
            addDevice(id, devParams)
            _turnDiscoveryOff()
            return id
        else:
            logger.error('wifi device has invalid client id')
    else:
        logging.error("invalid request to add device: " + request.data + ": not in include mode")


@webServer.app.route('/device/<id>', methods=['DELETE'])
def deleteDevice(id):
    if _discoveryState == 'exclude':
        gateway.deleteDevice(id)
    else:
        logging.error("invalid request to delete device: " + request.data + ": not in include mode")

@webServer.app.route('/device/<device>/asset/<asset>/state', methods=['GET'])
def getAssetState(device, asset):                                        # this field is no longer allowed in the body
    return cloud.getAssetState(gateway._moduleName, device, asset)

def _turnDiscoveryOff():
    """update the internal flaf and update the cloud so that we are no longer in discovery"""
    global _discoveryState
    _discoveryState = 'off'
    gateway.send(_discoveryState, None, _discoveryState)

def addDevice(id, parameters):
    """adds the specified device to the cloud.
    :param parameters: the jston object that defines the device (title, description)
    :returns the id of the device
    """
    try:
        if parameters:
            gateway.addDevice(id, parameters['title'], parameters['description'])
        else:
            gateway.addDevice(id, 'new device', 'wifi device')
    except:
        logger.exception('error while adding device with parameters: ' + str(parameters))


def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _mqttClient, gateway
    mqttId = 'gateway'
    _mqttClient = mqtt.Client(mqttId)
    _mqttClient.on_connect = on_connect
    _mqttClient.on_message = on_MQTTmessage
    _mqttClient.on_subscribe = on_MQTTSubscribed
    _mqttClient.username_pw_set("pyGate", "abc123");
    _mqttClient.connect("localhost", "1883", 60)
    _mqttClient.loop_start()

    gateway = Gateway(moduleName)
    gateway.addGatewayAsset(discoveryStateId, 'wifi discovery state', 'add/remove wifi devices to the network', True,  '{"type" :"string", "enum": ["off","include","exclude"]}')


def on_connect(client, userdata, rc):
    'The callback for when the client receives a CONNACK response from the server.'

    if rc == 0:
        msg = "Connected to mqtt broker with result code "+str(rc)
        logger.info(msg)
    else:
        logger.error("Failed to connect to mqtt broker, error: " + mqtt.connack_string(rc))
        return

    topic = "#/state"                                           #subscribe to the topics for the device
    #topic = '#'
    logger.info("subscribing to local topics: " + topic)
    result = _mqttClient.subscribe(topic)                                                    #Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
    logger.info(result)


def on_MQTTmessage(client, userdata, msg):
    'The callback for when a PUBLISH message is received from the server.'

    payload = str(msg.payload)
    logger.info("Incoming local message - topic: " + msg.topic + ", payload: " + payload)
    topicParts = msg.topic.split("/")
    try:
        if len(topicParts) >= 7:
            if topicParts[5] == 'device':   # 3
                devId = topicParts[6]       # 4
                assetId = topicParts[8]
            else:
                devId = None
                assetId = topicParts[6]
            gateway.send(msg.payload, devId, assetId)
        else:
            logger.error("unknown topic format: " + msg.topic)
    except:
        logger.exception("failed to process sensor update: " + msg.topic + ", payload: " + msg.payload)


def on_MQTTSubscribed(client, userdata, mid, granted_qos):
    logger.info("Subscribed to topic, receiving data from local devices: qos=" + str(granted_qos))


def onDeviceActuate(device, actuator, value):
    '''called when an actuator command is received'''
    topic = "client/" + config.clientId + "/in/device/" + device
    logging.info("Publishing message to local broker - topic: " + topic + ", payload: " + value)
    _mqttClient.publish(topic, value, 0, False)

def onActuate(actuator, value):
    '''callback for actuators on the gateway level'''
    global _discoveryState
    if actuator == discoveryStateId:               #change discovery state
        _discoveryState = value
        gateway.send(value, None, _discoveryState)
    else:
        logger.error("zwave: unknown gateway actuator command: " + actuator)
