import logging
import threading
from collections import deque
from datetime import datetime, timezone

from flask_mqtt import Mqtt

logger = logging.getLogger(__name__)
mqtt = Mqtt()

mqtt_log_lock = threading.Lock()
mqtt_log_entries = deque(maxlen=100)


def _append_mqtt_log(topic, payload, status):
    """Store an MQTT monitor entry in-memory with newest entries first."""
    entry = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'topic': topic,
        'payload': payload,
        'status': status,
    }
    with mqtt_log_lock:
        mqtt_log_entries.appendleft(entry)


def get_mqtt_logs():
    """Return a snapshot of MQTT monitor entries.

    A lock is used to prevent concurrent deque mutations while copying.
    """
    with mqtt_log_lock:
        return list(mqtt_log_entries)


def _decode_payload(payload):
    """Decode MQTT payload as UTF-8, falling back to hex for binary bytes."""
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError:
        logger.warning('MQTT payload contained non-UTF8 bytes; storing hex view')
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
    logger.debug('Received message on topic %s: %s', message.topic, payload)
    _append_mqtt_log(message.topic, payload, 'Received')


@mqtt.on_publish()
def handle_publish(_client, _userdata, mid):
    logger.debug('Published message with mid %s.', mid)


@mqtt.on_subscribe()
def handle_subscribe(_client, _userdata, mid, granted_qos):
    logger.debug('Subscription id %s granted with qos %s.', mid, granted_qos)
