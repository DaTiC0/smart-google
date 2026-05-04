import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import json

# Set environment variables for testing
import os
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['APP_ENV'] = 'testing'
os.environ['AGENT_USER_ID'] = 'test-fallback-user'

from action_devices import onSync, actions, rquery
from notifications import handle_messages, get_mqtt_logs, _append_mqtt_log

class MultiTenantTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['AGENT_USER_ID'] = 'test-fallback-user'
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('action_devices.db')
    @patch('action_devices.FIREBASE_AVAILABLE', True)
    def test_on_sync_scoped_path(self, mock_db):
        # Mock Firebase response for user 123
        mock_ref = MagicMock()
        mock_db.reference.return_value = mock_ref
        mock_ref.get.return_value = {
            "device1": {"name": {"name": "Light 1"}, "type": "light"}
        }

        # Call onSync for user 123
        response = onSync(user_id="123")

        # Verify correct Firebase path was hit
        mock_db.reference.assert_called_with('/users/123/devices')
        self.assertEqual(response['agentUserId'], "123")
        self.assertEqual(len(response['devices']), 1)
        self.assertEqual(response['devices'][0]['id'], "device1")

    @patch('action_devices.mqtt')
    @patch('action_devices.db')
    @patch('action_devices.FIREBASE_AVAILABLE', True)
    def test_on_execute_mqtt_topic(self, mock_db, mock_mqtt):
        # Mock request for user 456
        req = {
            "requestId": "req1",
            "inputs": [{
                "intent": "action.devices.EXECUTE",
                "payload": {
                    "commands": [{
                        "devices": [{"id": "fan1"}],
                        "execution": [{
                            "command": "action.devices.commands.OnOff",
                            "params": {"on": True}
                        }]
                    }]
                }
            }]
        }

        # Mock Firebase update
        mock_ref = MagicMock()
        mock_db.reference.return_value = mock_ref

        # Call actions
        actions(req, user_id="456")

        # Verify MQTT topic is scoped to user 456
        expected_topic = "456/fan1/notification"
        mock_mqtt.publish.assert_called()
        call_args = mock_mqtt.publish.call_args
        self.assertEqual(call_args.kwargs['topic'], expected_topic)

    @patch('firebase_admin.db')
    def test_mqtt_status_update_firebase_path(self, mock_db):
        # Mock MQTT message: user 789 reports status for lamp1
        mock_message = MagicMock()
        mock_message.topic = "789/lamp1/status"
        mock_message.payload = b'{"on": false, "online": true}'

        # Call handle_messages
        handle_messages(None, None, mock_message)

        # Verify Firebase update path is scoped to user 789
        expected_path = "/users/789/devices/lamp1/states"
        mock_db.reference.assert_called_with(expected_path)
        mock_db.reference().update.assert_called_with({"on": False, "online": True})

    def test_mqtt_log_filtering(self):
        # Clear logs (since they are in-memory deque)
        import notifications
        with notifications.mqtt_log_lock:
            notifications.mqtt_log_entries.clear()

        # Append logs for different users
        _append_mqtt_log("1/d1/status", "payload1", "Received", user_id="1")
        _append_mqtt_log("2/d2/status", "payload2", "Received", user_id="2")
        _append_mqtt_log("system", "connected", "Connected", user_id=None)

        # Get logs for user 1
        user1_logs = get_mqtt_logs(user_id="1")
        self.assertEqual(len(user1_logs), 2)  # user 1 log + system log
        topics = [log['topic'] for log in user1_logs]
        self.assertIn("1/d1/status", topics)
        self.assertIn("system", topics)
        self.assertNotIn("2/d2/status", topics)

if __name__ == '__main__':
    unittest.main()
