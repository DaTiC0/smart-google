# Mock Flask-SQLAlchemy for testing
class MockColumn:
    def __init__(self, type_, **kwargs):
        self.type = type_
        self.kwargs = kwargs

class MockModel:
    query = None

class MockDB:
    Model = MockModel
    Column = MockColumn
    Integer = int
    String = str
    Text = str
    Boolean = bool
    DateTime = str
    ForeignKey = str
    
    def __init__(self):
        self.session = MockSession()
    
    def init_app(self, app):
        pass
    
    def create_all(self, app=None):
        print("Mock database tables created")
    
    def relationship(self, *args, **kwargs):
        return None

class MockSession:
    def add(self, obj):
        print(f"Mock: Added {obj} to session")
    
    def commit(self):
        print("Mock: Session committed")
    
    def delete(self, obj):
        print(f"Mock: Deleted {obj} from session")

# Export
SQLAlchemy = MockDB
