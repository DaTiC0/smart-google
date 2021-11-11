# coding: utf-8
# Code By DaTi_Co

import json

from flask import Blueprint, current_app, request, jsonify, redirect, render_template, make_response
from flask_login import login_required, current_user
from action_devices import onSync, report_state, request_sync, actions
from models import Client
from my_oauth import get_current_user, oauth


bp = Blueprint(__name__, 'home')


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)


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


@bp.route('/sync')
def sync_devices():
    request_sync(current_app.config['API_KEY'],
                 current_app.config['AGENT_USER_ID'])
    report_state()

    return "THIS IS TEST NO RETURN"


@bp.route('/IFTTT', methods=['POST'])
def ifttt():
    req = request.get_json(silent=True, force=True)

    print('INCOMING IFTTT:')
    print(json.dumps(req, indent=4))
    return {
        "data": {
            'x': 'DaTi',
            'y': 'Comnpany'
        }
    }


# Created for DIY Sprinkler MADE BY DATI_CO (ME)
# Sprinkler code not finished
# Using Micropython on microcontrollers
@bp.route('/sprink')
def sprink():
    return "NOT OK"


@bp.route('/devices')
@login_required
def devices():
    dev_req = onSync()
    device_list = dev_req['devices']
    print('Are we OK?')
    return render_template('devices.html', title='Smart-Home', devices=device_list)


@bp.route('/smarthome', methods=['POST'])
def smarthome():
    req = request.get_json(silent=True, force=True)
    print("INCOMING REQUEST FROM GOOGLE HOME:")
    print(json.dumps(req, indent=4))
    payload = actions(req)
    result = {
        'requestId': req['requestId'],
        'payload': payload,
    }
    print('RESPONSE TO GOOGLE HOME')
    print(json.dumps(result, indent=4))
    return make_response(jsonify(result))
