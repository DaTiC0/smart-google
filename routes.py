# coding: utf-8
# Code By DaTi_Co

import json

from flask import (Blueprint, current_app, jsonify, redirect, render_template,
                   request, session)
from werkzeug.security import gen_salt
from flask_login import login_required, current_user
import ReportState as state
import RequestSync as sync
from action_devices import onSync, report_state
from models import Client, User, db
from my_oauth import get_current_user, oauth

################################################################
bp = Blueprint(__name__, 'home')
################################################################

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)


@bp.route('/old_login', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = get_current_user()
    print(user)
    return render_template('home.html', user=user)


@bp.route('/oauth/token', methods=['POST'])
@oauth.token_handler
def access_token():
    print('this is token')
    return {'version': '0.1.0'}


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
@oauth.authorize_handler
def authorize(*args, **kwargs):
    print("this is authorize")
    user = get_current_user()
    print("Authorize User: %s" % user)
    if not user:
        return redirect('/')
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        print(client_id)
        print(client)
        kwargs['client'] = client
        kwargs['user'] = user
        return render_template('authorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@bp.route('/api/me')
@oauth.require_oauth()
def me(req):
    print("this is me")
    user = req.user
    return jsonify(username=user.username)

################################################################

@bp.route('/sync')
def sync_devices():
    sync.main(current_app.config['API_KEY'],
              current_app.config['AGENT_USER_ID'])
    # state.main(current_app.config['SERVICE_ACCOUNT_FILE'], 'report_state_file.json')
    # lets fix this
    import random
    n = random.randint(10000000000000000000, 90000000000000000000)
    report_state_file = {
        'requestId': str(n),
        'agentUserId': current_app.config['AGENT_USER_ID'],
        'payload': report_state(),
    }
    # report state generated
    # now need to generate service account
    state.main(current_app.config['SERVICE_ACCOUNT_FILE'], report_state_file)
    return "THIS IS TEST NO RETURN"


@bp.route('/IFTTT', methods=['POST'])
def ifttt():
    req = request.get_json(silent=True, force=True)

    print('INCOMING IFTTT:')
    print(json.dumps(req, indent=4))
    # print(req)

    result = {
        "data": {
            'x': 'DaTi',
            'y': 'Comnpany'
        }
    }

    return result


# Created for DIY Sprinkler MADE BY DATI_CO (ME)
# Sprinkler code not finished
# Using Micropython on microcontrollers
@bp.route('/sprink')
def sprink():
    return "NOT OK"


@bp.route('/devices')
@login_required
def devices():
    dev_req = onSync('OK')
    device_list = dev_req['devices']
    print('Are we OK?')
    return render_template('devices.html', title='Smart-Home', devices=device_list)

################################################################
