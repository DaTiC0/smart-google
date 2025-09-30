#!/usr/bin/env python3
# coding: utf-8
# Code By DaTiC0
# Fixed Flask application for smart-google with proper Flask usage

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from flask import Flask, send_from_directory, jsonify, request, make_response
import json

# Import the fixed action devices
from action_devices import onSync, report_state, request_sync, actions

# Flask Application Configuration
app = Flask(__name__, template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = True
app.config['AGENT_USER_ID'] = os.environ.get('AGENT_USER_ID', 'test-user')
app.config['API_KEY'] = os.environ.get('API_KEY', 'test-api-key')
app.config['DATABASEURL'] = os.environ.get('DATABASEURL', 'https://test-project-default-rtdb.firebaseio.com/')
app.config['SERVICE_ACCOUNT_DATA'] = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json')
app.config['UPLOAD_FOLDER'] = './static/upload'

print(f'ENV is set to: {app.config.get("ENV", "development")}')
print(f'Agent USER.ID: {app.config["AGENT_USER_ID"]}')

# File Extensions for Upload Folder
ALLOWED_EXTENSIONS = {'txt', 'py'}

def allowed_file(filename):
    """File Uploading Function"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """File formats for upload folder"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Basic routes
@app.route('/')
def index():
    """Main index route"""
    return jsonify({
        'status': 'Smart-Google Flask App Running!',
        'version': '1.0.0-flask-fixed',
        'agent_user_id': app.config['AGENT_USER_ID'],
        'message': 'Flask is now working properly!'
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'flask_version': '2.0.3',
        'config_loaded': True,
        'environment_vars': {
            'SECRET_KEY': bool(os.environ.get('SECRET_KEY')),
            'AGENT_USER_ID': bool(os.environ.get('AGENT_USER_ID')),
            'API_KEY': bool(os.environ.get('API_KEY')),
            'DATABASEURL': bool(os.environ.get('DATABASEURL'))
        }
    })

@app.route('/sync')
def sync_devices():
    """Request sync with Google Home"""
    try:
        success = request_sync(app.config['API_KEY'], app.config['AGENT_USER_ID'])
        state_result = report_state()
        return jsonify({
            'sync_requested': True,
            'success': success,
            'state_report': state_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/devices')
def devices():
    """Get devices for Google Home"""
    try:
        dev_req = onSync()
        return jsonify(dev_req)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/smarthome', methods=['POST'])
def smarthome():
    """Google Home fulfillment endpoint"""
    try:
        req_data = request.get_json(silent=True, force=True)
        print("INCOMING REQUEST FROM GOOGLE HOME:")
        print(json.dumps(req_data, indent=4))
        
        result = {
            'requestId': req_data.get('requestId', 'unknown'),
            'payload': actions(req_data),
        }
        
        print('RESPONSE TO GOOGLE HOME')
        print(json.dumps(result, indent=4))
        return make_response(jsonify(result))
    except Exception as e:
        print(f"Error in smarthome endpoint: {e}")
        return jsonify({'error': str(e)}), 500

# Profile route (simplified without authentication for now)
@app.route('/profile')
def profile():
    """User profile - simplified"""
    return jsonify({
        'name': 'Test User',
        'message': 'Profile endpoint working (authentication disabled for testing)'
    })

# OAuth endpoints (simplified)
@app.route('/oauth/token', methods=['POST'])
def access_token():
    """OAuth token endpoint - simplified"""
    print('OAuth token request')
    return jsonify({'version': '0.1.0', 'access_token': 'test_token'})

@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    """OAuth authorize endpoint - simplified"""
    print("OAuth authorize request")
    if request.method == 'GET':
        return jsonify({'message': 'Authorization endpoint - simplified for testing'})
    return jsonify({'authorized': True})

# API endpoint
@app.route('/api/me')
def me():
    """API me endpoint - simplified"""
    return jsonify({'username': 'test_user'})

# IFTTT endpoint
@app.route('/IFTTT', methods=['POST'])
def ifttt():
    """IFTTT webhook endpoint"""
    try:
        # Get the event name from IFTTT
        event_name = request.json.get('event_name', None)
        if event_name is None:
            return jsonify({'errors': [{'message': 'No event name specified'}]}), 400

        # Get the data associated with the event
        data = request.json.get('data', None)
        if data is None:
            return jsonify({'errors': [{'message': 'No data specified'}]}), 400

        # Process the event
        print(f"IFTTT event: {event_name}, data: {data}")
        return jsonify({'data': [{'id': 1, 'name': 'Test'}]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Smart-Google Flask Application")
    print("=" * 50)
    print("Available endpoints:")
    print("  - http://localhost:5000/")
    print("  - http://localhost:5000/health")
    print("  - http://localhost:5000/devices")
    print("  - http://localhost:5000/sync")
    print("  - http://localhost:5000/smarthome (POST)")
    print("  - http://localhost:5000/profile")
    print("  - http://localhost:5000/oauth/token (POST)")
    print("  - http://localhost:5000/oauth/authorize")
    print("  - http://localhost:5000/IFTTT (POST)")
    print("=" * 50)
    
    os.environ['DEBUG'] = 'True'  # While in development
    app.run(host='0.0.0.0', port=5000, debug=False)  # Disable debug mode to avoid reloader issues