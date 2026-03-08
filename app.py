# coding: utf-8
# Code By DaTi_Co
import logging
import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, send_from_directory, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing Firebase, but don't fail if not available
try:
    from firebase_admin import credentials, initialize_app
    FIREBASE_AVAILABLE = True
except ImportError:
    logger.warning("Firebase admin not available, continuing without it")
    FIREBASE_AVAILABLE = False

# Try importing other modules, but provide fallbacks
try:
    from flask_login import LoginManager
    from models import User, db
    from my_oauth import init_oauth
    from notifications import mqtt
    from routes import bp
    from auth import auth
    FULL_FEATURES = True
except ImportError as e:
    logger.warning("Some modules not available: %s", e)
    FULL_FEATURES = False

# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}


def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app(config_class=None):
    """Application factory."""
    application = Flask(__name__, template_folder='templates')
    application.config['UPLOAD_FOLDER'] = './static/upload'

    # Load configuration
    env = os.environ.get('FLASK_ENV', os.environ.get('ENV', 'development'))
    if config_class is not None:
        application.config.from_object(config_class)
    elif env == 'production':
        try:
            application.config.from_object('config.ProductionConfig')
        except Exception as e:
            logger.warning("Could not load ProductionConfig: %s", e)
    else:
        try:
            application.config.from_object('config.DevelopmentConfig')
        except Exception as e:
            logger.warning("Could not load DevelopmentConfig: %s", e)

    # Apply fallback defaults so the app starts cleanly in dev/test
    if not application.config.get('AGENT_USER_ID'):
        application.config['AGENT_USER_ID'] = 'test-user'
    if not application.config.get('API_KEY'):
        application.config['API_KEY'] = 'test-api-key'
    if not application.config.get('DATABASEURL'):
        application.config['DATABASEURL'] = 'https://test-project-default-rtdb.firebaseio.com/'
    if not application.config.get('SECRET_KEY'):
        application.config['SECRET_KEY'] = secrets.token_urlsafe(16)
        logger.warning("SECRET_KEY not set in environment. Using a generated key (not suitable for production).")

    logger.info('ENV is set to: %s', env)
    logger.info('AGENT_USER_ID: %s', application.config.get('AGENT_USER_ID'))

    # Register extensions and blueprints when all features are available;
    # fall back to minimal routes if extension initialisation fails.
    if FULL_FEATURES:
        if not _init_full_features(application):
            _register_fallback_routes(application)
    else:
        _register_fallback_routes(application)

    # Initialize Firebase when full features are active
    if FIREBASE_AVAILABLE and FULL_FEATURES:
        try:
            svc = application.config.get('SERVICE_ACCOUNT_DATA')
            if svc:
                firebase_creds = credentials.Certificate(svc)
                firebase_opts = {'databaseURL': application.config['DATABASEURL']}
                initialize_app(firebase_creds, firebase_opts)
                logger.info("Firebase initialized successfully")
        except Exception as e:
            logger.warning("Could not initialize Firebase: %s", e)

    return application


def _init_full_features(application):
    """Initialize extensions and blueprints for the full-featured app.

    Returns True when all extensions and blueprints were successfully
    registered, False otherwise.
    """
    try:
        mqtt.init_app(application)
        mqtt.subscribe('+/notification')
        mqtt.subscribe('+/status')
        db.init_app(application)
        init_oauth(application)

        login_manager = LoginManager()
        login_manager.login_view = 'auth.login'
        login_manager.init_app(application)

        @login_manager.user_loader
        def load_user(user_id):
            """Get User by ID."""
            return db.session.get(User, int(user_id))

        # Create database tables within the application context
        with application.app_context():
            try:
                db_uri = application.config.get('SQLALCHEMY_DATABASE_URI', '')
                logger.info('DB Engine: %s', db_uri.split(':')[0] if db_uri else 'sqlite')
                db.create_all()
                logger.info('Initialized the database.')
            except Exception as e:
                logger.warning("Could not create database tables: %s", e)

        application.register_blueprint(bp, url_prefix='')
        application.register_blueprint(auth, url_prefix='')
        return True
    except Exception as e:
        logger.warning("Could not initialize full features: %s", e)
        return False


def _register_fallback_routes(application):
    """Register minimal routes when full features are unavailable."""
    @application.route('/')
    def index():
        return {'status': 'Smart-Google is working!', 'agent_user_id': application.config['AGENT_USER_ID']}

    @application.route('/health')
    def health():
        return jsonify({
            'status': 'degraded',
            'service': 'smart-google',
            'mqtt_connected': False,
        }), 503

    try:
        from action_devices import onSync, actions, request_sync, report_state

        @application.route('/devices')
        def devices():
            try:
                return onSync()
            except Exception as e:
                return {'error': str(e)}, 500

        @application.route('/smarthome', methods=['POST'])
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

        @application.route('/sync')
        def sync():
            try:
                success = request_sync(application.config['API_KEY'], application.config['AGENT_USER_ID'])
                state_result = report_state()
                return {'sync_requested': True, 'success': success, 'state_report': state_result}
            except Exception as e:
                return {'error': str(e)}, 500

    except ImportError as e:
        logger.warning("Could not import action_devices: %s", e)


# ---------------------------------------------------------------------------
# Module-level application instance (used by Gunicorn and the test suite)
# ---------------------------------------------------------------------------
app = create_app()


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve files from the upload folder."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    logger.info("Starting Smart-Google Flask Application")
    logger.info("Full features: %s", FULL_FEATURES)
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=False)
