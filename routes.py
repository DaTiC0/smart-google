import RequestSync as sync      # GOOGLE
import ReportState as state     # GOOGLE
import json
from flask import Blueprint, request, session, current_app, render_template
from action_devices import onSync


################################################################
bp = Blueprint(__name__, 'home')
################################################################

# Created for DIY Sprinkler MADE BY DATI_CO (ME)
# Sprinkler code not finished
# Using Micropython on microcontrollers
@bp.route('/sprink')
def sprink():
    return "NOT OK"


@bp.route('/sync')
def sync_devices():
    sync.main(current_app.config['API_KEY'], current_app.config['AGENT_USER_ID'])
    state.main(current_app.config['SERVICE_ACCOUNT_FILE'], 'report_state_file.json')
    return "THIS IS TEST NO RETURN"


@bp.route('/devices')
def devices():
    dev_req = onSync('OK')
    devices = dev_req['devices']
    print('Are we OK?')
    return render_template('devices.html', title='Smart-David', devices=devices)


def ifttt():
    # IFTTT Integration not completed
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