#!/usr/bin/env python3
# Working Flask app for smart-google
import os
import sys

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Apply Flask compatibility patch
try:
    import flask_patch
except ImportError:
    pass

# Use environment variables
from dotenv import load_dotenv
load_dotenv()

def create_app():
    """Create Flask app with error handling"""
    try:
        from flask import Flask, jsonify, request, render_template
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        print("Using simple HTTP server instead...")
        return None
    
    app = Flask(__name__, template_folder='templates')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = True
    app.config['AGENT_USER_ID'] = os.environ.get('AGENT_USER_ID', 'test-user')
    app.config['API_KEY'] = os.environ.get('API_KEY', 'test-api-key')
    
    # Import fixed modules
    try:
        from action_devices_fixed import actions, onSync, report_state, request_sync
        print("✓ Action devices imported")
    except ImportError as e:
        print(f"✗ Action devices import failed: {e}")
        return None
    
    # Routes
    @app.route('/')
    def index():
        return jsonify({
            'status': 'Smart-Google Flask App Running!',
            'version': '1.0.0-fixed',
            'agent_user_id': app.config['AGENT_USER_ID']
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'flask_version': 'working',
            'config_loaded': True
        })
    
    @app.route('/sync')
    def sync_devices():
        try:
            result = request_sync(app.config['API_KEY'], app.config['AGENT_USER_ID'])
            report_state()
            return jsonify({'sync_requested': True, 'success': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/devices')
    def devices():
        try:
            dev_req = onSync()
            return jsonify(dev_req)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/smarthome', methods=['POST'])
    def smarthome():
        try:
            req_data = request.get_json(silent=True, force=True)
            print(f"Incoming request: {req_data}")
            
            result = {
                'requestId': req_data.get('requestId', 'unknown'),
                'payload': actions(req_data),
            }
            
            print(f"Response: {result}")
            return jsonify(result)
            
        except Exception as e:
            print(f"Error in smarthome: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

def main():
    """Main function"""
    print("Smart-Google Working Flask App")
    print("=" * 40)
    
    app = create_app()
    
    if app:
        print("✓ Flask app created successfully!")
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        except Exception as e:
            print(f"Error running Flask app: {e}")
            print("Falling back to simple server...")
            # Import and run simple server
            from simple_server import main as simple_main
            return simple_main()
    else:
        print("Flask not available, using simple server...")
        from simple_server import main as simple_main
        return simple_main()

if __name__ == "__main__":
    main()
