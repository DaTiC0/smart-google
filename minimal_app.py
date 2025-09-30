#!/usr/bin/env python3
# Minimal version of smart-google app for testing and fixing issues

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_minimal_flask_app():
    """Create a minimal Flask app without dependency conflicts"""
    print("Creating minimal Flask app...")
    
    # Try to import Flask with fallback handling
    try:
        # Apply compatibility patch
        import flask_patch
        from flask import Flask, jsonify, request, render_template_string
        print("✓ Flask imported successfully with patch")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return None
    
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test-secret-key')
    app.config['DEBUG'] = True
    
    # Basic routes for testing
    @app.route('/')
    def index():
        return jsonify({
            'status': 'Smart-Google is running!',
            'version': '1.0.0-test',
            'endpoints': [
                '/',
                '/health',
                '/config-test',
                '/devices-mock'
            ]
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'environment_vars_loaded': len([k for k in os.environ.keys() if k.startswith(('SECRET_', 'MQTT_', 'API_', 'AGENT_', 'DATABASE', 'PROJECT_', 'CLIENT_'))]),
            'service_account_file_exists': os.path.exists(os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json'))
        })
    
    @app.route('/config-test')
    def config_test():
        """Test configuration loading"""
        config_status = {}
        
        # Test environment variables
        required_vars = ['SECRET_KEY', 'SQLALCHEMY_DATABASE_URI', 'MQTT_BROKER_URL', 'API_KEY', 'AGENT_USER_ID']
        for var in required_vars:
            config_status[var] = 'set' if os.environ.get(var) else 'missing'
        
        return jsonify(config_status)
    
    @app.route('/devices-mock')
    def devices_mock():
        """Mock devices endpoint for testing Google Home integration"""
        mock_devices = [
            {
                "id": "test-light-1",
                "type": "action.devices.types.LIGHT",
                "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
                "name": {
                    "name": "Test Light 1"
                },
                "willReportState": True,
                "attributes": {
                    "colorModel": "rgb"
                }
            },
            {
                "id": "test-switch-1", 
                "type": "action.devices.types.SWITCH",
                "traits": ["action.devices.traits.OnOff"],
                "name": {
                    "name": "Test Switch 1"
                },
                "willReportState": True
            }
        ]
        
        return jsonify({
            "agentUserId": os.environ.get('AGENT_USER_ID', 'test-user'),
            "devices": mock_devices
        })
    
    @app.route('/smarthome', methods=['POST'])
    def smarthome_mock():
        """Mock Google Home fulfillment endpoint"""
        req_data = request.get_json()
        
        # Basic response structure
        response = {
            'requestId': req_data.get('requestId', 'test-request-id'),
            'payload': {}
        }
        
        # Handle different intents
        if req_data and 'inputs' in req_data:
            for input_data in req_data['inputs']:
                intent = input_data.get('intent')
                
                if intent == 'action.devices.SYNC':
                    response['payload'] = {
                        "agentUserId": os.environ.get('AGENT_USER_ID', 'test-user'),
                        "devices": [
                            {
                                "id": "test-device-1",
                                "type": "action.devices.types.LIGHT",
                                "traits": ["action.devices.traits.OnOff"],
                                "name": {"name": "Test Light"},
                                "willReportState": True
                            }
                        ]
                    }
                elif intent == 'action.devices.QUERY':
                    response['payload'] = {
                        "devices": {
                            "test-device-1": {
                                "on": True,
                                "online": True
                            }
                        }
                    }
                elif intent == 'action.devices.EXECUTE':
                    response['payload'] = {
                        "commands": [{
                            "ids": ["test-device-1"],
                            "status": "SUCCESS",
                            "states": {
                                "on": True,
                                "online": True
                            }
                        }]
                    }
        
        return jsonify(response)
    
    return app

def test_database_mock():
    """Test database functionality with mock data"""
    print("\n=== Testing Database Mock ===")
    
    # Mock database operations
    mock_users = [
        {"id": 1, "email": "test@example.com", "name": "Test User"}
    ]
    
    mock_devices = [
        {"id": "test-device-1", "name": "Test Light", "type": "light", "state": {"on": True}}
    ]
    
    print("✓ Mock users:", len(mock_users))
    print("✓ Mock devices:", len(mock_devices))
    
    return mock_users, mock_devices

def test_service_account_mock():
    """Test service account functionality with mock"""
    print("\n=== Testing Service Account Mock ===")
    
    service_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json')
    
    if os.path.exists(service_file):
        try:
            with open(service_file, 'r') as f:
                data = json.load(f)
            print("✓ Service account file loaded")
            
            # Create mock credentials for testing
            mock_credentials = {
                'project_id': data.get('project_id', 'test-project'),
                'client_email': data.get('client_email', 'test@test-project.iam.gserviceaccount.com')
            }
            print("✓ Mock credentials created")
            return mock_credentials
            
        except Exception as e:
            print(f"✗ Error loading service account: {e}")
            return None
    else:
        print("✗ Service account file not found")
        return None

def main():
    """Main test function"""
    print("Smart-Google Minimal App Test")
    print("=" * 40)
    
    # Test components
    test_database_mock()
    test_service_account_mock()
    
    # Create and test Flask app
    app = create_minimal_flask_app()
    
    if app:
        print("\n✓ Minimal Flask app created successfully!")
        print("\nStarting test server...")
        print("Available endpoints:")
        print("  - http://localhost:5000/")
        print("  - http://localhost:5000/health")
        print("  - http://localhost:5000/config-test")
        print("  - http://localhost:5000/devices-mock")
        print("  - http://localhost:5000/smarthome (POST)")
        
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\n✗ Error running app: {e}")
    else:
        print("\n✗ Failed to create Flask app")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())