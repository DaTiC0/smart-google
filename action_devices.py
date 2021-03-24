# Code By DaTi_Co
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import config


cred = credentials.Certificate(config.FIREBASE_ADMINSDK_FILE)
firebase_admin.initialize_app(cred, {
    'databaseURL': config.DATABASEURL
})

ref = db.reference('/devices')


def report_state():
    # devices must be change to dynamic not static like this
    devices = [123, 124, 125, 126, 127] # this is for test. need to be updated to real devices
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
    # report = json.dumps(payload, indent=4, sort_keys=True)

    return payload


def rsync():
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
    snapshot = ref.child(deviceId).child('states').get()

    return snapshot


def rexecute(deviceId, parameters):
    ref.child(deviceId).child('states').update(parameters)
    states = ref.child(deviceId).child('states').get()

    return states


def onSync(body):
    # handle sync request
    payload = {
        "agentUserId": config.AGENT_USER_ID,
        "devices": rsync()
    }
    return payload


def onQuery(body):
    # handle query request
    payload = {
        "devices": {},
    }
    for input in body['inputs']:
        for device in input['payload']['devices']:
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
                    if execCommand == 'action.devices.commands.OnOff':
                        # firebaseRef.child(deviceId).child('OnOff').update({
                        #   on: params.on,
                        # });
                        parameters = params
                        rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = parameters
                        print('ON/OFF')
                        print(params)
                    elif execCommand == 'action.devices.commands.BrightnessAbsolute':
                        parameters = params
                        rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = parameters
                        print('ON/OFF')
                        print(params)
                    elif execCommand == 'action.devices.commands.StartStop':
                        parameters = {'isRunning': params['start']}
                        states = rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = states
                        print('START/STOP')
                        print(params)
                    elif execCommand == 'action.devices.commands.PauseUnpause':
                        parameters = {'isPaused': params['pause']}
                        states = rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = states
                        print('PAUSE/UNPAUSE')
                        print(params)
                    elif execCommand == 'action.devices.commands.GetCameraStream':
                        # this is the static Url for camera stream
                        # needs to be changed to stream link per device!
                        states = rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = states
                        print('CAMERA/STREAM')
                        print(params)
                    elif execCommand == 'action.devices.commands.LockUnlock':
                        parameters = {'isLocked': params['lock']}
                        states = rexecute(deviceId, parameters)
                        payload['commands'][0]['states'] = states
                        print('PAUSE/UNPAUSE')
                        print(params)
    return payload
