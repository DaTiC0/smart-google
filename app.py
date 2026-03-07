# coding: utf-8
# Code By DaTi_Co
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not available, continuing without loading .env file")

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
app.config['AGENT_USER_ID'] = os.environ.get('AGENT_USER_ID', 'test-user')
app.config['API_KEY'] = os.environ.get('API_KEY', 'test-api-key')
app.config['DATABASEURL'] = os.environ.get('DATABASEURL', 'https://test-project-default-rtdb.firebaseio.com/')
app.config['UPLOAD_FOLDER'] = './static/upload'

if app.config.get("ENV") == "production":
    try:
        app.config.from_object("config.ProductionConfig")
    except Exception as e:
        print(f"Could not load ProductionConfig: {e}")
else:
    try:
        app.config.from_object("config.DevelopmentConfig")
    except Exception as e:
        print(f"Could not load DevelopmentConfig: {e}")

# Ensure SECRET_KEY is set; generate a random one if missing (not suitable for production)
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
    print("WARNING: SECRET_KEY not set in environment. Using a generated key (not suitable for production).")

print(f'ENV is set to: {app.config.get("ENV", "development")}')
print(f'Agent USER.ID: {app.config.get("AGENT_USER_ID")}')

# Register blueprints if available — initialize extensions first, then blueprints.
# This order ensures that a failure in extension setup does not leave blueprints
# partially registered while FULL_FEATURES is flipped to False.
if FULL_FEATURES:
    try:
        # Initialize all extensions before touching the blueprint registry
        mqtt.init_app(app)
        mqtt.subscribe('+/notification')
        mqtt.subscribe('+/status')
        db.init_app(app)
        oauth.init_app(app)
        login_manager = LoginManager()
        login_manager.login_view = 'auth.login'
        login_manager.init_app(app)

        @login_manager.user_loader
        def load_user(user_id):
            """Get User ID"""
            print(user_id)
            return User.query.get(int(user_id))

        # Register blueprints only after all extensions succeed
        app.register_blueprint(bp, url_prefix='')
        app.register_blueprint(auth, url_prefix='')
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


# Fallback routes — only registered when full blueprint features are unavailable,
# to avoid duplicate URL rule conflicts with the blueprint routes.
if not FULL_FEATURES:
    @app.route('/')
    def index():
        return {'status': 'Smart-Google is working!', 'agent_user_id': app.config['AGENT_USER_ID']}

    @app.route('/health')
    def health():
        return {'status': 'healthy', 'features': 'basic'}

    try:
        from action_devices import onSync, actions, request_sync, report_state
        from flask import request, jsonify

        @app.route('/devices')
        def devices():
            try:
                return onSync()
            except Exception as e:
                return {'error': str(e)}, 500

        @app.route('/smarthome', methods=['POST'])
        def smarthome():
            try:
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
    print(f"Full features: {FULL_FEATURES}")

    if FULL_FEATURES:
        try:
            db.create_all(app=app)
        except Exception:
            pass

    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=False)

