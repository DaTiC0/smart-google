# coding: utf-8
# Code By DaTi_Co

import json
import logging
import os

from flask import Flask, jsonify, make_response, request, send_from_directory

from action_devices import onExecute, onQuery, onSync, rexecute
from models import db
from my_oauth import oauth
from notifications import mqtt
from routes import bp

log = logging.getLogger(__name__)

# Flask Application
app = Flask(__name__, template_folder='templates')
app.config.from_object('config')
app.register_blueprint(bp, url_prefix='')
# MQTT CONNECT
mqtt.init_app(app)
mqtt.subscribe('XXX/notification')
mqtt.subscribe('YYY/status')
# SQLAlchemy DATABASE
db.init_app(app)
# OAuth2 Authorisation
oauth.init_app(app)

ALLOWED_EXTENSIONS = set(['txt', 'py'])  # for some files to save


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


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


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'  # While in development
    db.create_all()
    app.run()
