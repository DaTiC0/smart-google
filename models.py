# models.py
import time
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Client(db.Model):
    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(
        db.String(55), unique=True, index=True, nullable=False)
    # creator of the client, not required
    user_id = db.Column(db.ForeignKey('user.id'))
    user = db.relationship('User')

    _redirect_uris = db.Column(db.Text)
    _default_scopes = db.Column(db.Text)

    # ------------------------------------------------------------------
    # Authlib ClientMixin interface
    # ------------------------------------------------------------------
    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        uris = self.redirect_uris
        return uris[0] if uris else ''

    def get_allowed_scope(self, scope):
        if not scope:
            return ''
        allowed = set(self.default_scopes)
        return ' '.join(allowed & set(scope.split()))

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret):
        return self.client_secret == client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        return True

    def check_grant_type(self, grant_type):
        return grant_type in ('authorization_code', 'refresh_token')

    def check_response_type(self, response_type):
        return response_type == 'code'

    # ------------------------------------------------------------------
    # Legacy helpers (kept for template compatibility)
    # ------------------------------------------------------------------
    @property
    def client_type(self):
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0] if self.redirect_uris else ''

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []


class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')
    code = db.Column(db.String(255), index=True, nullable=False)
    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    # ------------------------------------------------------------------
    # Authlib AuthorizationCodeMixin interface
    # ------------------------------------------------------------------
    def get_redirect_uri(self):
        return self.redirect_uri or ''

    def get_scope(self):
        return self._scopes or ''

    def get_auth_time(self):
        return int(time.time())

    def is_expired(self):
        if self.expires is None:
            return True
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expires

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id')
    )
    user = db.relationship('User')
    # currently only bearer is supported
    token_type = db.Column(db.String(40))

    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    _scopes = db.Column(db.Text)

    # ------------------------------------------------------------------
    # Authlib TokenMixin interface
    # ------------------------------------------------------------------
    def get_client_id(self):
        return self.client_id

    def get_scope(self):
        return self._scopes or ''

    def get_expires_at(self):
        if self.expires is None:
            return 0
        return int(self.expires.replace(tzinfo=timezone.utc).timestamp())

    def is_expired(self):
        if self.expires is None:
            return True
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expires

    def is_revoked(self):
        return False

    def check_client(self, client):
        return client.get_client_id() == self.client_id

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []
