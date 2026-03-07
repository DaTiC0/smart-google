import unittest

from app import app as flask_app
from app import allowed_file


class ApplicationRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        flask_app.config.update(TESTING=True)

    def setUp(self):
        self.client = flask_app.test_client()

    def test_root_endpoint_returns_success(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint_contract(self):
        response = self.client.get('/health')
        self.assertIn(response.status_code, (200, 503))

        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get('service'), 'smart-google')
        self.assertIsInstance(payload.get('mqtt_connected'), bool)
        self.assertIn(payload.get('status'), ('ok', 'degraded', 'healthy'))

        if response.status_code == 200:
            self.assertIn(payload.get('status'), ('ok', 'healthy'))
        else:
            self.assertEqual(payload.get('status'), 'degraded')


class AllowedFileTest(unittest.TestCase):
    def test_allowed_file_extensions(self):
        self.assertTrue(allowed_file('script.py'))
        self.assertTrue(allowed_file('notes.txt'))
        self.assertFalse(allowed_file('image.png'))
        self.assertFalse(allowed_file('no_extension'))
