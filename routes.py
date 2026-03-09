# coding: utf-8
# Code By DaTi_Co

from flask import Blueprint, current_app, request, jsonify, redirect, render_template, make_response, url_for
from flask_login import login_required, current_user
from action_devices import onSync, report_state, request_sync, actions, rquery
from models import Client
from my_oauth import get_current_user, oauth
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
@oauth.token_handler
def access_token():
    return {'version': '0.1.0'}


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
# Both GET (render consent page) and POST (handle form submission) are required
# by the OAuth2 Authorization Code flow and the @oauth.authorize_handler decorator.
@oauth.authorize_handler
def authorize(*args, **kwargs):
    user = get_current_user()
    if not user:
        return redirect('/')
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        if client is None:
            return redirect('/')
        kwargs['client'] = client
        kwargs['user'] = user
        return render_template('authorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'


@bp.route('/api/me')
@oauth.require_oauth()
def me(req):
    user = req.user
    return jsonify(username=user.username)


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


@bp.route('/device/<device_id>')
@login_required
def device_status(device_id):
    # Get specific device data
    dev_req = onSync()
    device = next((d for d in dev_req['devices'] if d['id'] == device_id), None)
    if not device:
        return redirect(url_for('routes.devices'))
    
    # Get current states
    states = rquery(device_id)
    return render_template('device_status.html', device=device, states=states)


@bp.route('/mqtt')
@login_required
def mqtt_log():
    return render_template('mqtt_log.html')


@bp.route('/smarthome', methods=['POST'])
def smarthome():
    req = request.get_json(silent=True, force=True)
    result = {
        'requestId': req['requestId'],
        'payload': actions(req),
    }
    return make_response(jsonify(result))
