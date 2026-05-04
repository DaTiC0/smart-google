# coding: utf-8
# Code By DaTi_Co
import os
import logging
from typing import Any, cast

from flask import Flask, send_from_directory
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app, get_app
from sqlalchemy import inspect, text
from auth import auth
from models import User, db
from my_oauth import init_oauth
from notifications import mqtt
from routes import bp

# Module logger
logger = logging.getLogger(__name__)


def _is_production_environment() -> bool:
    """Return True when runtime environment is production-like."""
    environment = os.getenv('APP_ENV', os.getenv('FLASK_ENV', 'development')).lower()
    return environment in {'production', 'prod'}


def _get_config_object() -> str:
    """Resolve config from explicit APP_ENV with FLASK_ENV fallback."""
    if _is_production_environment():
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

if not _is_production_environment():
    # Authlib requires HTTPS by default; allow HTTP for local/dev/test only.
    os.environ.setdefault('AUTHLIB_INSECURE_TRANSPORT', '1')

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
init_oauth(app)

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


def init_database_schema(flask_app: Flask) -> None:
    """Create DB tables if they do not exist."""
    db_uri = flask_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    logger.info('DB Engine: %s', db_uri.split(':')[0] if db_uri else 'unknown')
    with flask_app.app_context():
        db.create_all()
        _ensure_password_column_capacity()
    logger.info('Initialized the database.')


def _ensure_password_column_capacity() -> None:
    """Ensure legacy user.password columns can store modern Werkzeug hashes."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if 'user' not in table_names:
        return

    columns = {column['name']: column for column in inspector.get_columns('user')}
    password_column = columns.get('password')
    if not password_column:
        return

    current_length = getattr(password_column['type'], 'length', None)
    if current_length is None or current_length >= 255:
        return

    dialect = db.engine.dialect.name
    alter_sql = _password_column_migration_sql(dialect)
    if not alter_sql:
        message = (
            'Detected legacy password column length=%s on unsupported dialect=%s; '
            'manual migration to VARCHAR(255) required.'
        )
        if _is_production_environment():
            raise RuntimeError(message % (current_length, dialect))
        logger.warning(message, current_length, dialect)
        return

    logger.info('Expanding user.password column from %s to 255.', current_length)
    db.session.execute(text(alter_sql))
    db.session.commit()


def _password_column_migration_sql(dialect: str) -> Any:
    """Return migration SQL for supported dialects, or None if unsupported."""
    if dialect == 'postgresql':
        return 'ALTER TABLE "user" ALTER COLUMN password TYPE VARCHAR(255)'
    if dialect in {'mysql', 'mariadb'}:
        return 'ALTER TABLE `user` MODIFY COLUMN password VARCHAR(255)'
    return None


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.cli.command('init-db')
def create_db_command() -> None:
    """Initialize database tables."""
    init_database_schema(app)


if __name__ == '__main__':
    init_database_schema(app)
    app.run(debug=app.config.get('DEBUG', False))
