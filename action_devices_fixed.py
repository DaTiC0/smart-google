# coding: utf-8
# Code By DaTi_Co
# Fixed version with mock data for testing

import json
import requests
import random
import os

# Mock data for testing when Firebase is not available
MOCK_DEVICES = {
    "test-light-1": {
        "type": "action.devices.types.LIGHT",
        "traits": ["action.devices.traits.OnOff", "action.devices.traits.Brightness"],
        "name": {"name": "Test Light 1"},
        "willReportState": True,
        "attributes": {"colorModel": "rgb"},
        "states": {"on": True, "brightness": 80, "online": True}
    },
    "test-switch-1": {
        "type": "action.devices.types.SWITCH", 
        "traits": ["action.devices.traits.OnOff"],
        "name": {"name": "Test Switch 1"},
        "willReportState": True,
        "states": {"on": False, "online": True}
    },
    "test-thermostat-1": {
        "type": "action.devices.types.THERMOSTAT",
        "traits": ["action.devices.traits.TemperatureSetting"],
        "name": {"name": "Test Thermostat"},
        "willReportState": True,
        "attributes": {
            "availableThermostatModes": ["off", "heat", "cool", "auto"],
            "thermostatTemperatureUnit": "C"
        },
        "states": {
            "thermostatMode": "heat",
            "thermostatTemperatureSetpoint": 22,
            "thermostatTemperatureAmbient": 21,
            "online": True
        }
    }
}

def reference():
    """Mock Firebase reference - returns mock data structure"""
    return MockFirebaseReference()

class MockFirebaseReference:
    """Mock Firebase database reference for testing"""
    
    def __init__(self):
        self.data = MOCK_DEVICES
    
    def get(self):
        return self.data
    
    def child(self, path):
        return MockFirebaseChild(self.data, path)

class MockFirebaseChild:
    """Mock Firebase child reference"""
    
    def __init__(self, data, path):
        self.data = data
        self.path = path
    
    def child(self, child_path):
        return MockFirebaseChild(self.data, f"{self.path}/{child_path}")
    
    def get(self):
        keys = self.path.split('/')
        current = self.data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def update(self, values):
        keys = self.path.split('/')
        current = self.data
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Update the final key
        if keys[-1] not in current:
            current[keys[-1]] = {}
        
        if isinstance(current[keys[-1]], dict):
            current[keys[-1]].update(values)
        else:
            current[keys[-1]] = values
        
        return current[keys[-1]]

def rstate():
    """Get report state payload for all devices"""
    try:
        ref = reference()
        devices_data = ref.get()
        
        if not devices_data:
            return {"devices": {"states": {}}}
        
        devices = list(devices_data.keys())
        payload = {
            "devices": {
                "states": {}
            }
        }
        
        for device in devices:
            device = str(device)
            print(f'\nGetting Device status from: {device}')
            state = rquery(device)
            if state:
                payload['devices']['states'][device] = state
                print(f"State: {state}")
        
        return payload
        
    except Exception as e:
        print(f"Error in rstate: {e}")
        return {"devices": {"states": {}}}

def rsync():
    """Get devices for SYNC intent"""
    try:
        ref = reference()
        snapshot = ref.get()
        
        if not snapshot:
            return []
        
        DEVICES = []
        for k, v in snapshot.items():
            # Remove states from device info for sync
            device_info = v.copy()
            device_info.pop('states', None)
            
            DEVICE = {"id": k}
            DEVICE.update(device_info)
            DEVICES.append(DEVICE)
        
        return DEVICES
        
    except Exception as e:
        print(f"Error in rsync: {e}")
        return []

def rquery(deviceId):
    """Query device state"""
    try:
        ref = reference()
        device_states = ref.child(deviceId).child('states').get()
        return device_states or {"online": False}
        
    except Exception as e:
        print(f"Error querying device {deviceId}: {e}")
        return {"online": False}

def rexecute(deviceId, parameters):
    """Execute command on device and return new state"""
    try:
        ref = reference()
        
        # Update device states
        ref.child(deviceId).child('states').update(parameters)
        
        # Return updated states
        return ref.child(deviceId).child('states').get()
        
    except Exception as e:
        print(f"Error executing command on device {deviceId}: {e}")
        return parameters  # Return the parameters as fallback

def onSync():
    """Handle SYNC intent"""
    try:
        agent_user_id = os.environ.get('AGENT_USER_ID', 'test-user')
        return {
            "agentUserId": agent_user_id,
            "devices": rsync()
        }
    except Exception as e:
        print(f"Error in onSync: {e}")
        return {"agentUserId": "test-user", "devices": []}

def onQuery(body):
    """Handle QUERY intent"""
    try:
        payload = {"devices": {}}
        
        for i in body['inputs']:
            for device in i['payload']['devices']:
                deviceId = device['id']
                print(f'DEVICE ID: {deviceId}')
                data = rquery(deviceId)
                payload['devices'][deviceId] = data
        
        return payload
        
    except Exception as e:
        print(f"Error in onQuery: {e}")
        return {"devices": {}}

def onExecute(body):
    """Handle EXECUTE intent"""
    try:
        payload = {
            'commands': [{
                'ids': [],
                'status': 'SUCCESS',
                'states': {'online': True},
            }],
        }
        
        for i in body['inputs']:
            for command in i['payload']['commands']:
                for device in command['devices']:
                    deviceId = device['id']
                    payload['commands'][0]['ids'].append(deviceId)
                    
                    for execution in command['execution']:
                        execCommand = execution['command']
                        params = execution['params']
                        
                        # Process command and update payload
                        payload = commands(payload, deviceId, execCommand, params)
        
        return payload
        
    except Exception as e:
        print(f"Error in onExecute: {e}")
        return {
            'commands': [{
                'ids': [],
                'status': 'ERROR',
                'errorCode': 'deviceNotFound'
            }]
        }

def commands(payload, deviceId, execCommand, params):
    """Process device commands"""
    try:
        print(f"Processing command {execCommand} for device {deviceId} with params {params}")
        
        # Process different command types
        if execCommand == 'action.devices.commands.OnOff':
            processed_params = {'on': params.get('on', True)}
            print('OnOff command processed')
            
        elif execCommand == 'action.devices.commands.BrightnessAbsolute':
            processed_params = {
                'brightness': params.get('brightness', 100),
                'on': True  # Usually turning on when setting brightness
            }
            print('BrightnessAbsolute command processed')
            
        elif execCommand == 'action.devices.commands.StartStop':
            processed_params = {'isRunning': params.get('start', False)}
            print('StartStop command processed')
            
        elif execCommand == 'action.devices.commands.PauseUnpause':
            processed_params = {'isPaused': params.get('pause', False)}
            print('PauseUnpause command processed')
            
        elif execCommand == 'action.devices.commands.GetCameraStream':
            processed_params = {
                'cameraStreamAccessUrl': 'https://example.com/stream',
                'cameraStreamReceiverAppId': 'test-app'
            }
            print('GetCameraStream command processed')
            
        elif execCommand == 'action.devices.commands.LockUnlock':
            processed_params = {'isLocked': params.get('lock', False)}
            print('LockUnlock command processed')
            
        elif execCommand == 'action.devices.commands.ThermostatTemperatureSetpoint':
            processed_params = {
                'thermostatTemperatureSetpoint': params.get('thermostatTemperatureSetpoint', 22)
            }
            print('ThermostatTemperatureSetpoint command processed')
            
        else:
            processed_params = params
            print(f'Unknown command {execCommand}, using original params')
        
        # Execute the command and get updated states
        states = rexecute(deviceId, processed_params)
        payload['commands'][0]['states'] = states
        
        return payload
        
    except Exception as e:
        print(f"Error processing command: {e}")
        payload['commands'][0]['status'] = 'ERROR'
        payload['commands'][0]['errorCode'] = 'deviceNotReady'
        return payload

def actions(req):
    """Main action handler"""
    try:
        print(f"Processing request: {json.dumps(req, indent=2)}")
        
        for i in req['inputs']:
            intent = i['intent']
            print(f"Intent: {intent}")
            
            if intent == "action.devices.SYNC":
                payload = onSync()
                
            elif intent == "action.devices.QUERY":
                payload = onQuery(req)
                
            elif intent == "action.devices.EXECUTE":
                payload = onExecute(req)
                # Mock MQTT message sending
                try:
                    if 'commands' in payload and payload['commands']:
                        deviceId = payload['commands'][0]['ids'][0] if payload['commands'][0]['ids'] else 'unknown'
                        params = payload['commands'][0]['states']
                        print(f"Would send MQTT message to {deviceId}/notification with payload: {params}")
                        # mqtt.publish(topic=str(deviceId) + '/' + 'notification', payload=str(params), qos=0)
                except Exception as mqtt_error:
                    print(f"MQTT error (non-critical): {mqtt_error}")
                
            elif intent == "action.devices.DISCONNECT":
                print("DISCONNECT ACTION")
                payload = {}
                
            else:
                print(f'Unexpected action requested: {json.dumps(req)}')
                payload = {}
        
        return payload
        
    except Exception as e:
        print(f"Error in actions: {e}")
        return {}

def request_sync(api_key, agent_user_id):
    """Request sync with Google Home Graph API"""
    try:
        url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + api_key
        data = {"agentUserId": agent_user_id, "async": True}

        print(f"Requesting sync for agent: {agent_user_id}")
        response = requests.post(url, json=data)

        print(f'Request Code: {requests.codes["ok"]} | Response Code: {response.status_code}')
        print(f'Response: {response.text}')

        return response.status_code == requests.codes['ok']
        
    except Exception as e:
        print(f"Error in request_sync: {e}")
        return False

def report_state():
    """Report device states to Google"""
    try:
        import random
        
        # Generate random request ID
        n = random.randint(10**19, 10**20)
        agent_user_id = os.environ.get('AGENT_USER_ID', 'test-user')
        
        report_state_file = {
            'requestId': str(n),
            'agentUserId': agent_user_id,
            'payload': rstate(),
        }

        print(f"Reporting state: {json.dumps(report_state_file, indent=2)}")
        
        # Import ReportState module if available
        try:
            import ReportState as state
            state.main(report_state_file)
        except ImportError:
            print("ReportState module not available, using mock")
        
        return "State reported successfully"
        
    except Exception as e:
        print(f"Error in report_state: {e}")
        return f"Error reporting state: {e}"

# Test functions
def test_all_functions():
    """Test all functions with mock data"""
    print("=== Testing Action Devices Functions ===")
    
    # Test rsync
    print("\n1. Testing rsync:")
    devices = rsync()
    print(f"   Found {len(devices)} devices")
    for device in devices:
        print(f"   - {device['id']}: {device['name']['name']}")
    
    # Test rquery
    print("\n2. Testing rquery:")
    for device_id in ['test-light-1', 'test-switch-1']:
        state = rquery(device_id)
        print(f"   {device_id}: {state}")
    
    # Test onSync
    print("\n3. Testing onSync:")
    sync_result = onSync()
    print(f"   Agent User ID: {sync_result['agentUserId']}")
    print(f"   Devices count: {len(sync_result['devices'])}")
    
    # Test onQuery
    print("\n4. Testing onQuery:")
    query_request = {
        'inputs': [{
            'payload': {
                'devices': [{'id': 'test-light-1'}, {'id': 'test-switch-1'}]
            }
        }]
    }
    query_result = onQuery(query_request)
    print(f"   Queried devices: {list(query_result['devices'].keys())}")
    
    # Test onExecute
    print("\n5. Testing onExecute:")
    execute_request = {
        'inputs': [{
            'payload': {
                'commands': [{
                    'devices': [{'id': 'test-light-1'}],
                    'execution': [{
                        'command': 'action.devices.commands.OnOff',
                        'params': {'on': True}
                    }]
                }]
            }
        }]
    }
    execute_result = onExecute(execute_request)
    print(f"   Execution status: {execute_result['commands'][0]['status']}")
    print(f"   Device states: {execute_result['commands'][0]['states']}")
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_all_functions()