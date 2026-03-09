# coding: utf-8
# Code By DaTi_Co
# Generate service account file from ENV
# Temporary Solution
import logging
from os import environ, path
import json
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


def generate_file():
    s_file = path.join(basedir, 'service_account_file.json')
    with open(s_file) as json_file:
        data = json.load(json_file)
    data.update({
        'project_id': environ.get('PROJECT_ID'),
        'private_key_id': environ.get('PRIVATE_KEY_ID'),
        'private_key': environ.get('PRIVATE_KEY'),
        'client_email': environ.get('CLIENT_EMAIL'),
        'client_x509_cert_url': environ.get('CLIENT_X509_CERT_URL')
    })

    try:
        logger.debug('Try to replace NewLine Exception')
        data['private_key'] = data['private_key'].replace('\\n', '\n')
    except AttributeError as e:
        logger.warning('Error: %s', e)
    except KeyError as e:
        logger.warning('Error: %s', e)
    except Exception as e:
        logger.warning('Error: %s', e)
    logger.debug('Dictionary Generated')

    return data
