#!/usr/bin/env python
import paho.mqtt.client as mqtt                # provides publish-subscribe messaging support
import json
from flask import Flask, render_template, Response, request
import att_iot_gateway as IOT
import paho.mqtt.client as mqtt                # provides publish-subscribe messaging support
import logging

import webServer

logger = logging.getLogger('main')

_mqttClient = None

@webServer.app.route('/')
def index():
    return 'not supported'


@webServer.app.route('/asset/<name>', methods=['PUT'])
def putAsset(name):
    asset = json.loads(request.data)
    url = '/device/' + asset['deviceId'] + '/asset/' + name
    asset.remove('deviceId')                                            # this field is no longer allowed in the body
    IOT._sendData(url, str(asset), IOT._buildHeaders(), 'PUT')
    return 'ok', 200



def connectToGateway(moduleName):
    '''optional
        called when the system connects to the cloud.
    '''
    global _mqttClient                                             # we assign to this var first, so we need to make certain that they are declared as global, otherwise we create new local vars
    mqttId = 'gateway'
    _mqttClient = mqtt.Client(mqttId)
    _mqttClient.on_connect = on_connect
    _mqttClient.on_message = on_MQTTmessage
    _mqttClient.on_subscribe = on_MQTTSubscribed
    #_mqttClient.username_pw_set(brokerId, ClientKey);

    _mqttClient.connect("localhost", "1883", 60)
    _mqttClient.loop_start()


def on_connect(client, userdata, rc):
    'The callback for when the client receives a CONNACK response from the server.'

    if rc == 0:
        msg = "Connected to mqtt broker with result code "+str(rc)
        logger.info(msg)
    else:
        logger.error("Failed to connect to mqtt broker, error: " + mqtt.connack_string(rc))
        return

    topic =  "#/state"                                           #subscribe to the topics for the device
    #topic = '#'
    logger.info("subscribing to: " + topic)
    result = _mqttClient.subscribe(topic)                                                    #Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
    logger.info(result)


def on_MQTTmessage(client, userdata, msg):
    'The callback for when a PUBLISH message is received from the server.'

    payload = str(msg.payload)
    logger.info("Incoming message - topic: " + msg.topic + ", payload: " + payload)
    topicParts = msg.topic.split("/")
    if on_message is not None:
        try:
            if len(topicParts) >= 7:
                if topicParts[5] == 'device':   # 3
                    devId = topicParts[6]       # 4
                    assetId = topicParts[8]
                else:
                    devId = None
                    assetId = topicParts[6]
                on_message(devId, assetId, msg.payload)                                 #we want the second last value in the array, the last one is 'command'
            else:
                logger.error("unknown topic format: " + msg.topic)
        except:
            logger.exception("failed to process actuator command: " + msg.topic + ", payload: " + msg.payload)

def on_MQTTSubscribed(client, userdata, mid, granted_qos):
    logger.info("Subscribed to topic, receiving data from the cloud: qos=" + str(granted_qos))