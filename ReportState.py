import time
import json
from flask import current_app
from google.auth import crypt, jwt
import requests


def generate_jwt(service_account):
    signer = crypt.RSASigner.from_string(service_account['private_key'])
    now = int(time.time())
    payload = {
        'iat': now,
        'exp': now + 3600,
        'aud': 'https://accounts.google.com/o/oauth2/token',
        'iss': service_account['client_email'],
        'scope': 'https://www.googleapis.com/auth/homegraph'
    }

    return jwt.encode(signer, payload)


def get_access_token(signed_jwt):
    url = 'https://accounts.google.com/o/oauth2/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = f'grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion={signed_jwt}'
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == requests.codes.ok:
        token_data = json.loads(response.text)
        return token_data['access_token']
    response.raise_for_status()

    return 'ERROR'


def report_state(access_token, report_state_file):
    url = 'https://homegraph.googleapis.com/v1/devices:reportStateAndNotification'
    headers = {'X-GFE-SSL': 'yes', 'Authorization': f'Bearer {access_token}'}
    data = report_state_file
    response = requests.post(url, headers=headers, json=data)
    print(f'Response: {response.text}')

    return response.status_code == requests.codes.ok


def main(report_state_file):
    service_account = current_app.config['SERVICE_ACCOUNT_DATA']
    print('By ReportState')
    signed_jwt = generate_jwt(service_account).decode("utf-8")  # Decode
    access_token = get_access_token(signed_jwt)
    if success := report_state(access_token, report_state_file):
        print('Report State has been done successfully.')
    else:
        print('Report State failed. Please check the log above.')
