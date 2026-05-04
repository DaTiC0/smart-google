# pyright: reportAttributeAccessIssue=false
import unittest
import sys
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Ensure tests never touch runtime DB (db.sqlite)
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['APP_ENV'] = 'development'

from app import app as flask_app  # noqa: E402
from app import allowed_file  # noqa: E402
from app import _is_production_environment, _password_column_migration_sql  # noqa: E402
from models import db, User, Client  # noqa: E402
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


class AppHardeningHelpersTest(unittest.TestCase):
    def test_is_production_environment_true_for_production_values(self):
        with patch.dict(os.environ, {'APP_ENV': 'production'}, clear=False):
            self.assertTrue(_is_production_environment())
        with patch.dict(os.environ, {'APP_ENV': 'prod'}, clear=False):
            self.assertTrue(_is_production_environment())

    def test_is_production_environment_false_for_development(self):
        with patch.dict(os.environ, {'APP_ENV': 'development'}, clear=False):
            self.assertFalse(_is_production_environment())

    def test_password_column_migration_sql_for_supported_dialects(self):
        self.assertEqual(
            _password_column_migration_sql('postgresql'),
            'ALTER TABLE "user" ALTER COLUMN password TYPE VARCHAR(255)',
        )
        self.assertEqual(
            _password_column_migration_sql('mysql'),
            'ALTER TABLE `user` MODIFY COLUMN password VARCHAR(255)',
        )
        self.assertEqual(
            _password_column_migration_sql('mariadb'),
            'ALTER TABLE `user` MODIFY COLUMN password VARCHAR(255)',
        )

    def test_password_column_migration_sql_for_unsupported_dialect(self):
        self.assertIsNone(_password_column_migration_sql('sqlite'))


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
        with flask_app.app_context():
            db.create_all()
        self.client = flask_app.test_client()

    @staticmethod
    def _create_oauth_user_and_client():
        with flask_app.app_context():
            user = User(
                username='oauth-user',
                email='oauth@example.com',
                name='OAuth User',
                password='test-password',
            )
            client = Client(
                client_id='oauth-client-id',
                client_secret='oauth-client-secret',
                user=user,
                _redirect_uris='http://localhost/callback',
                _default_scopes='profile',
            )
            db.session.add_all([user, client])
            db.session.commit()
            return user.id

    def _login_oauth_test_user_session(self, user_id):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)

    def tearDown(self):
        with flask_app.app_context():
            db.session.remove()
            db.drop_all()

    def test_authorize_redirects_without_session(self):
        authorize_resp = self.client.get('/oauth/authorize', follow_redirects=False)
        self.assertEqual(authorize_resp.status_code, 302)
        self.assertTrue(authorize_resp.location.endswith('/'))

    def test_authorize_invalid_request_returns_oauth_error_when_logged_in(self):
        user_id = self._create_oauth_user_and_client()
        self._login_oauth_test_user_session(user_id)

        authorize_resp = self.client.get('/oauth/authorize', follow_redirects=False)
        self.assertEqual(authorize_resp.status_code, 400)
        self.assertTrue(authorize_resp.content_type.startswith('application/json'))
        payload = authorize_resp.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get('error'), 'unsupported_response_type')

    def test_authorize_valid_request_renders_consent_for_logged_in_user(self):
        user_id = self._create_oauth_user_and_client()
        self._login_oauth_test_user_session(user_id)

        authorize_resp = self.client.get(
            '/oauth/authorize?response_type=code&client_id=oauth-client-id'
            '&redirect_uri=http://localhost/callback&scope=profile&state=abc',
            follow_redirects=False,
        )
        self.assertEqual(authorize_resp.status_code, 200)
        body = authorize_resp.get_data(as_text=True)
        self.assertIn('oauth-client-id', body)

    def test_authorization_code_exchange_allows_me_endpoint(self):
        user_id = self._create_oauth_user_and_client()
        self._login_oauth_test_user_session(user_id)

        authorize_path = (
            '/oauth/authorize?response_type=code&client_id=oauth-client-id'
            '&redirect_uri=http://localhost/callback&scope=profile&state=xyz'
        )

        authorize_get_resp = self.client.get(authorize_path, follow_redirects=False)
        self.assertEqual(authorize_get_resp.status_code, 200)

        authorize_post_resp = self.client.post(
            authorize_path,
            data={'confirm': 'yes'},
            follow_redirects=False,
        )
        self.assertEqual(authorize_post_resp.status_code, 302)

        redirect_location = authorize_post_resp.headers.get('Location')
        self.assertIsNotNone(redirect_location)

        query_params = parse_qs(urlparse(redirect_location).query)
        auth_code = query_params.get('code', [None])[0]
        state = query_params.get('state', [None])[0]
        self.assertIsNotNone(auth_code)
        self.assertEqual(state, 'xyz')

        token_resp = self.client.post(
            '/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': 'oauth-client-id',
                'client_secret': 'oauth-client-secret',
                'code': auth_code,
                'redirect_uri': 'http://localhost/callback',
            },
        )
        self.assertEqual(token_resp.status_code, 200)
        token_payload = token_resp.get_json()
        self.assertIsInstance(token_payload, dict)
        self.assertEqual(token_payload.get('token_type'), 'Bearer')
        access_token = token_payload.get('access_token')
        self.assertTrue(access_token)

        me_resp = self.client.get('/api/me', headers={'Authorization': f'Bearer {access_token}'})
        self.assertEqual(me_resp.status_code, 200)
        me_payload = me_resp.get_json()
        self.assertIsInstance(me_payload, dict)
        self.assertEqual(me_payload.get('username'), 'oauth-user')

    def test_authorize_deny_consent_redirects_with_access_denied(self):
        user_id = self._create_oauth_user_and_client()
        self._login_oauth_test_user_session(user_id)

        authorize_path = (
            '/oauth/authorize?response_type=code&client_id=oauth-client-id'
            '&redirect_uri=http://localhost/callback&scope=profile&state=deny-state'
        )

        authorize_get_resp = self.client.get(authorize_path, follow_redirects=False)
        self.assertEqual(authorize_get_resp.status_code, 200)

        authorize_post_resp = self.client.post(
            authorize_path,
            data={'confirm': 'no'},
            follow_redirects=False,
        )
        self.assertEqual(authorize_post_resp.status_code, 302)

        redirect_location = authorize_post_resp.headers.get('Location')
        self.assertIsNotNone(redirect_location)
        query_params = parse_qs(urlparse(redirect_location).query)
        self.assertEqual(query_params.get('error', [None])[0], 'access_denied')
        self.assertEqual(query_params.get('state', [None])[0], 'deny-state')

    def test_token_rejects_invalid_authorization_code(self):
        self._create_oauth_user_and_client()

        token_resp = self.client.post(
            '/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': 'oauth-client-id',
                'client_secret': 'oauth-client-secret',
                'code': 'invalid-code',
                'redirect_uri': 'http://localhost/callback',
            },
        )
        self.assertEqual(token_resp.status_code, 400)
        self.assertTrue(token_resp.content_type.startswith('application/json'))
        token_payload = token_resp.get_json()
        self.assertIsInstance(token_payload, dict)
        self.assertEqual(token_payload.get('error'), 'invalid_grant')

    def test_token_rejects_authorization_code_with_mismatched_redirect_uri(self):
        user_id = self._create_oauth_user_and_client()
        self._login_oauth_test_user_session(user_id)

        authorize_path = (
            '/oauth/authorize?response_type=code&client_id=oauth-client-id'
            '&redirect_uri=http://localhost/callback&scope=profile&state=mismatch-state'
        )

        authorize_get_resp = self.client.get(authorize_path, follow_redirects=False)
        self.assertEqual(authorize_get_resp.status_code, 200)

        authorize_post_resp = self.client.post(
            authorize_path,
            data={'confirm': 'yes'},
            follow_redirects=False,
        )
        self.assertEqual(authorize_post_resp.status_code, 302)

        redirect_location = authorize_post_resp.headers.get('Location')
        self.assertIsNotNone(redirect_location)
        query_params = parse_qs(urlparse(redirect_location).query)
        auth_code = query_params.get('code', [None])[0]
        self.assertIsNotNone(auth_code)

        token_resp = self.client.post(
            '/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': 'oauth-client-id',
                'client_secret': 'oauth-client-secret',
                'code': auth_code,
                'redirect_uri': 'http://localhost/wrong-callback',
            },
        )
        self.assertEqual(token_resp.status_code, 400)
        self.assertTrue(token_resp.content_type.startswith('application/json'))
        token_payload = token_resp.get_json()
        self.assertIsInstance(token_payload, dict)
        self.assertEqual(token_payload.get('error'), 'invalid_grant')

    def test_token_returns_error_json_for_unsupported_grant(self):
        token_resp = self.client.post('/oauth/token', data={'grant_type': 'client_credentials'})
        self.assertEqual(token_resp.status_code, 400)
        self.assertTrue(token_resp.content_type.startswith('application/json'))
        payload = token_resp.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get('error'), 'unsupported_grant_type')

    def test_me_requires_authorization_header(self):
        me_resp = self.client.get('/api/me')
        self.assertEqual(me_resp.status_code, 401)
        self.assertTrue(me_resp.content_type.startswith('application/json'))
        payload = me_resp.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get('error'), 'missing_authorization')

    def test_me_rejects_invalid_bearer_token(self):
        me_resp = self.client.get(
            '/api/me',
            headers={'Authorization': 'Bearer not-a-valid-token'},
        )
        self.assertEqual(me_resp.status_code, 401)
        self.assertTrue(me_resp.content_type.startswith('application/json'))
        payload = me_resp.get_json()
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get('error'), 'invalid_token')


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
