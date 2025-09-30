# Mock Flask-MQTT for testing
class MockMqtt:
    def __init__(self):
        self.handlers = {}
    
    def init_app(self, app):
        pass
    
    def subscribe(self, topic):
        print(f"Subscribed to MQTT topic: {topic}")
    
    def publish(self, topic, payload, qos=0):
        print(f"Publishing to {topic}: {payload}")
    
    def on_message(self):
        def decorator(f):
            self.handlers['message'] = f
            return f
        return decorator
    
    def on_publish(self):
        def decorator(f):
            self.handlers['publish'] = f
            return f
        return decorator
    
    def on_subscribe(self):
        def decorator(f):
            self.handlers['subscribe'] = f
            return f
        return decorator
    
    def on_topic(self, topic):
        def decorator(f):
            self.handlers[topic] = f
            return f
        return decorator

# Export
Mqtt = MockMqtt
