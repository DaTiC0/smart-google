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
        self.assertIn(payload.get('status'), ('ok', 'degraded'))

        if response.status_code == 200:
            self.assertEqual(payload.get('status'), 'ok')
        else:
            self.assertEqual(payload.get('status'), 'degraded')


class AllowedFileTest(unittest.TestCase):
    def test_allowed_file_extensions(self):
        self.assertTrue(allowed_file('script.py'))
        self.assertTrue(allowed_file('notes.txt'))
        self.assertFalse(allowed_file('image.png'))
        self.assertFalse(allowed_file('no_extension'))

    def test_allowed_file_multiple_dots(self):
        # Should be allowed or disallowed based on the final extension
        self.assertTrue(allowed_file('archive.tar.py'))
        self.assertFalse(allowed_file('archive.tar.gz'))

    def test_allowed_file_uppercase_extension(self):
        # Uppercase extensions corresponding to allowed types should be accepted
        self.assertTrue(allowed_file('SCRIPT.PY'))
        self.assertTrue(allowed_file('NOTES.TXT'))
        self.assertFalse(allowed_file('IMAGE.PNG'))

    def test_allowed_file_empty_and_edge_names(self):
        self.assertFalse(allowed_file(''))
        self.assertFalse(allowed_file('.'))
        self.assertFalse(allowed_file('.hidden'))
