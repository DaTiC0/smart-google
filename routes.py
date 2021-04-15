# coding: utf-8
# Code By DaTi_Co

import json
from flask import Blueprint, request, session, current_app
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from action_devices import onSync, report_state
from models import db, User, Client
from my_oauth import oauth, current_user
import RequestSync as sync
import ReportState as state


################################################################
bp = Blueprint(__name__, 'home')
################################################################


@bp.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        print(username)
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = current_user()
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
    user = current_user()
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
        'requestId': n,
        'agentUserId': current_app.config['AGENT_USER_ID'],
        'payload': ''
    }
    report_state_file['payload'] = report_state()
    # print(report_state_file)
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
def devices():
    dev_req = onSync('OK')
    devices = dev_req['devices']
    print('Are we OK?')
    return render_template('devices.html', title='Smart-David', devices=devices)

################################################################
