import unittest
from unittest.mock import patch, MagicMock
from flask import Flask

# Set environment variables for testing
import os
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['APP_ENV'] = 'testing'

from action_devices import onSync, actions
from notifications import handle_messages, get_mqtt_logs, _append_mqtt_log

class MultiTenantTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('action_devices.reference')
    @patch('firebase_utils.FIREBASE_AVAILABLE', True)
    def test_on_sync_scoped_path(self, mock_reference):
        # Mock Firebase response for user 123
        mock_ref = MagicMock()
        mock_reference.return_value = mock_ref
        mock_ref.get.return_value = {
            "device1": {"name": {"name": "Light 1"}, "type": "light"}
        }

        # Call onSync for user 123
        response = onSync(user_id="123")

        # Verify correct Firebase path was hit
        mock_reference.assert_called_with('123')
        self.assertEqual(response['agentUserId'], "123")
        self.assertEqual(len(response['devices']), 1)
        self.assertEqual(response['devices'][0]['id'], "device1")

    @patch('action_devices.mqtt')
    @patch('action_devices.reference')
    @patch('firebase_utils.FIREBASE_AVAILABLE', True)
    def test_on_execute_mqtt_topic(self, mock_reference, mock_mqtt):
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
        mock_reference.return_value = mock_ref

        # Call actions
        actions(req, user_id="456")

        # Verify MQTT topic is scoped to user 456
        expected_topic = "456/fan1/notification"
        mock_mqtt.publish.assert_called()
        call_args = mock_mqtt.publish.call_args
        self.assertEqual(call_args.kwargs['topic'], expected_topic)

    @patch('notifications._get_user_device_states_ref')
    @patch('firebase_utils.FIREBASE_AVAILABLE', True)
    def test_mqtt_status_update_firebase_path(self, mock_reference):
        # Mock MQTT message: user 789 reports status for lamp1
        mock_message = MagicMock()
        mock_message.topic = "789/lamp1/status"
        mock_message.payload = b'{"on": false, "online": true}'

        # Mock reference chain
        mock_user_ref = MagicMock()
        mock_device_ref = MagicMock()
        mock_states_ref = MagicMock()
        




        # Call handle_messages
        handle_messages(None, None, mock_message)

        # Verify Firebase update path is scoped correctly
        mock_reference.assert_called_with('789', 'lamp1')


        mock_reference.return_value.update.assert_called_with({"on": False, "online": True})

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

    @patch('firebase_utils.FIREBASE_AVAILABLE', False)
    def test_on_sync_without_fallback_no_user(self):
        """Verify onSync returns 'unknown' when no user is resolved."""
        response = onSync(user_id=None, agent_user_id=None)
        self.assertEqual(response['agentUserId'], "unknown")
        self.assertEqual(response['devices'], [])

    def test_smarthome_resolution_without_fallback_no_user(self):
        """Verify _resolve_smarthome_user_scope returns (None, None) when no user is found."""
        from routes import _resolve_smarthome_user_scope
        req = {"requestId": "req1", "inputs": []}
        user_scope, agent_user_id = _resolve_smarthome_user_scope(req)
        self.assertIsNone(user_scope)
        self.assertIsNone(agent_user_id)

if __name__ == '__main__':
    unittest.main()
