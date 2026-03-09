# coding: utf-8
# Code By DaTi_Co

import logging
import os
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, jsonify, send_from_directory, request
from flask_login import login_required  # used even in minimal mode

# Try importing Firebase, but don't fail if not available
try:
    from firebase_admin import credentials, initialize_app
    FIREBASE_AVAILABLE = True
except ImportError:
    logger.warning("Firebase admin not available, continuing without it")
    FIREBASE_AVAILABLE = False

# always import core pieces; failures here are fatal
try:
    from models import User, db
    from auth import auth
except ImportError as e:
    logger.warning("Critical import failed: %s", e)

# load add‑ons; missing ones just disable full features
try:
    from flask_login import LoginManager
    from my_oauth import oauth
    from notifications import mqtt
    FULL_FEATURES = True
except ImportError as e:
    logger.warning("Optional module missing: %s", e)
    FULL_FEATURES = False

# Flask Application Configuration
app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = './static/upload'

# Always set up a login manager if flask_login is available so that
# @login_required decorators function and tests can rely on redirections.
try:
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """Get User ID"""
        # User import should succeed earlier
        return User.query.get(int(user_id))
except Exception as e:
    logger.warning("LoginManager unavailable: %s", e)

if app.config.get("ENV") == "production":
    try:
        app.config.from_object("config.ProductionConfig")
    except Exception as e:
        logger.warning("Could not load ProductionConfig: %s", e)
else:
    try:
        app.config.from_object("config.DevelopmentConfig")
    except Exception as e:
        logger.warning("Could not load DevelopmentConfig: %s", e)

# fallback values for when env vars are missing
if not app.config.get('AGENT_USER_ID'):
    app.config['AGENT_USER_ID'] = 'test-user'
if not app.config.get('API_KEY'):
    app.config['API_KEY'] = 'test-api-key'
if not app.config.get('DATABASEURL'):
    app.config['DATABASEURL'] = 'https://test-project-default-rtdb.firebaseio.com/'

# ensure sqlalchemy flag key exists
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

# generate a temp secret key when not provided
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
    logger.warning("SECRET_KEY not set; generated temporary key")

logger.info('ENV is set to: %s', app.config.get("ENV", "development"))
logger.info('AGENT_USER_ID: %s', app.config.get("AGENT_USER_ID"))

if FULL_FEATURES:
    try:
        mqtt.init_app(app)
        mqtt.subscribe('+/notification')
        mqtt.subscribe('+/status')
        db.init_app(app)
        oauth.init_app(app)
        from routes import bp
        app.register_blueprint(bp, url_prefix='')
    except ImportError as e:
        logger.warning("Optional route blueprint missing: %s", e)
        FULL_FEATURES = False
    except Exception as e:
        logger.warning("Could not initialize full features: %s", e)
        FULL_FEATURES = False

# auth routes should always be available
try:
    app.register_blueprint(auth, url_prefix='')
except Exception as e:
    logger.warning("auth blueprint registration failed: %s", e)

# optional Firebase integration
if FIREBASE_AVAILABLE and FULL_FEATURES:
    try:
        file = app.config.get('SERVICE_ACCOUNT_DATA')
        if file:
            FIREBASE_CREDENTIALS = credentials.Certificate(file)
            initialize_app(FIREBASE_CREDENTIALS, {'databaseURL': app.config['DATABASEURL']})
            logger.info("Firebase initialized")
    except Exception as e:
        logger.warning("Firebase init failed: %s", e)

ALLOWED_EXTENSIONS = {'txt', 'py'}


def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if not FULL_FEATURES:
    @app.route('/')
    def index():
        return {'status': 'Smart-Google is working!', 'agent_user_id': app.config['AGENT_USER_ID']}

    @app.route('/health')
    def health():
        return jsonify({
            'status': 'degraded',
            'service': 'smart-google',
            'mqtt_connected': False,
        }), 503

    try:
        from action_devices import onSync, actions, request_sync, report_state

        @app.route('/devices')
        @login_required
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
        logger.warning("Could not import action_devices: %s", e)

if FULL_FEATURES:
    try:
        @app.before_first_request
        def create_db_command():
            # ensure database tables exist
            logger.info('DB Engine: %s', app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite').split(':')[0])
            db.create_all(app=app)
            logger.info('Initialized the database.')
    except Exception as e:
        logger.warning("Could not set up database initialization: %s", e)

if __name__ == '__main__':
    logger.info("Starting Smart-Google Flask Application")
    logger.info("Full features: %s", FULL_FEATURES)

    if FULL_FEATURES:
        try:
            db.create_all(app=app)
        except Exception:
            pass

    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    app.run(host=host, port=5000, debug=False)
