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

import argparse
# import json
import requests
# from six.moves import urllib


def request_sync(api_key, agent_user_id):
    """This function does blah blah."""
    url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + api_key
    data = {"agentUserId": agent_user_id, "async": True}

    response = requests.post(url, json=data)

    print('\nRequests Code: %s' %
          requests.codes['ok'] + '\nResponse Code: %s' % response.status_code)
    print('\nResponse: ' + response.text)

    return response.status_code == requests.codes['ok']


def main(api_key, agent_user_id):
    """This function does blah blah."""
    if request_sync(api_key, agent_user_id):
        print('Request Sync has been done successfully.')
    else:
        print('Request Sync failed. Please check the log above.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'api_key',
        help='The api key downloaded from Google Cloud Platform Console.')
    parser.add_argument(
        'agent_user_id',
        help='The unique user ID on the agent\'s platform which returned in the SYNC response.')

    args = parser.parse_args()

    main(args.api_key, args.agent_user_id)
