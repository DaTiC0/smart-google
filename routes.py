# coding: utf-8
# Code By DaTi_Co

import json
from flask import Blueprint, request, session, current_app
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from action_devices import onSync
from models import db, User, Client
from oauth2 import oauth, current_user
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
        print(user)
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = current_user()
    print(user)
    return render_template('home.html', user=user)


@bp.route('/sync')
def sync_devices():
    sync.main(current_app.config['API_KEY'], current_app.config['AGENT_USER_ID'])
    state.main(current_app.config['SERVICE_ACCOUNT_FILE'], 'report_state_file.json')
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