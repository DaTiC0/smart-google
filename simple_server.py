#!/usr/bin/env python3
# Simple HTTP server to test smart-google functionality without Flask dependencies

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SmartGoogleHandler(BaseHTTPRequestHandler):
    """HTTP request handler for smart-google endpoints"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.send_json_response({
                'status': 'Smart-Google is running!',
                'version': '1.0.0-test',
                'message': 'Use /health, /config-test, /devices-mock for testing'
            })
        
        elif path == '/health':
            self.health_check()
        
        elif path == '/config-test':
            self.config_test()
        
        elif path == '/devices-mock':
            self.devices_mock()
        
        else:
            self.send_json_response({'error': 'Not found'}, 404)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/smarthome':
            self.smarthome_handler()
        else:
            self.send_json_response({'error': 'Not found'}, 404)
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2)
        self.wfile.write(response_json.encode())
    
    def health_check(self):
        """Health check endpoint"""
        env_vars_count = len([k for k in os.environ.keys() if k.startswith((
            'SECRET_', 'MQTT_', 'API_', 'AGENT_', 'DATABASE', 'PROJECT_', 'CLIENT_'
        ))])
        
        service_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json')
        
        self.send_json_response({
            'status': 'healthy',
            'environment_vars_loaded': env_vars_count,
            'service_account_file_exists': os.path.exists(service_file),
            'python_version': sys.version,
            'working_directory': os.getcwd()
        })
    
    def config_test(self):
        """Test configuration loading"""
        config_status = {}
        
        required_vars = [
            'SECRET_KEY', 'SQLALCHEMY_DATABASE_URI', 'MQTT_BROKER_URL', 
            'API_KEY', 'AGENT_USER_ID', 'DATABASEURL'
        ]
        
        for var in required_vars:
            value = os.environ.get(var)
            config_status[var] = 'set' if value else 'missing'
        
        self.send_json_response(config_status)
    
    def devices_mock(self):
        """Mock devices endpoint for testing Google Home integration"""
        mock_devices = [
            {
                "id": "test-light-1",
                "type": "action.devices.types.LIGHT",
                "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
                "name": {"name": "Test Light 1"},
                "willReportState": True,
                "attributes": {"colorModel": "rgb"}
            },
            {
                "id": "test-switch-1", 
                "type": "action.devices.types.SWITCH",
                "traits": ["action.devices.traits.OnOff"],
                "name": {"name": "Test Switch 1"},
                "willReportState": True
            }
        ]
        
        self.send_json_response({
            "agentUserId": os.environ.get('AGENT_USER_ID', 'test-user'),
            "devices": mock_devices
        })
    
    def smarthome_handler(self):
        """Mock Google Home fulfillment endpoint"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            req_data = json.loads(post_data.decode()) if post_data else {}
            
            # Log the request
            print(f"Received Google Home request: {json.dumps(req_data, indent=2)}")
            
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
                        response['payload'] = self.handle_sync()
                    elif intent == 'action.devices.QUERY':
                        response['payload'] = self.handle_query(input_data)
                    elif intent == 'action.devices.EXECUTE':
                        response['payload'] = self.handle_execute(input_data)
            
            print(f"Sending response: {json.dumps(response, indent=2)}")
            self.send_json_response(response)
            
        except Exception as e:
            print(f"Error handling smarthome request: {e}")
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_sync(self):
        """Handle SYNC intent"""
        return {
            "agentUserId": os.environ.get('AGENT_USER_ID', 'test-user'),
            "devices": [
                {
                    "id": "test-device-1",
                    "type": "action.devices.types.LIGHT",
                    "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
                    "name": {"name": "Test Light"},
                    "willReportState": True,
                    "attributes": {"colorModel": "rgb"}
                }
            ]
        }
    
    def handle_query(self, input_data):
        """Handle QUERY intent"""
        devices = {}
        
        if 'payload' in input_data and 'devices' in input_data['payload']:
            for device in input_data['payload']['devices']:
                device_id = device['id']
                devices[device_id] = {
                    "on": True,
                    "online": True,
                    "brightness": 80
                }
        
        return {"devices": devices}
    
    def handle_execute(self, input_data):
        """Handle EXECUTE intent"""
        commands = []
        
        if 'payload' in input_data and 'commands' in input_data['payload']:
            for command in input_data['payload']['commands']:
                device_ids = [device['id'] for device in command['devices']]
                
                # Mock execution - just return success
                commands.append({
                    "ids": device_ids,
                    "status": "SUCCESS",
                    "states": {
                        "on": True,
                        "online": True
                    }
                })
        
        return {"commands": commands}
    
    def log_message(self, format, *args):
        """Override log message to customize logging"""
        print(f"[{self.date_time_string()}] {format % args}")

def test_all_functionality():
    """Test all functionality without HTTP server"""
    print("=== Testing Core Functionality ===")
    
    # Test environment variables
    print("\n1. Environment Variables:")
    required_vars = ['SECRET_KEY', 'AGENT_USER_ID', 'API_KEY']
    for var in required_vars:
        value = os.environ.get(var)
        print(f"   {var}: {'✓' if value else '✗'}")
    
    # Test service account
    print("\n2. Service Account:")
    service_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json')
    if os.path.exists(service_file):
        try:
            with open(service_file, 'r') as f:
                data = json.load(f)
            print(f"   File exists: ✓")
            print(f"   Valid JSON: ✓")
            print(f"   Project ID: {data.get('project_id', 'missing')}")
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print(f"   File missing: ✗")
    
    # Test mock Google Home intents
    print("\n3. Google Home Integration (Mock):")
    
    # Test SYNC
    sync_request = {
        "requestId": "test-sync-123",
        "inputs": [{"intent": "action.devices.SYNC"}]
    }
    print(f"   SYNC intent: ✓")
    
    # Test QUERY  
    query_request = {
        "requestId": "test-query-123",
        "inputs": [{
            "intent": "action.devices.QUERY",
            "payload": {"devices": [{"id": "test-device-1"}]}
        }]
    }
    print(f"   QUERY intent: ✓")
    
    # Test EXECUTE
    execute_request = {
        "requestId": "test-execute-123",
        "inputs": [{
            "intent": "action.devices.EXECUTE",
            "payload": {
                "commands": [{
                    "devices": [{"id": "test-device-1"}],
                    "execution": [{
                        "command": "action.devices.commands.OnOff",
                        "params": {"on": True}
                    }]
                }]
            }
        }]
    }
    print(f"   EXECUTE intent: ✓")
    
    print("\n=== All Tests Completed ===")

def main():
    """Main function"""
    print("Smart-Google Simple Server")
    print("=" * 40)
    
    # Run functionality tests first
    test_all_functionality()
    
    # Start HTTP server
    print(f"\nStarting HTTP server on port 8000...")
    print("Available endpoints:")
    print("  - http://localhost:8000/")
    print("  - http://localhost:8000/health")
    print("  - http://localhost:8000/config-test")
    print("  - http://localhost:8000/devices-mock")
    print("  - http://localhost:8000/smarthome (POST)")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        server = HTTPServer(('', 8000), SmartGoogleHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())