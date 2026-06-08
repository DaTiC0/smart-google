import unittest
from unittest.mock import MagicMock, patch
import firebase_utils


class TestFirebaseUtils(unittest.TestCase):

    def test_reference_root_success(self):
        # Mock db as it might not be imported if firebase_admin is missing
        mock_db = MagicMock()
        with patch('firebase_utils.FIREBASE_AVAILABLE', True), \
             patch('firebase_utils.db', mock_db, create=True):
            ref = firebase_utils.reference()
            mock_db.reference.assert_called_with('/devices')
            self.assertNotIsInstance(ref, firebase_utils.MockRef)

    def test_reference_user_success(self):
        mock_db = MagicMock()
        with patch('firebase_utils.FIREBASE_AVAILABLE', True), \
             patch('firebase_utils.db', mock_db, create=True):
            ref = firebase_utils.reference(user_id="user123")
            mock_db.reference.assert_called_with('/users/user123/devices')
            self.assertNotIsInstance(ref, firebase_utils.MockRef)

    def test_reference_exception_path(self):
        # Ensure FIREBASE_AVAILABLE is True for this test
        mock_db = MagicMock()
        mock_db.reference.side_effect = Exception("Firebase initialization error")
        with patch('firebase_utils.FIREBASE_AVAILABLE', True), \
             patch('firebase_utils.db', mock_db, create=True), \
             patch('firebase_utils.logger.warning') as mock_warning:
            ref = firebase_utils.reference()

            # Verify it returns a MockRef instance
            self.assertIsInstance(ref, firebase_utils.MockRef)

            # Verify the warning was logged
            mock_warning.assert_called()
            self.assertIn("Firebase not initialized", mock_warning.call_args[0][0])

    def test_reference_firebase_not_available(self):
        with patch('firebase_utils.FIREBASE_AVAILABLE', False):
            ref = firebase_utils.reference()
            self.assertIsInstance(ref, firebase_utils.MockRef)

    def test_normalize_user_scope(self):
        self.assertEqual(firebase_utils._normalize_user_scope("user123"), "user123")
        self.assertEqual(firebase_utils._normalize_user_scope(123), "123")
        self.assertEqual(firebase_utils._normalize_user_scope("  user123  "), "user123")
        self.assertIsNone(firebase_utils._normalize_user_scope(None))
        self.assertIsNone(firebase_utils._normalize_user_scope(""))
        self.assertIsNone(firebase_utils._normalize_user_scope("   "))
        self.assertIsNone(firebase_utils._normalize_user_scope("user/123"))
        self.assertIsNone(firebase_utils._normalize_user_scope("user\\123"))
        self.assertIsNone(firebase_utils._normalize_user_scope("user..123"))

    def test_get_user_device_states_ref_valid(self):
        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_db.reference.return_value = mock_ref
        mock_device_ref = MagicMock()
        mock_ref.child.return_value = mock_device_ref
        mock_states_ref = MagicMock()
        mock_device_ref.child.return_value = mock_states_ref

        with patch('firebase_utils.FIREBASE_AVAILABLE', True), \
             patch('firebase_utils.db', mock_db, create=True):

            ref = firebase_utils._get_user_device_states_ref("user123", "device1")

            mock_db.reference.assert_called_with('/users/user123/devices')
            mock_ref.child.assert_called_with('device1')
            mock_device_ref.child.assert_called_with('states')
            self.assertEqual(ref, mock_states_ref)

    def test_get_user_device_states_ref_invalid(self):
        self.assertIsNone(firebase_utils._get_user_device_states_ref(None, "device1"))
        self.assertIsNone(firebase_utils._get_user_device_states_ref("user/123", "device1"))
        self.assertIsNone(firebase_utils._get_user_device_states_ref("user1", None))
        self.assertIsNone(firebase_utils._get_user_device_states_ref("user1", "device/1"))

    def test_mock_ref_and_child(self):
        ref = firebase_utils.MockRef()
        data = ref.get()
        self.assertEqual(data, firebase_utils.MOCK_DEVICES)

        child = ref.child("test-light-1")
        self.assertIsInstance(child, firebase_utils.MockChild)
        self.assertEqual(child.get(), firebase_utils.MOCK_DEVICES["test-light-1"])

        grandchild = child.child("name")
        self.assertEqual(grandchild.get(), firebase_utils.MOCK_DEVICES["test-light-1"]["name"])

        # Test non-existent path
        self.assertIsNone(ref.child("non-existent").get())

        # Test update
        # Careful as MOCK_DEVICES is shared.
        original_states = firebase_utils.MOCK_DEVICES["test-light-1"]["states"].copy()
        try:
            update_data = {"on": not original_states["on"]}
            child.child("states").update(update_data)
            self.assertEqual(firebase_utils.MOCK_DEVICES["test-light-1"]["states"]["on"], not original_states["on"])
        finally:
            firebase_utils.MOCK_DEVICES["test-light-1"]["states"] = original_states


if __name__ == '__main__':
    unittest.main()
