# coding: utf-8
# Code By DaTi_Co

import logging
import requests
import secrets
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
        res = ref.child(deviceId).child('states').get()
        return res if res is not None else {"online": False}
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
    """Map an execution command to its device-state parameters and apply them."""
    # Dispatch map: command → parameter transformer
    _COMMAND_PARAMS = {
        'action.devices.commands.OnOff': lambda p: {'on': p['on']} if 'on' in p else None,
        'action.devices.commands.BrightnessAbsolute': lambda p: {'brightness': p.get('brightness', 100), 'on': True},
        'action.devices.commands.StartStop': lambda p: {'isRunning': p['start']},
        'action.devices.commands.PauseUnpause': lambda p: {'isPaused': p['pause']},
        'action.devices.commands.GetCameraStream': lambda p: p,
        'action.devices.commands.LockUnlock': lambda p: {'isLocked': p['lock']},
    }

    try:
        transformer = _COMMAND_PARAMS.get(execCommand)
        if transformer is None:
            logger.debug('Unhandled command: %s', execCommand)
        else:
            transformed = transformer(params)
            if transformed is None:
                logger.error("'on' parameter missing for OnOff command")
                payload['commands'][0]['status'] = 'ERROR'
                payload['commands'][0]['errorCode'] = 'hardError'
                return payload
            params = transformed
            logger.debug('Executing command: %s', execCommand)

        states = rexecute(deviceId, params)
        payload['commands'][0]['states'] = states

        return payload
    except Exception as e:
        logger.error("Error in commands: %s", e)
        payload['commands'][0]['status'] = 'ERROR'
        return payload


def _handle_execute(req):
    """Execute intent handler – runs onExecute and publishes MQTT notification."""
    payload = onExecute(req)
    try:
        if (payload.get('commands')
                and payload['commands'][0]['ids']):
            deviceId = payload['commands'][0]['ids'][0]
            params = payload['commands'][0]['states']
            mqtt.publish(
                topic=str(deviceId) + '/notification',
                payload=str(params),
                qos=0,
            )
    except Exception as mqtt_error:
        logger.warning("MQTT error: %s", mqtt_error)
    return payload


# ---------------------------------------------------------------------------
# Dispatch map: Google Home intent → handler function
# ---------------------------------------------------------------------------
_INTENT_DISPATCH = {
    "action.devices.SYNC": lambda req: onSync(),
    "action.devices.QUERY": onQuery,
    "action.devices.EXECUTE": _handle_execute,
    "action.devices.DISCONNECT": lambda req: {},
}


def actions(req):
    try:
        payload = {}
        for i in req['inputs']:
            intent = i['intent']
            logger.debug('Intent: %s', intent)
            handler = _INTENT_DISPATCH.get(intent)
            if handler is not None:
                payload = handler(req)
            else:
                logger.warning('Unexpected action requested with intent: %s', intent)
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

        n = 10**19 + secrets.randbelow(9 * 10**19 + 1)
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
