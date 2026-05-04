# coding: utf-8
# Code By DaTi_Co
# OAuth2
import logging
from datetime import datetime, timedelta, timezone
from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import session
from flask_login import current_user
from sqlalchemy import select
from models import db
from models import Client, Token, Grant, User

logger = logging.getLogger(__name__)

oauth = AuthorizationServer()
require_oauth = ResourceProtector()
AUTHORIZATION_CODE_EXPIRES_IN = 100
DEFAULT_ACCESS_TOKEN_EXPIRES_IN = 3600


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_current_user():
    # Prefer Flask-Login identity so OAuth consent works after normal login flow.
    if current_user.is_authenticated:
        return current_user

    # Fallback for legacy session payloads.
    if 'id' in session:
        uid = session['id']
        user = db.session.get(User, uid)
        logger.debug("Current user: %s", user)
        return user
    return None


def load_client(client_id):
    logger.debug("get client")
    logger.debug("client_id: %s", client_id)
    client = db.session.scalars(
        select(Client).filter_by(client_id=client_id)
    ).first()
    logger.debug("Client: %s", client)
    return client


def save_token(token_data, request):
    logger.debug("token setter")
    # make sure that every client has only one token connected to a user
    existing_tokens = db.session.execute(
        select(Token).filter_by(
            client_id=request.client.client_id,
            user_id=request.user.id,
        )
    ).scalars()
    for t in existing_tokens:
        db.session.delete(t)

    raw_expires_in = token_data.get('expires_in')
    try:
        expires_in = int(raw_expires_in)
        if expires_in <= 0:
            raise ValueError('expires_in must be positive')
    except (TypeError, ValueError):
        logger.warning(
            "Invalid token expires_in=%r; defaulting to %s seconds",
            raw_expires_in,
            DEFAULT_ACCESS_TOKEN_EXPIRES_IN,
        )
        expires_in = DEFAULT_ACCESS_TOKEN_EXPIRES_IN
    expires = _utcnow_naive() + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token'),
        token_type=token_data.get('token_type', 'Bearer'),
        _scopes=token_data.get('scope', ''),
        expires=expires,
        client_id=request.client.client_id,
        user_id=request.user.id,
    )
    logger.debug("Token created: %s", tok)
    db.session.add(tok)
    db.session.commit()
    return tok


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(self, code, request):
        logger.debug("save authorization code")
        request_payload = getattr(request, 'payload', request)
        redirect_uri = getattr(request_payload, 'redirect_uri', None) or getattr(request, 'redirect_uri', None)
        scope = getattr(request_payload, 'scope', None)
        if scope is None:
            scope = getattr(request, 'scope', '')
        expires = _utcnow_naive() + timedelta(seconds=AUTHORIZATION_CODE_EXPIRES_IN)
        grant = Grant(
            client_id=request.client.client_id,
            code=code,
            redirect_uri=redirect_uri,
            _scopes=scope or '',
            user=request.user,
            expires=expires,
        )
        db.session.add(grant)
        db.session.commit()
        return grant

    def query_authorization_code(self, code, client):
        grant = db.session.scalars(
            select(Grant).filter_by(client_id=client.client_id, code=code)
        ).first()
        if grant and not grant.is_expired():
            return grant
        return None

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        token = db.session.scalars(
            select(Token).filter_by(refresh_token=refresh_token)
        ).first()
        if token and not token.is_expired() and not token.is_revoked():
            return token
        return None

    def authenticate_user(self, refresh_token):
        return refresh_token.user

    def revoke_old_credential(self, refresh_token):
        db.session.delete(refresh_token)
        db.session.commit()


class MyBearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string):
        token = db.session.scalars(
            select(Token).filter_by(access_token=token_string)
        ).first()
        if token and (token.is_expired() or token.is_revoked()):
            return None
        return token


def init_oauth(app):
    if app.extensions.get('authlib_oauth_configured'):
        return

    oauth.init_app(app, query_client=load_client, save_token=save_token)
    oauth.register_grant(AuthorizationCodeGrant)
    oauth.register_grant(RefreshTokenGrant)
    require_oauth.register_token_validator(MyBearerTokenValidator())
    app.extensions['authlib_oauth_configured'] = True
