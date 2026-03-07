from flask_mqtt import Mqtt

mqtt = Mqtt()


def is_mqtt_connected():
    """Return True if the MQTT client is currently connected."""
    return bool(getattr(mqtt, 'connected', False))


@mqtt.on_message()
def handle_messages(_client, _userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
    if message == 'hi':
        print('== THIS IS NOT JOKE NO HI HERE ==')


@mqtt.on_publish()
def handle_publish(_client, _userdata, mid):
    print(f'Published message with mid {mid}.')


@mqtt.on_subscribe()
def handle_subscribe(_client, _userdata, mid, granted_qos):
    print(f'Subscription id {mid} granted with qos {granted_qos}.')


@mqtt.on_topic('XXX/notification')
def handle_mytopic(_client, _userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')


@mqtt.on_topic('ZZZ/notification')
def handle_ztopic(_client, _userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
