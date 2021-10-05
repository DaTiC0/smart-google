# coding: utf-8
# Code By DaTi_Co
# OAuth2
from datetime import datetime, timedelta
from flask_oauthlib.provider import OAuth2Provider
from flask import session
from models import db
from models import Client, Token, Grant, User

oauth = OAuth2Provider()


def get_current_user():
    if 'id' in session:
        uid = session['id']
        print(User.query.get(uid))
        return User.query.get(uid)
    return None


@oauth.clientgetter
def load_client(client_id):
    print("get client")
    print(client_id)
    print(Client.query.filter_by(client_id=client_id).first())
    return Client.query.filter_by(client_id=client_id).first()


@oauth.grantgetter
def load_grant(client_id, code):
    print("grant getter")
    return Grant.query.filter_by(client_id=client_id, code=code).first()


@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    # decide the expires time yourself
    print("save grant")
    expires = datetime.utcnow() + timedelta(seconds=100)
    grant = Grant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=request.redirect_uri,
        _scopes=' '.join(request.scopes),
        user=get_current_user(),
        expires=expires
    )
    print(grant)
    db.session.add(grant)
    db.session.commit()
    return grant


@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    print("token getter")
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    if refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()


@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    print("token setter")
    toks = Token.query.filter_by(
        client_id=request.client.client_id,
        user_id=request.user.id
    )
    print(toks)
    # make sure that every client has only one token connected to a user
    for t in toks:
        db.session.delete(t)

    expires_in = token.pop('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    tok = Token(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_type=token['token_type'],
        _scopes=token['scope'],
        expires=expires,
        client_id=request.client.client_id,
        user_id=request.user.id,
    )
    print(tok)
    db.session.add(tok)
    db.session.commit()
    return tok