# Code By DaTi_Co
from os import environ
from firebase_admin import db
import requests
from flask import current_app

# firebase initialisation problem was fixed?
def reference():
    # Firebase Realtime Database module.
    ref = db.reference('/devices')
    return ref


def report_state():
    ref = reference()
    # Getting devices from Firebase as list
    devices = list(ref.get().keys())
    payload = {
        "devices": {
            "states": {}
        }
    }
    for device in devices:
        device = str(device)
        print('\nGetting Device status from: ' + device)
        state = rquery(device)
        payload['devices']['states'][device] = state
        print(state)

    return payload


def rsync():
    ref = reference()
    snapshot = ref.get()
    DEVICES = []
    for k, v in snapshot.items():
        v.pop('states', None)
        DEVICE = {
            "id": k,
        }
        DEVICE.update(v)

        DEVICES.append(DEVICE)
    return DEVICES


def rquery(deviceId):
    ref = reference()
    return ref.child(deviceId).child('states').get()


def rexecute(deviceId, parameters):
    ref = reference()
    ref.child(deviceId).child('states').update(parameters)
    return ref.child(deviceId).child('states').get()


def onSync(body):
    # handle sync request
    payload = {
        "agentUserId": current_app.config['AGENT_USER_ID'],
        "devices": rsync()
    }
    return payload


def onQuery(body):
    # handle query request
    payload = {
        "devices": {},
    }
    for i in body['inputs']:
        for device in i['payload']['devices']:
            deviceId = device['id']
            print('DEVICE ID: ' + deviceId)
            data = rquery(deviceId)
            payload['devices'][deviceId] = data
    return payload


def onExecute(body):
    # handle execute request
    payload = {
        'commands': [{
            'ids': [],
            'status': 'SUCCESS',
            'states': {
                'online': True,
            },
        }],
    }
    for i in body['inputs']:
        for command in i['payload']['commands']:
            for device in command['devices']:
                deviceId = device['id']
                payload['commands'][0]['ids'].append(deviceId)
                for execution in command['execution']:
                    execCommand = execution['command']
                    params = execution['params']
                    # First try to refactor
                    payload = commands(payload, deviceId, execCommand, params)
    return payload


def commands(payload, deviceId, execCommand, params):
    # more clean code as was bedore. dont remember how state ad parameters is used
    if execCommand == 'action.devices.commands.OnOff':
        print('OnOff')
    elif execCommand == 'action.devices.commands.BrightnessAbsolute':
        print('BrightnessAbsolute')
    elif execCommand == 'action.devices.commands.StartStop':
        params = {'isRunning': params['start']}
        print('StartStop')
    elif execCommand == 'action.devices.commands.PauseUnpause':
        params = {'isPaused': params['pause']}
        print('PauseUnpause')
    elif execCommand == 'action.devices.commands.GetCameraStream':
        print('GetCameraStream')
    elif execCommand == 'action.devices.commands.LockUnlock':
        params = {'isLocked': params['lock']}
        print('LockUnlock')
    # Out from elif
    states = rexecute(deviceId, params)
    payload['commands'][0]['states'] = states

    return payload


def request_sync(api_key, agent_user_id):
    """This function does blah blah."""
    url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + api_key
    data = {"agentUserId": agent_user_id, "async": True}

    response = requests.post(url, json=data)

    print('\nRequests Code: %s' %
          requests.codes['ok'] + '\nResponse Code: %s' % response.status_code)
    print('\nResponse: ' + response.text)

    return response.status_code == requests.codes['ok']
