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

        body = response.get_data(as_text=True)
        self.assertIsInstance(body, str)
        self.assertNotEqual(body.strip(), "")

    def test_health_endpoint_contract(self):
        response = self.client.get('/health')
        self.assertIn(response.status_code, (200, 503))

        self.assertTrue(
            response.content_type.startswith("application/json"),
            msg=f"Unexpected content type: {response.content_type}",
        )

        payload = response.get_json()
        self.assertIsInstance(payload, dict)

        self.assertIn("service", payload)
        self.assertIsInstance(payload["service"], str)
        self.assertTrue(payload["service"])
        self.assertEqual(payload["service"], "smart-google")

        self.assertIn("mqtt_connected", payload)
        self.assertIsInstance(payload["mqtt_connected"], bool)

        self.assertIn("status", payload)
        self.assertIsInstance(payload["status"], str)
        self.assertIn(payload["status"], ("ok", "degraded"))

        if response.status_code == 200:
            self.assertEqual(payload["status"], "ok")
        else:
            self.assertEqual(payload["status"], "degraded")


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
