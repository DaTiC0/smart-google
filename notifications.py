import logging
from flask_mqtt import Mqtt

logger = logging.getLogger(__name__)
mqtt = Mqtt()


def is_mqtt_connected():
    """Return True if the MQTT client is currently connected."""
    return bool(getattr(mqtt, 'connected', False))


@mqtt.on_message()
def handle_messages(_client, _userdata, message):
    logger.debug('Received message on topic %s: %s', message.topic, message.payload.decode())
    if message == 'hi':
        logger.debug('== THIS IS NOT JOKE NO HI HERE ==')


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
