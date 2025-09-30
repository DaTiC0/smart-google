# coding: utf-8
# Code By DaTi_Co
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from flask import Flask, send_from_directory

# Try importing Firebase, but don't fail if not available
try:
    from firebase_admin import credentials, initialize_app
    FIREBASE_AVAILABLE = True
except ImportError:
    print("Firebase admin not available, continuing without it")
    FIREBASE_AVAILABLE = False

# Try importing other modules, but provide fallbacks
try:
    from flask_login import LoginManager
    from models import User, db
    from my_oauth import oauth
    from notifications import mqtt
    from routes import bp
    from auth import auth
    FULL_FEATURES = True
except ImportError as e:
    print(f"Some modules not available: {e}")
    FULL_FEATURES = False

# Flask Application Configuration
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = True
app.config['AGENT_USER_ID'] = os.environ.get('AGENT_USER_ID', 'test-user')
app.config['API_KEY'] = os.environ.get('API_KEY', 'test-api-key')
app.config['DATABASEURL'] = os.environ.get('DATABASEURL', 'https://test-project-default-rtdb.firebaseio.com/')
app.config['UPLOAD_FOLDER'] = './static/upload'

if app.config.get("ENV") == "production":
    try:
        app.config.from_object("config.ProductionConfig")
    except:
        print("Could not load ProductionConfig")
else:
    try:
        app.config.from_object("config.DevelopmentConfig")
    except:
        print("Could not load DevelopmentConfig")

print(f'ENV is set to: {app.config.get("ENV", "development")}')
print(f'Agent USER.ID: {app.config["AGENT_USER_ID"]}')

# Register blueprints if available
if FULL_FEATURES:
    try:
        app.register_blueprint(bp, url_prefix='')
        app.register_blueprint(auth, url_prefix='')
        # MQTT CONNECT
        mqtt.init_app(app)
        mqtt.subscribe('+/notification')
        mqtt.subscribe('+/status')
        # SQLAlchemy DATABASE
        db.init_app(app)
        # OAuth2 Authorisation
        oauth.init_app(app)
        # Flask Login
        login_manager = LoginManager()
        login_manager.login_view = 'auth.login'
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(user_id):
            """Get User ID"""
            print(user_id)
            return User.query.get(int(user_id))
            
    except Exception as e:
        print(f"Could not initialize full features: {e}")
        FULL_FEATURES = False

# Initialize Firebase if available
if FIREBASE_AVAILABLE and FULL_FEATURES:
    try:
        FIREBASE_ADMINSDK_FILE = app.config.get('SERVICE_ACCOUNT_DATA')
        if FIREBASE_ADMINSDK_FILE:
            FIREBASE_CREDENTIALS = credentials.Certificate(FIREBASE_ADMINSDK_FILE)
            FIREBASE_DATABASEURL = app.config['DATABASEURL']
            FIREBASE_OPTIONS = {'databaseURL': FIREBASE_DATABASEURL}
            initialize_app(FIREBASE_CREDENTIALS, FIREBASE_OPTIONS)
            print("Firebase initialized successfully")
    except Exception as e:
        print(f"Could not initialize Firebase: {e}")

# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}

def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Basic routes for testing
@app.route('/')
def index():
    return {'status': 'Smart-Google is working!', 'agent_user_id': app.config['AGENT_USER_ID']}

@app.route('/health')
def health():
    return {'status': 'healthy', 'features': 'full' if FULL_FEATURES else 'basic'}

# Import action_devices and add basic endpoints
try:
    from action_devices import onSync, actions, request_sync, report_state
    
    @app.route('/devices')
    def devices():
        try:
            return onSync()
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/smarthome', methods=['POST'])
    def smarthome():
        try:
            from flask import request, jsonify
            req_data = request.get_json()
            result = {
                'requestId': req_data.get('requestId', 'unknown'),
                'payload': actions(req_data),
            }
            return jsonify(result)
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/sync')
    def sync():
        try:
            success = request_sync(app.config['API_KEY'], app.config['AGENT_USER_ID'])
            state_result = report_state()
            return {'sync_requested': True, 'success': success, 'state_report': state_result}
        except Exception as e:
            return {'error': str(e)}, 500

except ImportError as e:
    print(f"Could not import action_devices: {e}")

if FULL_FEATURES:
    try:
        @app.before_first_request
        def create_db_command():
            """Search for tables and if there is no data create new tables."""
            print('DB Engine: ' + app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite').split(':')[0])
            db.create_all(app=app)
            print('Initialized the database.')
    except Exception as e:
        print(f"Could not set up database initialization: {e}")

if __name__ == '__main__':
    print("Starting Smart-Google Flask Application")
    print("Available endpoints: /, /health, /devices, /smarthome, /sync")
    
    os.environ['DEBUG'] = 'True'  # While in development
    if FULL_FEATURES:
        try:
            db.create_all(app=app)
        except:
            pass
    app.run(host='0.0.0.0', port=5000, debug=False)
