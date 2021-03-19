# coding: utf-8
# Code By DaTi_Co

import os
import logging
import json
from datetime import datetime, timedelta
from flask import Flask, flash, jsonify, request, redirect, url_for, session
from flask import render_template, make_response, send_from_directory
from flask_oauthlib.provider import OAuth2Provider
from werkzeug.security import gen_salt
from werkzeug.utils import secure_filename
# LOCAL Modules
from action_devices import onSync, onQuery, onExecute, rexecute # I WILL ADD Modules LATER AFTER CLEANING THE CODE
import RequestSync as sync      # GOOGLE
import ReportState as state     # GOOGLE
from notifications import mqtt # I WILL ADD Modules LATER AFTER CLEANING THE CODE
from models import db
from models import User, Token, Grant, Client
from routes import bp # I WILL ADD Modules LATER AFTER CLEANING THE CODE
# from oauth2 import oauth

log = logging.getLogger(__name__)

# Flask Application
app = Flask(__name__, template_folder='templates')
app.config.from_object('config')
app.register_blueprint(bp, url_prefix='')
# MQTT CONNECT
# mqtt = Mqtt(app)

mqtt.init_app(app)
mqtt.subscribe('XXX/notification')
mqtt.subscribe('YYY/status')

# SQLAlchemy DATABASE
# db = SQLAlchemy(app)
db.init_app(app)
# OAuth2 Authorisation
# oauth = OAuth2Provider(app)
oauth = OAuth2Provider()
oauth.init_app(app)

ALLOWED_EXTENSIONS = set(['txt', 'py']) # for some files to save 

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

# Created for DIY Sprinkler MADE BY DATI_CO (ME)
# Sprinkler code not finished
# Using Micropython on microcontrollers
@app.route('/sprink')
def sprink():
    return "NOT OK"


@app.route('/sync')
def sync_devices():
    # sync devices via API and Token From Google
    # token must be generated from google and save localy
    ## whant to change JSON to some env secret
    sync.main(app.config['API_KEY'], app.config['AGENT_USER_ID'])
    state.main(app.config['SERVICE_ACCOUNT_FILE'], 'report_state_file.json')
    return "THIS IS TEST NO RETURN"


@app.route('/IFTTT', methods=['POST'])
def ifttt():
    # IFTTT Integration not completed
    req = request.get_json(silent=True, force=True)
    print('INCOMING IFTTT:')
    print(json.dumps(req, indent=4))
    # print(req)


    result = {
        "data": {
            'x': 'DaTi',
            'y': 'Comnpany'
        }
    }

    return result


@app.route('/smarthome', methods=['POST'])
def smarthome():
    payload = {}
    req = request.get_json(silent=True, force=True)
    print("INCOMING REQUEST FROM GOOGLE HOME:")
    print(json.dumps(req, indent=4))
    requestId = req['requestId']
    print('requestId: ' + requestId)
    for i in req['inputs']:
        if i['intent'] == "action.devices.SYNC":
            print("\nSYNC ACTION")
            payload = onSync(req)
        elif i['intent'] == "action.devices.QUERY":
            print("\nQUERY ACTION")
            payload = onQuery(req)
        elif i['intent'] == "action.devices.EXECUTE":
            print("\nEXECUTE ACTION")
            payload = onExecute(req)
            # NOT GOOD CODE
            # SEND MQTT
            deviceId = payload['commands'][0]['ids'][0]
            params = payload['commands'][0]['states']
            mqtt.publish(topic=str(deviceId) + '/' + 'notification',
                         payload=str(params), qos=0)  # SENDING MQTT MESSAGE
        elif i['intent'] == "action.devices.DISCONNECT":
            print("\nDISCONNECT ACTION")
        else:
            log.error('Unexpected action requested: %s', json.dumps(req))
            log.error('THIS IS ERROR')
    # THIS IS RESPONSE
    result = {
        'requestId': requestId,
        'payload': payload,
    }
    print('RESPONSE TO GOOGLE HOME')
    print(json.dumps(result, indent=4))
    return make_response(jsonify(result))


@app.route('/devices')
def devices():
    dev_req = onSync('OK')
    devices = dev_req['devices']
    print('Are we OK?')
    return render_template('devices.html', title='Smart-David', devices=devices)


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'
    db.create_all()
    app.run()
