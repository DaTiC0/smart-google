# coding: utf-8
# Code By DaTi_Co
import logging
import os

from flask import Flask, send_from_directory
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app
from auth import auth
from models import User, db
from my_oauth import oauth
from notifications import mqtt
from routes import bp

# feature flags (mandatory)
FULL_FEATURES = True
FIREBASE_AVAILABLE = True

# configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask extensions that need initialization
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='templates')

    # load configuration
    if test_config:
        app.config.from_mapping(test_config)
    elif app.config.get("ENV") == "production":
        app.config.from_object("config.ProductionConfig")
    else:
        app.config.from_object("config.DevelopmentConfig")

    logger.info('ENV is set to: %s', app.config.get("ENV"))
    logger.info('Agent USER.ID: %s', app.config.get("AGENT_USER_ID"))

    # register blueprints
    app.register_blueprint(bp, url_prefix='')
    app.register_blueprint(auth, url_prefix='')

    # initialize extensions
    mqtt.init_app(app)
    mqtt.subscribe('+/notification')
    mqtt.subscribe('+/status')
    db.init_app(app)
    oauth.init_app(app)
    login_manager.init_app(app)

    # initialize firebase (assume available if import succeeded earlier)
    file = app.config.get('SERVICE_ACCOUNT_DATA')
    if file:
        creds = credentials.Certificate(file)
        initialize_app(creds, {'databaseURL': app.config.get('DATABASEURL')})
        logger.info('Firebase initialized')

    # database setup before first request
    @app.before_first_request
    def create_db_command():
        """Search for tables and if there is no data create new tables."""
        logger.info('DB Engine: %s', app.config['SQLALCHEMY_DATABASE_URI'].split(':')[0])
        db.create_all(app=app)
        logger.info('Initialized the database.')

    return app

# create the default app for imports
app = create_app()
# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}


@login_manager.user_loader
def load_user(user_id):
    """Get User ID"""
    logger.debug('loading user %s', user_id)
    return User.query.get(int(user_id))


def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'  # While in development
    db.create_all(app=app)
    app.run()
