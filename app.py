# coding: utf-8
# Code By DaTi_Co
import os

from flask import Flask, send_from_directory
from flask_login import LoginManager

from auth import auth
from models import User, db
from my_oauth import oauth
from notifications import mqtt
from routes import bp

# Flask Application
app = Flask(__name__, template_folder='templates')
# app.config.from_object('config.DevelopmentConfig')
if app.config["ENV"] == "production":
    app.config.from_object("config.ProductionConfig")
else:
    app.config.from_object("config.DevelopmentConfig")
print(f'ENV is set to: {app.config["ENV"]}')
print(f'Agent USER.ID: {app.config["AGENT_USER_ID"]}')
# app.config.from_pyfile('config_old.py')
app.register_blueprint(bp, url_prefix='')
app.register_blueprint(auth, url_prefix='')
# MQTT CONNECT
mqtt.init_app(app)
mqtt.subscribe('XXX/notification')
mqtt.subscribe('YYY/status')
# SQLAlchemy DATABASE
db.init_app(app)
print('SQLAlchemyURI: ' + app.config['SQLALCHEMY_DATABASE_URI'])
db.create_all(app=app)  # ????
# OAuth2 Authorisation
oauth.init_app(app)
# Flask Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

ALLOWED_EXTENSIONS = set(['txt', 'py'])  # for some files to save


@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


if __name__ == '__main__':
    os.environ['DEBUG'] = 'True'  # While in development
    db.create_all(app=app)
    app.run()
