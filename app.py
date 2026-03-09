# coding: utf-8
# Code By DaTi_Co
import os
import logging
from typing import Any, cast

from flask import Flask, send_from_directory
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app, get_app
from auth import auth
from models import User, db
from my_oauth import oauth
from notifications import mqtt
from routes import bp

# Module logger
logger = logging.getLogger(__name__)


def _get_config_object() -> str:
    """Resolve config from explicit APP_ENV with FLASK_ENV fallback."""
    environment = os.getenv('APP_ENV', os.getenv('FLASK_ENV', 'development')).lower()
    if environment in {'production', 'prod'}:
        return 'config.ProductionConfig'
    return 'config.DevelopmentConfig'


def _init_firebase(flask_app: Flask) -> None:
    """Initialize Firebase only when required configuration is available."""
    # Avoid duplicate default app initialization when module reload/import happens.
    try:
        get_app()
        logger.info('Firebase already initialized; skipping re-initialization.')
        return
    except ValueError:
        pass

    service_account_data = flask_app.config.get('SERVICE_ACCOUNT_DATA')
    database_url = flask_app.config.get('DATABASEURL')

    if not service_account_data or not database_url:
        logger.warning('Firebase config missing; skipping Firebase initialization.')
        return

    firebase_credentials = credentials.Certificate(service_account_data)
    firebase_options = {'databaseURL': database_url}
    initialize_app(firebase_credentials, firebase_options)


# Flask Application Configuration
app = Flask(__name__, template_folder='templates')
app.config.from_object(_get_config_object())

logger.info('ENV is set to: %s', app.config.get('ENV'))
logger.info('Agent USER.ID: %s', app.config.get('AGENT_USER_ID'))

app.register_blueprint(bp, url_prefix='')
app.register_blueprint(auth, url_prefix='')

# MQTT CONNECT
try:
    mqtt.init_app(app)
    mqtt.subscribe('+/notification')
    mqtt.subscribe('+/status')
except Exception as e:
    logger.warning('MQTT initialization skipped: %s', e)

# SQLAlchemy DATABASE
db.init_app(app)

# OAuth2 Authorisation
oauth.init_app(app)

# Flask Login
login_manager = LoginManager()
cast(Any, login_manager).login_view = 'auth.login'
login_manager.init_app(app)

# FIREBASE_CONFIG environment variable can be added
_init_firebase(app)

# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}


@login_manager.user_loader
def load_user(user_id):
    """Get User ID"""
    session = cast(Any, db.session)
    return session.get(User, int(user_id))


def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.before_first_request
def create_db_command():
    """Search for tables and if there is no data create new tables."""
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    logger.info('DB Engine: %s', db_uri.split(':')[0] if db_uri else 'unknown')
    db.create_all(app=app)
    logger.info('Initialized the database.')


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'  # While in development
    db.create_all(app=app)
    app.run(debug=app.config.get('DEBUG', False))
