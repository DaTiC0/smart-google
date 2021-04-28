from flask_mqtt import Mqtt
from action_devices import rexecute

mqtt = Mqtt()

##################################################
##################################################
# @mqtt.on_log()
# def handle_logging(client, userdata, level, buf):
#     print(client, userdata, level, buf)


@mqtt.on_message()
def handle_messages(client, userdata, message):
    print('Received message on topic {}: {}'
          .format(message.topic, message.payload.decode()))
    if message == 'hi':
        print('== THIS IS NOT JOKE NO HI HERE ==')


@mqtt.on_publish()
def handle_publish(client, userdata, mid):
    print('Published message with mid {}.'
          .format(mid))


@mqtt.on_subscribe()
def handle_subscribe(client, userdata, mid, granted_qos):
    print('Subscription id {} granted with qos {}.'
          .format(mid, granted_qos))


@mqtt.on_topic('XXX/notification')
def handle_mytopic(client, userdata, message):
    print('Received message on topic {}: {}'
          .format(message.topic, message.payload.decode()))
