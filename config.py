# coding: utf-8
# Code By DaTi_Co
# Config.py
# App Configuration File
from os import environ, path
import secrets
from dotenv import load_dotenv
from generate_service_account_file import generate_file

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

data = generate_file()


class Config:
    # General Config
    DEBUG = False
    TESTING = False
    SECRET_KEY = environ.get('SECRET_KEY')
    UPLOAD_FOLDER = './static/upload'
    SQLALCHEMY_DATABASE_URI = environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MQTT_BROKER_URL = environ.get('MQTT_BROKER_URL')
    MQTT_BROKER_PORT = 11868
    MQTT_USERNAME = environ.get('MQTT_USERNAME')
    MQTT_PASSWORD = environ.get('MQTT_PASSWORD')
    MQTT_KEEPALIVE = 90
    MQTT_TLS_ENABLED = False  # set TLS to disabled for testing purposes
    API_KEY = environ.get('API_KEY')
    AGENT_USER_ID = environ.get('AGENT_USER_ID')
    DATABASEURL = environ.get('DATABASEURL')  # your Project database URL
    SERVICE_ACCOUNT_DATA = data


class ProductionConfig(Config):
    DEBUG = False
    # DATABASEURL = '192.168.1.100'  # change to some your URL


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = secrets.token_urlsafe(16)


class TestingConfig(Config):
    DB_SERVER = 'localhost'
    DEBUG = True
    DATABASE_URI = 'sqlite:///:memory:'
