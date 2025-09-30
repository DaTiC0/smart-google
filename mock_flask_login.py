# Mock Flask-Login for testing
class MockLoginManager:
    def __init__(self):
        self.login_view = None
    
    def init_app(self, app):
        pass
    
    def user_loader(self, func):
        return func

class MockUserMixin:
    pass

def login_required(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

def login_user(user, remember=False):
    return True

def logout_user():
    return True

def current_user():
    return None

# Export
LoginManager = MockLoginManager
UserMixin = MockUserMixin
