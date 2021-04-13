# Generate service account file from ENV
# TEmporary Solution
from os import environ, path
from dotenv import load_dotenv
import json

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


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
try:
    print('Try to replace NewLine Exception')
    data['private_key'] = data['private_key'].replace('\\n', '\n')
except:
    print('Nothing to replace')

print('DICTIONARY: ')
print(data)

with open('service_account_file.json', 'w') as jsonFile:
    json.dump(data, jsonFile, indent=4)
