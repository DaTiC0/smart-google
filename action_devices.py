# coding: utf-8
# Code By DaTi_Co

import json
import logging
import requests
import secrets
from notifications import mqtt
from firebase_utils import (
    _normalize_user_scope,
    _get_user_device_states_ref,
    reference,
)

logger = logging.getLogger(__name__)

# Fallback identifier for cases where user scope cannot be determined
UNKNOWN_USER_ID = "unknown"

try:
    import ReportState as state
    REPORTSTATE_AVAILABLE = True
except ImportError:
    state = None
    REPORTSTATE_AVAILABLE = False
    logger.warning("ReportState module not available, some features may be disabled.")


def _to_sync_device(device_id, raw_data):
    """Convert Firebase record to SYNC-compatible device object."""
    if not isinstance(raw_data, dict):
        return None

    device_copy = raw_data.copy()
    device_copy.pop('states', None)
    device_copy['id'] = device_id
    return device_copy


def _build_sync_devices(snapshot):
    """Build sorted SYNC-compatible devices from snapshot."""
    if not isinstance(snapshot, dict):
        return []

    devices = []
    for device_id, raw_data in snapshot.items():
        sync_device = _to_sync_device(device_id, raw_data)
        if sync_device:
            devices.append(sync_device)
    devices.sort(key=lambda item: item['id'])
    return devices


def _get_scoped_snapshot(user_id):
    """Get per-user device snapshot from scoped Firebase path."""
    user_scope = _normalize_user_scope(user_id)
    if not user_scope:
        return {}
    return reference(user_scope).get() or {}


def _get_scoped_device_states(device_id, user_id):
    """Get device states from user-scoped Firebase path."""
    ref = _get_user_device_states_ref(user_id, device_id)
    if not ref:
        return None
    return ref.get()


def rstate(user_id=None):
    try:
        devices_data = _get_scoped_snapshot(user_id)
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
            state_data = rquery(device, user_id=user_id)
            if state_data:
                payload['devices']['states'][device] = state_data
            logger.debug('Device state: %s', state_data)

        return payload
    except Exception as e:
        logger.error("Error in rstate: %s", e)
        return {"devices": {"states": {}}}


def rsync(user_id=None):
    try:
        snapshot = _get_scoped_snapshot(user_id)
        return _build_sync_devices(snapshot)
    except Exception as e:
        logger.error("Error in rsync: %s", e)
        return []


def _normalize_device_type(device_type):
    """Return concise lowercase type for UI icon mapping."""
    if not device_type:
        return 'devices'

    type_value = str(device_type)
    if 'action.devices.types.' in type_value:
        type_value = type_value.split('action.devices.types.', 1)[1]
    return type_value.lower()


def get_dashboard_devices(user_id=None):
    """Return Firebase-backed device data for the Device Management dashboard."""
    try:
        snapshot = _get_scoped_snapshot(user_id)
        devices = []

        for device_id, raw_data in snapshot.items():
            if not isinstance(raw_data, dict):
                continue

            states = raw_data.get('states') if isinstance(raw_data.get('states'), dict) else {}
            name_info = raw_data.get('name') if isinstance(raw_data.get('name'), dict) else {}

            normalized_type = _normalize_device_type(raw_data.get('type'))
            display_name = name_info.get('name') or device_id
            is_online = bool(states.get('online', False))

            devices.append({
                'id': device_id,
                'display_name': display_name,
                'type': raw_data.get('type', 'Unknown'),
                'type_label': normalized_type.replace('_', ' ').title(),
                'icon': normalized_type if normalized_type in {
                    'light', 'heating', 'ac', 'camera', 'door', 'alarm', 'garage', 'garden'
                } else 'devices',
                'is_online': is_online,
                'status': 'Online' if is_online else 'Offline',
                'status_class': 'status-pill--active' if is_online else '',
            })

        devices.sort(key=lambda item: item['display_name'].lower())
        return devices
    except Exception as e:
        logger.error("Error getting dashboard devices: %s", e)
        return []


def rquery(deviceId, user_id=None):
    # Sanitize deviceId to prevent path traversal attacks
    if not deviceId or '/' in deviceId or '\\' in deviceId or '..' in deviceId:
        logger.error("Invalid deviceId: %s", deviceId)
        return {"online": False}
    try:
        res = _get_scoped_device_states(deviceId, user_id)
        return res if res is not None else {"online": False}
    except Exception as e:
        logger.error("Error querying device %s: %s", deviceId, e)
        return {"online": False}


def rexecute(deviceId, parameters, user_id=None):
    # Sanitize deviceId to prevent path traversal attacks
    if not deviceId or '/' in str(deviceId) or '\\' in str(deviceId) or '..' in str(deviceId):
        logger.error("Invalid deviceId: %s", deviceId)
        return parameters
    try:
        ref = _get_user_device_states_ref(user_id, deviceId)
        if not ref:
            return parameters
        ref.update(parameters)
        updated = ref.get()
        return updated if updated is not None else parameters
    except Exception as e:
        logger.error("Error executing on device %s: %s", deviceId, e)
        return parameters


def onSync(user_id=None, agent_user_id=None):
    try:
        resolved_user = _normalize_user_scope(user_id)
        agent_user = str(agent_user_id if agent_user_id is not None else (resolved_user or UNKNOWN_USER_ID))
        return {
            "agentUserId": agent_user,
            "devices": rsync(resolved_user)
        }
    except Exception as e:
        logger.error("Error in onSync: %s", e)
        return {"agentUserId": UNKNOWN_USER_ID, "devices": []}


def onQuery(body, user_id=None):
    try:
        # handle query request
        payload = {
            "devices": {},
        }
        for i in body['inputs']:
            for device in i['payload']['devices']:
                deviceId = device['id']
                data = rquery(deviceId, user_id=user_id)
                payload['devices'][deviceId] = data
        return payload
    except Exception as e:
        logger.error("Error in onQuery: %s", e)
        return {"devices": {}}


def onExecute(body, user_id=None):
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
                        payload = commands(payload, deviceId, execCommand, params, user_id=user_id)
        return payload
    except Exception as e:
        logger.error("Error in onExecute: %s", e)
        return {'commands': [{'ids': [], 'status': 'ERROR', 'errorCode': 'deviceNotFound'}]}


def commands(payload, deviceId, execCommand, params, user_id=None):
    """Normalize and execute smart home commands on a specific device."""
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
        states = rexecute(deviceId, params, user_id=user_id)
        payload['commands'][0]['states'] = states

        return payload
    except Exception as e:
        logger.error("Error in commands: %s", e)
        payload['commands'][0]['status'] = 'ERROR'
        return payload


def actions(req, user_id=None, agent_user_id=None):
    try:
        payload = {}
        for i in req['inputs']:
            if i['intent'] == "action.devices.SYNC":
                payload = onSync(user_id=user_id, agent_user_id=agent_user_id)
            elif i['intent'] == "action.devices.QUERY":
                payload = onQuery(req, user_id=user_id)
            elif i['intent'] == "action.devices.EXECUTE":
                payload = onExecute(req, user_id=user_id)
                # SEND TEST MQTT
                try:
                    if payload.get('commands') and payload['commands'] and payload['commands'][0]['ids']:
                        deviceId = payload['commands'][0]['ids'][0]
                        params = payload['commands'][0]['states']

                        # Normalize user_id for MQTT topic to prevent injection
                        safe_user = _normalize_user_scope(user_id)
                        if safe_user:
                            # Multi-tenant MQTT topic: {user_id}/{device_id}/notification
                            mqtt_topic = f"{safe_user}/{deviceId}/notification"
                            mqtt.publish(topic=mqtt_topic,
                                         payload=str(params), qos=0)  # SENDING MQTT MESSAGE
                        else:
                            logger.warning("Skipping MQTT publish: invalid user scope %s", user_id)
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

        response = requests.post(url, json=data, timeout=10)

        return response.status_code == requests.codes['ok']
    except Exception as e:
        logger.error("Error in request_sync: %s", e)
        return False


def report_state(user_id=None):
    try:
        if not REPORTSTATE_AVAILABLE:
            logger.warning("ReportState module not available, skipping report_state")
            return "ReportState not available"

        n = 10**19 + secrets.randbelow(9 * 10**19 + 1)
        report_state_file = {
            'requestId': str(n),
            'agentUserId': user_id or UNKNOWN_USER_ID,
            'payload': rstate(user_id),
        }

        state.main(report_state_file)

        return "THIS IS TEST NO RETURN"
    except Exception as e:
        logger.error("Error in report_state: %s", e)
        return f"Error: {e}"
