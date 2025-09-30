# Mock Firebase Admin for testing
class MockCredentials:
    def __init__(self, cert_path):
        self.cert_path = cert_path

class MockDB:
    @staticmethod
    def reference(path):
        from action_devices_fixed import MockFirebaseReference
        return MockFirebaseReference()

def credentials():
    return MockCredentials

def initialize_app(credentials, options):
    print(f"Mock Firebase initialized with options: {options}")
    return True

# Mock modules
credentials.Certificate = MockCredentials
db = MockDB()
