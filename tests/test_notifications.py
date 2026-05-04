import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes
from app import app as flask_app
from notifications import (
    _append_mqtt_log,
    get_mqtt_logs,
    handle_connect,
    handle_disconnect,
    handle_messages,
    mqtt_log_entries,
    mqtt_log_lock,
)


class NotificationsHandlersTest(unittest.TestCase):
    def setUp(self):
        with mqtt_log_lock:
            mqtt_log_entries.clear()

    def test_handle_connect_success_records_connected(self):
        handle_connect(None, None, {'session present': 0}, 0)
        logs = get_mqtt_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['status'], 'Connected')

    def test_handle_connect_failure_records_error_state(self):
        handle_connect(None, None, {'session present': 0}, 5)
        logs = get_mqtt_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['status'], 'Connection failed')

    def test_handle_disconnect_variants(self):
        handle_disconnect(None, None, 0)
        handle_disconnect(None, None, 7)
        logs = get_mqtt_logs()
        self.assertEqual(logs[0]['status'], 'Disconnected')
        self.assertEqual(logs[1]['status'], 'Clean disconnect')

    def test_handle_messages_binary_payload_falls_back_to_hex(self):
        message = SimpleNamespace(topic='sensor/bytes', payload=b'\xff\xfeA')
        handle_messages(None, None, message)
        logs = get_mqtt_logs()
        self.assertEqual(logs[0]['topic'], 'sensor/bytes')
        self.assertEqual(logs[0]['payload'], 'fffe41')
        self.assertEqual(logs[0]['status'], 'Received')

    def test_log_buffer_keeps_latest_100_entries(self):
        for idx in range(105):
            _append_mqtt_log('topic', f'payload-{idx}', 'Received')

        logs = get_mqtt_logs()
        self.assertEqual(len(logs), 100)
        self.assertEqual(logs[0]['payload'], 'payload-104')
        self.assertEqual(logs[-1]['payload'], 'payload-5')


class MqttRouteViewModelTest(unittest.TestCase):
    def test_mqtt_route_renders_dynamic_context(self):
        sample_logs = [
            {
                'timestamp': '2026-05-04 10:00:00 UTC',
                'topic': 'system',
                'payload': 'Connected',
                'status': 'Connected',
            },
            {
                'timestamp': '2026-05-04 10:01:00 UTC',
                'topic': 'system',
                'payload': 'Failed',
                'status': 'Connection failed',
            },
        ]

        with flask_app.test_request_context('/mqtt'), \
             patch('routes.is_mqtt_connected', return_value=True), \
             patch('routes.get_mqtt_logs', return_value=sample_logs), \
             patch('routes.render_template', return_value='ok') as render_mock:
            response = routes.mqtt_log.__wrapped__()

        self.assertEqual(response, 'ok')
        render_mock.assert_called_once()
        args, kwargs = render_mock.call_args
        self.assertEqual(args[0], 'mqtt_log.html')
        self.assertTrue(kwargs['broker_connected'])
        self.assertIsInstance(kwargs['tls_enabled'], bool)
        self.assertEqual(kwargs['log_entries'][0]['status_class'], 'status-pill--active')
        self.assertEqual(kwargs['log_entries'][1]['status_class'], '')


if __name__ == '__main__':
    unittest.main()
