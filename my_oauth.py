# coding: utf-8
# Code By DaTi_Co
# OAuth2 – migrated from Flask-OAuthlib to Authlib
import logging
from datetime import datetime, timedelta, timezone

from flask import session
from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.integrations.flask_oauth2 import current_token  # noqa: F401 – re-exported
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6750 import BearerTokenValidator

from models import db, Client, Grant, Token, User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Authlib server & resource protector (initialised in create_app via init_oauth)
# ---------------------------------------------------------------------------
authorization = AuthorizationServer()
require_oauth = ResourceProtector()


# ---------------------------------------------------------------------------
# Helper: get the currently logged-in user from the session
# ---------------------------------------------------------------------------
def get_current_user():
    if 'id' in session:
        return db.session.get(User, session['id'])
    return None


# ---------------------------------------------------------------------------
# Client / token query + save helpers required by AuthorizationServer
# ---------------------------------------------------------------------------
def _query_client(client_id):
    return db.session.execute(
        db.select(Client).filter_by(client_id=client_id)
    ).scalar_one_or_none()


def _save_token(token_data, request):
    # Ensure each client/user pair has only one active token
    existing = db.session.execute(
        db.select(Token).filter_by(
            client_id=request.client.client_id,
            user_id=request.user.id,
        )
    ).scalars().all()
    for t in existing:
        db.session.delete(t)

    expires_in = token_data.get('expires_in', 3600)
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token', ''),
        token_type=token_data['token_type'],
        _scopes=token_data.get('scope', ''),
        expires=expires,
        client_id=request.client.client_id,
        user_id=request.user.id,
    )
    db.session.add(tok)
    db.session.commit()
    return tok


# ---------------------------------------------------------------------------
# Authorization Code grant
# ---------------------------------------------------------------------------
class _AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        'client_secret_basic',
        'client_secret_post',
        'none',
    ]

    def save_authorization_code(self, code, request):
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=100)
        grant = Grant(
            code=code,
            client_id=request.client.client_id,
            redirect_uri=request.redirect_uri or '',
            _scopes=' '.join(request.scopes),
            user=request.user,
            expires=expires,
        )
        db.session.add(grant)
        db.session.commit()
        logger.debug('Authorization code saved for client %s', request.client.client_id)
        return grant

    def query_authorization_code(self, code, client):
        return db.session.execute(
            db.select(Grant).filter_by(code=code, client_id=client.client_id)
        ).scalar_one_or_none()

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return db.session.get(User, authorization_code.user_id)


# ---------------------------------------------------------------------------
# Bearer token validator for protected resources
# ---------------------------------------------------------------------------
class _BearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string):
        return db.session.execute(
            db.select(Token).filter_by(access_token=token_string)
        ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Application-level initialiser – called from create_app()
# ---------------------------------------------------------------------------
def init_oauth(app):
    authorization.init_app(app, query_client=_query_client, save_token=_save_token)
    authorization.register_grant(_AuthorizationCodeGrant)
    require_oauth.register_token_validator(_BearerTokenValidator())
