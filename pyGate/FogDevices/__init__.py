#!/usr/bin/env python
import paho.mqtt.client as mqtt                # provides publish-subscribe messaging support
import json
from flask import Flask, render_template, Response, request
import att_iot_gateway as IOT

import webServer


@webServer.app.route('/')
def index():
    return 'not supported'


@webServer.app.route('/asset/<name>', methods=['PUT'])
def putAsset(name):
    asset = json.loads(request.data)
    url = '/device/' + asset['deviceId'] + '/asset/' + name
    asset.remove('deviceId')                                            # this field is no longer allowed in the body
    IOT._sendData(url, asset, IOT._buildHeaders(), 'PUT')
    return 'ok', 200