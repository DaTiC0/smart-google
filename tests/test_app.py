# pyright: reportAttributeAccessIssue=false
import unittest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Ensure tests never touch runtime DB (db.sqlite)
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['APP_ENV'] = 'development'

from app import app as flask_app  # noqa: E402
from app import allowed_file  # noqa: E402
from models import db, User  # noqa: E402
from sqlalchemy import select  # used in cleanup queries


class ApplicationRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        flask_app.config.update(TESTING=True)

    def setUp(self):
        self.client = flask_app.test_client()

    def test_root_endpoint_content_contract(self):
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


class AuthTests(unittest.TestCase):
    def setUp(self):
        flask_app.config.update(TESTING=True)
        with flask_app.app_context():
            db.create_all()
        self.client = flask_app.test_client()

    def tearDown(self):
        # remove any test user that was created
        with flask_app.app_context():
            result = db.session.execute(select(User).filter_by(email='a@b.com')).scalar_one_or_none()
            if result:
                db.session.delete(result)
                db.session.commit()

    def test_signup_and_login(self):
        resp = self.client.post('/signup', data={'email': 'a@b.com', 'name': 'A', 'password': 'pass'})
        self.assertIn(resp.status_code, (302, 200))
        resp2 = self.client.post('/login', data={'email': 'a@b.com', 'password': 'pass'}, follow_redirects=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertIn('Profile', resp2.get_data(as_text=True))

    def test_password_hash_fits_schema_length(self):
        self.client.post('/signup', data={'email': 'a@b.com', 'name': 'A', 'password': 'pass'})
        with flask_app.app_context():
            user = db.session.execute(select(User).filter_by(email='a@b.com')).scalar_one_or_none()
            self.assertIsNotNone(user)
            self.assertLessEqual(len(user.password), 255)


class OAuthEndpointTests(unittest.TestCase):
    def setUp(self):
        flask_app.config.update(TESTING=True)
        self.client = flask_app.test_client()

    def test_oauth_routes_smoke(self):
        authorize_resp = self.client.get('/oauth/authorize', follow_redirects=False)
        self.assertEqual(authorize_resp.status_code, 302)

        token_resp = self.client.post('/oauth/token', data={'grant_type': 'client_credentials'})
        self.assertIn(token_resp.status_code, (400, 401))

        me_resp = self.client.get('/api/me')
        self.assertEqual(me_resp.status_code, 401)


class DeviceEndpointTests(unittest.TestCase):
    def setUp(self):
        flask_app.config.update(TESTING=True)
        self.client = flask_app.test_client()

    def test_devices_requires_login(self):
        resp = self.client.get('/devices')
        self.assertEqual(resp.status_code, 302)

    def test_smarthome_sync(self):
        payload = {'requestId': '1', 'inputs': [{'intent': 'action.devices.SYNC', 'payload': {}}]}
        resp = self.client.post('/smarthome', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('payload', data)


class ActionDevicesUnitTests(unittest.TestCase):
    def setUp(self):
        flask_app.config.update(TESTING=True)

    def test_onSync_and_helpers(self):
        with flask_app.app_context():
            from action_devices import onSync, onQuery, onExecute, request_sync
            sync = onSync()
            self.assertIn('agentUserId', sync)
            q = onQuery({'inputs': [{'payload': {'devices': [{'id': 'nonexistent'}]}}]})
            self.assertIn('devices', q)
            exec_resp = onExecute({'inputs': [{'payload': {'devices': [{'id': 'nonexistent'}]},
                                               'commands': [{'execution': [{'command': 'action.devices.commands.OnOff',
                                                                            'params': {'on': True}}]}]}]})
            self.assertIn('commands', exec_resp)
            self.assertEqual(exec_resp['commands'][0]['status'], 'ERROR')
            self.assertFalse(request_sync('', ''))
