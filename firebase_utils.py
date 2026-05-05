# coding: utf-8
# Firebase reference helpers shared between action_devices and notifications.
# Extracted to a dedicated module to break the action_devices ↔ notifications
# cyclic import.

import logging

logger = logging.getLogger(__name__)

try:
    from firebase_admin import db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase admin not available, using mock data for testing")

# Mock data for testing when Firebase is not available
MOCK_DEVICES = {
    "test-light-1": {
        "type": "action.devices.types.LIGHT",
        "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
        "name": {"name": "Test Light"},
        "willReportState": True,
        "attributes": {"colorModel": "rgb"},
        "states": {"on": True, "brightness": 80, "online": True}
    },
    "test-switch-1": {
        "type": "action.devices.types.SWITCH",
        "traits": ["action.devices.traits.OnOff"],
        "name": {"name": "Test Switch"},
        "willReportState": True,
        "states": {"on": False, "online": True}
    }
}


class MockRef:
    @staticmethod
    def get():
        return MOCK_DEVICES

    @staticmethod
    def child(path):
        return MockChild(MOCK_DEVICES, path)


class MockChild:
    def __init__(self, data, path):
        self.data = data
        self.path = path

    def child(self, child_path):
        return MockChild(self.data, self.path + '/' + child_path)

    def get(self):
        keys = self.path.split('/')
        current = self.data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def update(self, values):
        keys = self.path.split('/')
        current = self.data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        if keys[-1] not in current:
            current[keys[-1]] = {}
        current[keys[-1]].update(values)
        return current[keys[-1]]


def _normalize_user_scope(user_id):
    """Normalize user scope value used in Firebase path building."""
    if user_id is None:
        return None
    user_value = str(user_id).strip()
    if not user_value or '/' in user_value or '\\' in user_value or '..' in user_value:
        return None
    return user_value


def reference(user_id=None):
    """Return a Firebase database reference scoped to the given user, or the root devices ref."""
    if FIREBASE_AVAILABLE:
        try:
            user_scope = _normalize_user_scope(user_id)
            if user_scope:
                return db.reference(f'/users/{user_scope}/devices')
            return db.reference('/devices')
        except Exception as e:
            # Firebase is installed but not initialized (e.g. missing credentials in dev)
            logger.warning("Firebase not initialized, falling back to mock data: %s", e)
    return MockRef()


def _get_user_device_states_ref(user_id, device_id):
    """Centralized helper for building user-scoped device state Firebase references."""
    user_scope = _normalize_user_scope(user_id)
    if not user_scope or not device_id or '/' in str(device_id):
        return None
    return reference(user_scope).child(str(device_id)).child('states')
