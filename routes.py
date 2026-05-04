# coding: utf-8
# Code By DaTi_Co

import logging
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse
from flask import Blueprint, current_app, request, jsonify, redirect, render_template, make_response, url_for
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2.rfc6749 import OAuth2Error
from flask_login import login_required, current_user
from action_devices import onSync, report_state, request_sync, actions, rquery
from my_oauth import get_current_user, load_client, oauth, require_oauth
from notifications import get_mqtt_logs, is_mqtt_connected

logger = logging.getLogger(__name__)


bp = Blueprint('routes', __name__)


def _oauth_error_response(exc):
    """Return OAuth errors in a client-friendly way when redirect URI is valid."""
    client_id = request.values.get('client_id')
    redirect_uri = request.values.get('redirect_uri')
    state = request.values.get('state')

    client = load_client(client_id) if client_id else None
    if client:
        if not redirect_uri:
            redirect_uri = client.get_default_redirect_uri()
        if redirect_uri and client.check_redirect_uri(redirect_uri):
            parsed = urlparse(redirect_uri)
            if parsed.scheme and parsed.netloc:
                params = {'error': exc.error}
                if exc.description:
                    params['error_description'] = exc.description
                if state:
                    params['state'] = state

                existing_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
                existing_query.update(params)
                safe_redirect_uri = urlunparse(
                    parsed._replace(query=urlencode(existing_query))
                )
                return redirect(safe_redirect_uri)

    status_code = getattr(exc, 'status_code', 400) or 400
    return jsonify(error=exc.error, error_description=exc.description), status_code


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
    return oauth.create_token_response()


@bp.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = get_current_user()
    if not user:
        return redirect('/')

    try:
        grant = oauth.get_consent_grant(end_user=user)
    except OAuth2Error as exc:
        logger.exception("OAuth consent grant error: %s", exc)
        return _oauth_error_response(exc)

    if request.method == 'GET':
        request_payload = getattr(grant.request, 'payload', grant.request)
        scope = getattr(request_payload, 'scope', '') or ''
        return render_template(
            'authorize.html',
            client=grant.client,
            user=user,
            scopes=scope.split(),
            response_type=getattr(request_payload, 'response_type', None),
            state=getattr(request_payload, 'state', None),
        )

    confirm = request.form.get('confirm', 'no')
    grant_user = user if confirm == 'yes' else None
    return oauth.create_authorization_response(grant_user=grant_user, grant=grant)


@bp.route('/api/me')
@require_oauth()
def me():
    user = current_token.user
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
    logger.debug("Retrieving devices for user: %s", current_user)
    dev_req = onSync()
    device_list = dev_req['devices']
    logger.debug("Device list: %s", device_list)
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
    connected = is_mqtt_connected()
    positive_statuses = {'Received', 'Connected', 'Clean disconnect'}
    log_entries = [
        {
            **entry,
            'status_class': 'status-pill--active' if entry.get('status') in positive_statuses else '',
        }
        for entry in get_mqtt_logs()
    ]
    return render_template(
        'mqtt_log.html',
        broker_connected=connected,
        tls_enabled=current_app.config.get('MQTT_TLS_ENABLED', False),
        log_entries=log_entries,
    )


@bp.route('/smarthome', methods=['POST'])
def smarthome():
    req = request.get_json(silent=True, force=True)
    if not req or 'requestId' not in req or 'inputs' not in req:
        logger.warning("Invalid smarthome request: missing required fields")
        return jsonify({'error': 'Invalid request format'}), 400
    logger.debug("Smart home request: %s", req.get('requestId', 'unknown'))
    result = {
        'requestId': req['requestId'],
        'payload': actions(req),
    }
    logger.debug("Smart home response: %s", result)
    return make_response(jsonify(result))
