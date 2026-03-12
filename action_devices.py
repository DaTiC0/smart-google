# coding: utf-8
# Code By DaTi_Co

import json
import logging
import requests
from flask import current_app
from notifications import mqtt

logger = logging.getLogger(__name__)

try:
    import ReportState as state
    REPORTSTATE_AVAILABLE = True
except ImportError:
    state = None
    REPORTSTATE_AVAILABLE = False
    logger.warning("ReportState module not available, some features may be disabled.")

# Try to import firebase_admin, but provide fallback if not available
try:
    from firebase_admin import db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase admin not available, using mock data for testing")

# Mock data for testing when Firebase is not available
MOCK_DEVICES = {
    "test-light-1": {
        "type": "action.devices.types.LIGHT",
        "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
        "name": {"name": "Test Light"},
        "willReportState": True,
        "attributes": {"colorModel": "rgb"},
        "states": {"on": True, "brightness": 80, "online": True}
    },
    "test-switch-1": {
        "type": "action.devices.types.SWITCH",
        "traits": ["action.devices.traits.OnOff"],
        "name": {"name": "Test Switch"},
        "willReportState": True,
        "states": {"on": False, "online": True}
    }
}


class MockRef:
    @staticmethod
    def get():
        return MOCK_DEVICES

    @staticmethod
    def child(path):
        return MockChild(MOCK_DEVICES, path)


class MockChild:
    def __init__(self, data, path):
        self.data = data
        self.path = path

    def child(self, child_path):
        return MockChild(self.data, self.path + '/' + child_path)

    def get(self):
        keys = self.path.split('/')
        current = self.data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def update(self, values):
        keys = self.path.split('/')
        current = self.data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        if keys[-1] not in current:
            current[keys[-1]] = {}
        current[keys[-1]].update(values)
        return current[keys[-1]]


# firebase initialisation problem was fixed?
def reference():
    if FIREBASE_AVAILABLE:
        try:
            return db.reference('/devices')
        except Exception as e:
            # Firebase is installed but not initialized (e.g. missing credentials in dev)
            logger.warning("Firebase not initialized, falling back to mock data: %s", e)
    return MockRef()


def rstate():
    try:
        ref = reference()
        devices_data = ref.get()
        if not devices_data:
            return {"devices": {"states": {}}}

        devices = list(devices_data.keys())
        payload = {
            "devices": {
                "states": {}
            }
        }
        for device in devices:
            device = str(device)
            logger.debug('Getting Device status from: %s', device)
            state_data = rquery(device)
            if state_data:
                payload['devices']['states'][device] = state_data
            logger.debug('Device state: %s', state_data)

        return payload
    except Exception as e:
        logger.error("Error in rstate: %s", e)
        return {"devices": {"states": {}}}


def rsync():
    try:
        ref = reference()
        snapshot = ref.get()
        if not snapshot:
            return []

        DEVICES = []
        for k, v in snapshot.items():
            v_copy = v.copy()
            v_copy.pop('states', None)
            DEVICE = {
                "id": k,
            }
            DEVICE.update(v_copy)
            DEVICES.append(DEVICE)
        return DEVICES
    except Exception as e:
        logger.error("Error in rsync: %s", e)
        return []


def rquery(deviceId):
    # Sanitize deviceId to prevent path traversal attacks
    if not deviceId or '/' in deviceId or '\\' in deviceId or '..' in deviceId:
        logger.error("Invalid deviceId: %s", deviceId)
        return {"online": False}
    try:
        ref = reference()
        return ref.child(deviceId).child('states').get()
    except Exception as e:
        logger.error("Error querying device %s: %s", deviceId, e)
        return {"online": False}


def rexecute(deviceId, parameters):
    # Sanitize deviceId to prevent path traversal attacks
    if not deviceId or '/' in deviceId or '\\' in deviceId or '..' in deviceId:
        logger.error("Invalid deviceId: %s", deviceId)
        return parameters
    try:
        ref = reference()
        ref.child(deviceId).child('states').update(parameters)
        return ref.child(deviceId).child('states').get()
    except Exception as e:
        logger.error("Error executing on device %s: %s", deviceId, e)
        return parameters


def onSync():
    try:
        return {
            "agentUserId": current_app.config['AGENT_USER_ID'],
            "devices": rsync()
        }
    except Exception as e:
        logger.error("Error in onSync: %s", e)
        return {"agentUserId": "test-user", "devices": []}


def onQuery(body):
    try:
        # handle query request
        payload = {
            "devices": {},
        }
        for i in body['inputs']:
            for device in i['payload']['devices']:
                deviceId = device['id']
                data = rquery(deviceId)
                payload['devices'][deviceId] = data
        return payload
    except Exception as e:
        logger.error("Error in onQuery: %s", e)
        return {"devices": {}}


def onExecute(body):
    try:
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
    except Exception as e:
        logger.error("Error in onExecute: %s", e)
        return {'commands': [{'ids': [], 'status': 'ERROR', 'errorCode': 'deviceNotFound'}]}


def commands(payload, deviceId, execCommand, params):
    """ more clean code as was bedore.
    dont remember how state ad parameters is used """
    try:
        if execCommand == 'action.devices.commands.OnOff':
            if 'on' not in params:
                logger.error("Error: 'on' parameter missing for OnOff command")
                payload['commands'][0]['status'] = 'ERROR'
                payload['commands'][0]['errorCode'] = 'hardError'
                return payload
            params = {'on': params['on']}
            logger.debug('OnOff')
        elif execCommand == 'action.devices.commands.BrightnessAbsolute':
            params = {'brightness': params.get('brightness', 100), 'on': True}
            logger.debug('BrightnessAbsolute')
        elif execCommand == 'action.devices.commands.StartStop':
            params = {'isRunning': params['start']}
            logger.debug('StartStop')
        elif execCommand == 'action.devices.commands.PauseUnpause':
            params = {'isPaused': params['pause']}
            logger.debug('PauseUnpause')
        elif execCommand == 'action.devices.commands.GetCameraStream':
            logger.debug('GetCameraStream')
        elif execCommand == 'action.devices.commands.LockUnlock':
            params = {'isLocked': params['lock']}
            logger.debug('LockUnlock')

        # Out from elif
        states = rexecute(deviceId, params)
        payload['commands'][0]['states'] = states

        return payload
    except Exception as e:
        logger.error("Error in commands: %s", e)
        payload['commands'][0]['status'] = 'ERROR'
        return payload


def actions(req):
    try:
        payload = {}
        for i in req['inputs']:
            if i['intent'] == "action.devices.SYNC":
                payload = onSync()
            elif i['intent'] == "action.devices.QUERY":
                payload = onQuery(req)
            elif i['intent'] == "action.devices.EXECUTE":
                payload = onExecute(req)
                # SEND TEST MQTT
                try:
                    if payload.get('commands') and len(payload['commands']) > 0 and len(payload['commands'][0]['ids']) > 0:
                        deviceId = payload['commands'][0]['ids'][0]
                        params = payload['commands'][0]['states']
                        mqtt.publish(topic=str(deviceId) + '/' + 'notification',
                                     payload=str(params), qos=0)  # SENDING MQTT MESSAGE
                except Exception as mqtt_error:
                    logger.warning("MQTT error: %s", mqtt_error)
            elif i['intent'] == "action.devices.DISCONNECT":
                logger.debug("DISCONNECT ACTION")
                payload = {}
            else:
                logger.warning('Unexpected action requested: %s', json.dumps(req))
                payload = {}
        return payload
    except Exception as e:
        logger.error("Error in actions: %s", e)
        return {}


def request_sync(api_key, agent_user_id):
    try:
        url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + api_key
        data = {"agentUserId": agent_user_id, "async": True}

        response = requests.post(url, json=data)

        return response.status_code == requests.codes['ok']
    except Exception as e:
        logger.error("Error in request_sync: %s", e)
        return False


def report_state():
    try:
        if not REPORTSTATE_AVAILABLE:
            logger.warning("ReportState module not available, skipping report_state")
            return "ReportState not available"
        import secrets
        n = 10**19 + secrets.randbelow(10**20 - 10**19 + 1)
        report_state_file = {
            'requestId': str(n),
            'agentUserId': current_app.config['AGENT_USER_ID'],
            'payload': rstate(),
        }

        state.main(report_state_file)

        return "THIS IS TEST NO RETURN"
    except Exception as e:
        logger.error("Error in report_state: %s", e)
        return f"Error: {e}"
