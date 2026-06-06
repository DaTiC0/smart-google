import unittest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime, timezone

# Mock dependencies before importing my_oauth
mock_db = MagicMock()
mock_models = MagicMock()
mock_models.db = mock_db
mock_models.Token = MagicMock()
mock_models.Client = MagicMock()
mock_models.Grant = MagicMock()
mock_models.User = MagicMock()

mock_flask = MagicMock()
mock_flask_login = MagicMock()
mock_authlib_flask = MagicMock()
mock_authlib_rfc6749 = MagicMock()
mock_authlib_rfc6750 = MagicMock()
mock_sqlalchemy = MagicMock()

sys.modules['flask'] = mock_flask
sys.modules['flask_login'] = mock_flask_login
sys.modules['authlib.integrations.flask_oauth2'] = mock_authlib_flask
sys.modules['authlib.oauth2.rfc6749'] = mock_authlib_rfc6749
sys.modules['authlib.oauth2.rfc6750'] = mock_authlib_rfc6750
sys.modules['sqlalchemy'] = mock_sqlalchemy
sys.modules['models'] = mock_models

# Now import save_token from my_oauth
import my_oauth

class TestOAuthOptimization(unittest.TestCase):
    def test_save_token_uses_bulk_delete(self):
        # Setup mock request and token data
        mock_request = MagicMock()
        mock_request.client.client_id = 'test_client'
        mock_request.user.id = 123

        token_data = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'token_type': 'Bearer',
            'scope': 'profile',
            'expires_in': 3600
        }

        # Setup mocks for SQLAlchemy functions
        mock_delete_obj = MagicMock()
        mock_sqlalchemy.delete.return_value = mock_delete_obj
        mock_delete_obj.filter_by.return_value = mock_delete_obj

        # Call save_token
        my_oauth.save_token(token_data, mock_request)

        # Verify bulk delete was called
        mock_sqlalchemy.delete.assert_called_once_with(mock_models.Token)
        mock_delete_obj.filter_by.assert_called_once_with(
            client_id='test_client',
            user_id=123
        )
        mock_db.session.execute.assert_any_call(mock_delete_obj)

        # Also verify db.session.delete was NOT called (to ensure loop is gone)
        self.assertFalse(mock_db.session.delete.called)

if __name__ == '__main__':
    unittest.main()
