#!/usr/bin/env python

# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A tool for calling HomeGraph API with a JWT signed
by a Google API Service Account.
"""

import argparse
import time
import json
import io

import google.auth.crypt
import google.auth.jwt
import requests
# from six.moves import urllib


def generate_jwt(service_account_file):
    """Generates a signed JSON Web Token using a Google API Service Account."""

    # Note: this sample shows how to manually create the JWT for the purposes
    # of showing how the authentication works, but you can use
    # google.auth.jwt.Credentials to automatically create the JWT.
    #   http://google-auth.readthedocs.io/en/latest/reference
    #   /google.auth.jwt.html#google.auth.jwt.Credentials

    signer = google.auth.crypt.RSASigner.from_service_account_file(
        service_account_file)

    now = int(time.time())
    expires = now + 3600  # One hour in seconds

    iss = ''

    with io.open(service_account_file, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        iss = data['client_email']

    payload = {
        'iat': now,
        'exp': expires,
        'aud': 'https://accounts.google.com/o/oauth2/token',
        'iss': iss,
        'scope': 'https://www.googleapis.com/auth/homegraph'
    }

    signed_jwt = google.auth.jwt.encode(signer, payload)

    return signed_jwt


def get_access_token(signed_jwt):
    url = 'https://accounts.google.com/o/oauth2/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = 'grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=' + signed_jwt

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == requests.codes.ok:
        token_data = json.loads(response.text)
        return token_data['access_token']

    response.raise_for_status()
    return 'ERROR'


def report_state(access_token, report_state_file):
    url = 'https://homegraph.googleapis.com/v1/devices:reportStateAndNotification'
    headers = {
        'X-GFE-SSL': 'yes',
        'Authorization': 'Bearer ' + access_token
    }
    data = {}

    with io.open(report_state_file, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    response = requests.post(url, headers=headers, json=data)

    print('Response: ' + response.text)

    return response.status_code == requests.codes.ok


def main(service_account_file, report_state_file):
    signed_jwt = generate_jwt(service_account_file).decode("utf-8")  # Decode
    print('signed JWT: ' + signed_jwt)

    access_token = get_access_token(signed_jwt)
    print('access token: ' + access_token)

    success = report_state(access_token, report_state_file)
    if success:
        print('Report State has been done successfully.')
    else:
        print('Report State failed. Please check the log above.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'service_account_file',
        help='The path to your service account json file.')
    parser.add_argument(
        'report_state_file',
        help='The path to the json file containing the states you want to report.')

    args = parser.parse_args()

    main(args.service_account_file, args.report_state_file)
