from flask_mqtt import Mqtt

mqtt = Mqtt()

##################################################
##################################################
# @mqtt.on_log()
# def handle_logging(client, userdata, level, buf):
#     print(client, userdata, level, buf)


@mqtt.on_message()
def handle_messages(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
    if message == 'hi':
        print('== THIS IS NOT JOKE NO HI HERE ==')


@mqtt.on_publish()
def handle_publish(client, userdata, mid):
    print(f'Published message with mid {mid}.')


@mqtt.on_subscribe()
def handle_subscribe(client, userdata, mid, granted_qos):
    print(f'Subscription id {mid} granted with qos {granted_qos}.')


@mqtt.on_topic('XXX/notification')
def handle_mytopic(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')


@mqtt.on_topic('ZZZ/notification')
def handle_ztopic(client, userdata, message):
    print(f'Received message on topic {message.topic}: {message.payload.decode()}')
