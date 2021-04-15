# coding: utf-8
# Code By DaTi_Co
# Config.py
# App Configuration File
from os import environ, path
from dotenv import load_dotenv
from generate_service_account_file import generate_file

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

# General Config
DEBUG = True  # Turns on debugging features in Flask
SECRET_KEY = environ.get('SECRET_KEY')
UPLOAD_FOLDER = './static/upload'
SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI')
SQLALCHEMY_TRACK_MODIFICATIONS = False
MQTT_BROKER_URL = environ.get('MQTT_BROKER_URL')  # use the free broker from HIVEMQ
MQTT_BROKER_PORT = 11868  # default port for non-tls connection
MQTT_USERNAME = environ.get('MQTT_USERNAME')  # set the username here if you need authentication for the broker
MQTT_PASSWORD = environ.get('MQTT_PASSWORD')  # set the password here if the broker demands authentication
MQTT_KEEPALIVE = 90  # set the time interval for sending a ping to the broker to 5 seconds
MQTT_TLS_ENABLED = False  # set TLS to disabled for testing purposes
API_KEY = environ.get('API_KEY')
AGENT_USER_ID = environ.get('AGENT_USER_ID')
SERVICE_ACCOUNT_FILE = generate_file()
FIREBASE_ADMINSDK_FILE = generate_file()
# SERVICE_ACCOUNT_FILE = environ.get('SERVICE_ACCOUNT_FILE')  # Google service account file location and name
# FIREBASE_ADMINSDK_FILE = environ.get('FIREBASE_ADMINSDK_FILE')
DATABASEURL = environ.get('DATABASEURL')  # your Project database URL
SERVICE_ACCOUNT_DATA = environ.get('SERVICE_ACCOUNT_DATA')
