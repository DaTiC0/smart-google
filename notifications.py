import logging
import threading
from collections import deque
from datetime import datetime, timezone

from flask_mqtt import Mqtt
from flask import current_app

logger = logging.getLogger(__name__)
mqtt = Mqtt()

mqtt_log_lock = threading.Lock()
mqtt_log_entries = deque(maxlen=200)

# Statuses that represent a healthy/expected MQTT event.
# `status_class` is derived from this set inside _append_mqtt_log so that
# routes and templates never need to re-declare the mapping.
POSITIVE_STATUSES = frozenset({'Connected', 'Received', 'Clean disconnect'})


def _append_mqtt_log(topic, payload, status, user_id=None):
    """Store an MQTT monitor entry in-memory with newest entries first."""
    entry = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'topic': topic,
        'payload': payload,
        'status': status,
        'status_class': 'status-pill--active' if status in POSITIVE_STATUSES else '',
        'user_id': user_id
    }
    with mqtt_log_lock:
        mqtt_log_entries.appendleft(entry)


def get_mqtt_logs(user_id=None):
    """Return a snapshot of MQTT monitor entries filtered by user_id if provided.

    A lock is used to prevent concurrent deque mutations while copying.
    """
    with mqtt_log_lock:
        logs = list(mqtt_log_entries)
    
    if user_id:
        # Filter logs for specific user + system messages
        return [log for log in logs if log['user_id'] == user_id or log['user_id'] is None]
    return logs


def _decode_payload(payload):
    """Decode MQTT payload as UTF-8, falling back to hex for binary bytes."""
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError:
        logger.debug('MQTT payload contained non-UTF8 bytes; storing hex view')
        return payload.hex()


def is_mqtt_connected():
    """Return True if the MQTT client is currently connected."""
    return bool(getattr(mqtt, 'connected', False))


@mqtt.on_connect()
def handle_connect(_client, _userdata, flags, rc):
    if rc == 0:
        logger.info('Connected to MQTT broker; flags=%s, rc=%s', flags, rc)
        _append_mqtt_log('system', f'Connected (flags={flags}, rc={rc})', 'Connected')
        return

    logger.error('MQTT connection failed; flags=%s, rc=%s', flags, rc)
    _append_mqtt_log(
        'system',
        f'Connection failed (flags={flags}, rc={rc})',
        'Connection failed',
    )


@mqtt.on_disconnect()
def handle_disconnect(_client, _userdata, rc):
    if rc == 0:
        logger.info('MQTT broker disconnected cleanly; rc=%s', rc)
        _append_mqtt_log('system', f'Disconnected cleanly (rc={rc})', 'Clean disconnect')
    else:
        logger.warning('MQTT broker disconnected unexpectedly; rc=%s', rc)
        _append_mqtt_log('system', f'Unexpected disconnect (rc={rc})', 'Disconnected')


@mqtt.on_message()
def handle_messages(_client, _userdata, message):
    payload = _decode_payload(message.payload)
    topic = message.topic
    logger.debug('Received message on topic %s: %s', topic, payload)
    
    # Expected topic structure: {user_id}/{device_id}/{notification|status}
    # Current supported topics: 
    # {user_id}/{device_id}/notification
    # {user_id}/{device_id}/status
    
    parts = topic.split('/')
    user_id = None
    if len(parts) >= 3:
        user_id = parts[0]
        device_id = parts[1]
        msg_type = parts[2]
        
        # Try to update Firebase if it's a status message
        if msg_type == 'status':
            try:
                from firebase_admin import db
                # Update status in /users/{user_id}/devices/{device_id}/states
                # Assuming payload is a JSON string of states
                import json
                state_updates = json.loads(payload)
                db.reference(f'/users/{user_id}/devices/{device_id}/states').update(state_updates)
                logger.debug("Updated Firebase status for %s/%s", user_id, device_id)
            except Exception as e:
                logger.error("Failed to update Firebase from MQTT: %s", e)

    _append_mqtt_log(topic, payload, 'Received', user_id=user_id)


@mqtt.on_publish()
def handle_publish(_client, _userdata, mid):
    logger.debug('Published message with mid %s.', mid)


@mqtt.on_subscribe()
def handle_subscribe(_client, _userdata, mid, granted_qos):
    logger.debug('Subscription id %s granted with qos %s.', mid, granted_qos)
