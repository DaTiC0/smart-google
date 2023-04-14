# coding: utf-8
# Code By DaTi_Co
import os

from flask import Flask, send_from_directory
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app
from auth import auth
from models import User, db
from my_oauth import oauth
from notifications import mqtt
from routes import bp

# Flask Application Configuration
app = Flask(__name__, template_folder='templates')
if app.config["ENV"] == "production":
    app.config.from_object("config.ProductionConfig")
else:
    app.config.from_object("config.DevelopmentConfig")
print(f'ENV is set to: {app.config["ENV"]}')
print(f'Agent USER.ID: {app.config["AGENT_USER_ID"]}')
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
# FIREBASE_CONFIG environment variable can be added
FIREBASE_ADMINSDK_FILE = app.config['SERVICE_ACCOUNT_DATA']
FIREBASE_CREDENTIALS = credentials.Certificate(FIREBASE_ADMINSDK_FILE)
FIREBASE_DATABASEURL = app.config['DATABASEURL']
FIREBASE_OPTIONS = {'databaseURL': FIREBASE_DATABASEURL}
initialize_app(FIREBASE_CREDENTIALS, FIREBASE_OPTIONS)
# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}


@login_manager.user_loader
def load_user(user_id):
    """Get User ID"""
    print(user_id)
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


@app.before_first_request
def create_db_command():
    """Search for tables and if there is no data create new tables."""
    print('DB Engine: ' + app.config['SQLALCHEMY_DATABASE_URI'].split(':')[0])
    db.create_all(app=app)
    print('Initialized the database.')


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'  # While in development
    db.create_all(app=app)
    app.run()
