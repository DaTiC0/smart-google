# coding: utf-8
# Code By DaTi_Co
# Generate service account file from ENV
# TEmporary Solution
from os import environ, path
from dotenv import load_dotenv


basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


def generate_file():
    data = {
        'type': 'service_account',
        'project_id': environ.get('PROJECT_ID'),
        'private_key_id': environ.get('PRIVATE_KEY_ID'),
        'private_key': environ.get('PRIVATE_KEY'),
        'client_email': environ.get('CLIENT_EMAIL'),
        'client_id': '',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
        'client_x509_cert_url': environ.get('CLIENT_X509_CERT_URL')
    }

    print('replacing NewLine Exception')
    data['private_key'] = data['private_key'].replace('\\n', '\n')

    # with open('service_account_file.json', 'w') as jsonFile:
    #     json.dump(data, jsonFile, indent=4)
    return data
