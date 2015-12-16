#!/usr/bin/env python
from flask import Flask, render_template, Response, request
import paho.mqtt.client as mqtt                # provides publish-subscribe messaging support
import json

import att_iot_gateway as IOT



app = Flask(__name__)


@app.route('/')
def index():
    return 'not supported'


@app.route('/asset/<name>', methods=['PUT'])
def index(name):
    url = '/device/'  '/asset/' + name
    IOT._sendData(request.url, request.data, IOT._buildHeaders(), 'PUT')
    return 'not supported', 200