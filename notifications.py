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
    entry = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'topic': topic,
        'payload': payload,
        'status': status,
    }
    with mqtt_log_lock:
        mqtt_log_entries.appendleft(entry)


def get_mqtt_logs():
    with mqtt_log_lock:
        return list(mqtt_log_entries)


def is_mqtt_connected():
    """Return True if the MQTT client is currently connected."""
    return bool(getattr(mqtt, 'connected', False))


@mqtt.on_connect()
def handle_connect(_client, _userdata, flags, rc):
    logger.info('Connected to MQTT broker; flags=%s, rc=%s', flags, rc)
    _append_mqtt_log('system', f'Connected (flags={flags}, rc={rc})', 'Connected')


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
    payload = message.payload.decode(errors='replace')
    logger.debug('Received message on topic %s: %s', message.topic, payload)
    _append_mqtt_log(message.topic, payload, 'Received')


@mqtt.on_publish()
def handle_publish(_client, _userdata, mid):
    logger.debug('Published message with mid %s.', mid)


@mqtt.on_subscribe()
def handle_subscribe(_client, _userdata, mid, granted_qos):
    logger.debug('Subscription id %s granted with qos %s.', mid, granted_qos)


@mqtt.on_topic('XXX/notification')
def handle_mytopic(_client, _userdata, message):
    logger.debug('Received message on topic %s: %s', message.topic, message.payload.decode())


@mqtt.on_topic('ZZZ/notification')
def handle_ztopic(_client, _userdata, message):
    logger.debug('Received message on topic %s: %s', message.topic, message.payload.decode())
