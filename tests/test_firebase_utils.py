import unittest
from unittest.mock import patch, MagicMock

class TestFirebaseUtils(unittest.TestCase):
    def test_reference_value_error_fallback(self):
        # We must clear the module to reload it with our mocked FIREBASE_AVAILABLE state
        import sys
        if 'firebase_utils' in sys.modules:
            del sys.modules['firebase_utils']

        # Mock firebase_admin and db to simulate an uninitialized state where db.reference raises ValueError
        mock_db = MagicMock()
        mock_db.reference.side_effect = ValueError("The default Firebase app does not exist.")

        with patch.dict(sys.modules, {'firebase_admin': MagicMock(db=mock_db)}):
            import firebase_utils

            # FIREBASE_AVAILABLE should be True because the import succeeds (mocked)
            self.assertTrue(firebase_utils.FIREBASE_AVAILABLE)

            with patch('firebase_utils.logger.warning') as mock_logger:
                ref = firebase_utils.reference()

                # Should fallback to MockRef
                self.assertIsInstance(ref, firebase_utils.MockRef)
                mock_logger.assert_called_once()
                self.assertIn("Firebase not initialized", mock_logger.call_args[0][0])

    def test_reference_other_exception_bubbles_up(self):
        import sys
        if 'firebase_utils' in sys.modules:
            del sys.modules['firebase_utils']

        mock_db = MagicMock()
        # Some other error like network permission denied
        mock_db.reference.side_effect = PermissionError("Permission denied.")

        with patch.dict(sys.modules, {'firebase_admin': MagicMock(db=mock_db)}):
            import firebase_utils

            with self.assertRaises(PermissionError):
                firebase_utils.reference()

if __name__ == '__main__':
    unittest.main()
