import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.curdir))

class TestOAuthOptimization(unittest.TestCase):
    def test_save_token_uses_bulk_delete(self):
        """
        Verify that save_token uses a bulk delete instead of a loop.
        """
        # Always use a fully mocked approach to avoid issues with missing dependencies
        # or partial environments in both CI and local.

        mock_db = MagicMock()
        mock_models = MagicMock()
        mock_models.db = mock_db
        mock_token_cls = MagicMock()
        mock_models.Token = mock_token_cls

        mock_sqlalchemy = MagicMock()
        mock_delete_query = MagicMock()
        mock_sqlalchemy.delete.return_value = mock_delete_query
        mock_delete_query.filter_by.return_value = mock_delete_query

        # Mock all possible dependencies to prevent ImportErrors during the test
        mock_modules = {
            'flask': MagicMock(),
            'flask.debughelpers': MagicMock(),
            'flask_login': MagicMock(),
            'authlib.integrations.flask_oauth2': MagicMock(),
            'authlib.oauth2.rfc6749': MagicMock(),
            'authlib.oauth2.rfc6750': MagicMock(),
            'sqlalchemy': mock_sqlalchemy,
            'models': mock_models
        }

        # Using patch.dict on sys.modules is safe and isolates the test
        with patch.dict(sys.modules, mock_modules):
            # Ensure my_oauth is reloaded within this mocked context
            if 'my_oauth' in sys.modules:
                del sys.modules['my_oauth']
            import my_oauth

            mock_request = MagicMock()
            mock_request.client.client_id = 'test_client'
            mock_request.user.id = 123

            token_data = {
                'access_token': 'new_token',
                'expires_in': 3600,
                'token_type': 'Bearer',
                'scope': 'profile'
            }

            # Call the function
            my_oauth.save_token(token_data, mock_request)

            # Verify bulk delete was called
            mock_db.session.execute.assert_any_call(mock_delete_query)
            mock_sqlalchemy.delete.assert_called_once_with(mock_token_cls)

            # Verify the old iterative delete is NOT called
            self.assertFalse(mock_db.session.delete.called)

if __name__ == '__main__':
    unittest.main()
