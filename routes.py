# coding: utf-8
# Code By DaTi_Co

from flask import Blueprint, current_app, request, jsonify, redirect, render_template, make_response
from flask_login import login_required, current_user
from sqlalchemy import select
from action_devices import onSync, report_state, request_sync, actions
from models import Client, db
from my_oauth import get_current_user, authorization, require_oauth, current_token
from notifications import is_mqtt_connected


bp = Blueprint('routes', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/health')
def health():
    mqtt_connected = is_mqtt_connected()
    status_code = 200 if mqtt_connected else 503
    return jsonify({
        'status': 'ok' if mqtt_connected else 'degraded',
        'service': 'smart-google',
        'mqtt_connected': mqtt_connected,
    }), status_code


@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)


@bp.route('/oauth/token', methods=['POST'])
def access_token():
    return authorization.create_token_response()


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = get_current_user()
    if not user:
        return redirect('/')

    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except Exception:
            return redirect('/')
        client_id = request.args.get('client_id')
        client = db.session.execute(
            select(Client).filter_by(client_id=client_id)
        ).scalar_one_or_none()
        if client is None:
            return redirect('/')
        return render_template('authorize.html', grant=grant, user=user, client=client)

    confirmed = request.form.get('confirm', 'no') == 'yes'
    return authorization.create_authorization_response(
        grant_user=user if confirmed else None
    )


@bp.route('/api/me')
@require_oauth()
def me():
    user = current_token.user
    return jsonify(email=user.email)


@bp.route('/sync')
def sync_devices():
    request_sync(current_app.config['API_KEY'],
                 current_app.config['AGENT_USER_ID'])
    report_state()

    return "Sync request sent"


@bp.route('/IFTTT', methods=['POST'])
def ifttt():
    # Get the event name from IFTTT
    event_name = request.json.get('event_name', None)
    if event_name is None:
        # If no event name is found, return an error
        return jsonify({'errors': [{'message': 'No event name specified'}]}), 400

    # Get the data associated with the event
    data = request.json.get('data', None)
    if data is None:
        # If no data is found, return an error
        return jsonify({'errors': [{'message': 'No data specified'}]}), 400

    # Do something with the event and data
    return jsonify({'data': [{'id': 1, 'name': 'Test'}]}), 200


@bp.route('/devices')
@login_required
def devices():
    dev_req = onSync()
    device_list = dev_req['devices']
    return render_template('devices.html', title='Smart-Home', devices=device_list)


@bp.route('/smarthome', methods=['POST'])
def smarthome():
    req = request.get_json(silent=True, force=True)
    result = {
        'requestId': req['requestId'],
        'payload': actions(req),
    }
    return make_response(jsonify(result))
