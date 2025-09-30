#!/usr/bin/env python3
# Simple test app to identify and fix issues in smart-google

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test all imports and identify missing dependencies"""
    print("=== Testing Imports ===")
    
    import_tests = [
        ('os', 'os'),
        ('json', 'json'),
        ('dotenv', 'python-dotenv'),
        ('requests', 'requests'),
    ]
    
    failed_imports = []
    
    for module, package in import_tests:
        try:
            __import__(module)
            print(f"✓ {module} - OK")
        except ImportError as e:
            print(f"✗ {module} - FAILED: {e}")
            failed_imports.append((module, package))
    
    return failed_imports

def test_environment_variables():
    """Test required environment variables"""
    print("\n=== Testing Environment Variables ===")
    
    required_vars = [
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI', 
        'MQTT_BROKER_URL',
        'MQTT_USERNAME',
        'MQTT_PASSWORD',
        'API_KEY',
        'AGENT_USER_ID',
        'DATABASEURL',
        'SERVICE_ACCOUNT_FILE',
        'PROJECT_ID',
        'PRIVATE_KEY_ID',
        'PRIVATE_KEY',
        'CLIENT_EMAIL',
        'CLIENT_X509_CERT_URL'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✓ {var} - Set")
        else:
            print(f"✗ {var} - Missing")
            missing_vars.append(var)
    
    return missing_vars

def test_service_account_file():
    """Test service account file"""
    print("\n=== Testing Service Account File ===")
    
    service_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service_account_file.json')
    
    if os.path.exists(service_file):
        print(f"✓ Service account file exists: {service_file}")
        try:
            with open(service_file, 'r') as f:
                data = json.load(f)
            
            required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_keys = []
            
            for key in required_keys:
                if key in data and data[key] and data[key] != key.upper().replace('_', ' '):
                    print(f"✓ {key} - Present")
                else:
                    print(f"✗ {key} - Missing or placeholder")
                    missing_keys.append(key)
            
            return missing_keys
            
        except json.JSONDecodeError as e:
            print(f"✗ Service account file is not valid JSON: {e}")
            return ['json_format']
    else:
        print(f"✗ Service account file not found: {service_file}")
        return ['file_missing']

def test_file_structure():
    """Test required files and directories"""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        'app.py',
        'config.py',
        'models.py',
        'auth.py',
        'routes.py',
        'my_oauth.py',
        'notifications.py',
        'action_devices.py',
        'ReportState.py',
        'generate_service_account_file.py'
    ]
    
    required_dirs = [
        'templates',
        'static',
        'tests'
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} - Exists")
        else:
            print(f"✗ {file} - Missing")
            missing_files.append(file)
    
    for dir in required_dirs:
        if os.path.isdir(dir):
            print(f"✓ {dir}/ - Exists")
        else:
            print(f"✗ {dir}/ - Missing")
            missing_dirs.append(dir)
    
    return missing_files, missing_dirs

def analyze_code_issues():
    """Analyze common code issues"""
    print("\n=== Analyzing Code Issues ===")
    
    issues = []
    
    # Check app.py for basic issues
    try:
        with open('app.py', 'r') as f:
            app_content = f.read()
        
        # Check for imports
        if 'from flask import' in app_content:
            print("✓ Flask imports present in app.py")
        else:
            print("✗ Flask imports missing in app.py")
            issues.append("flask_imports")
        
        # Check for config loading
        if 'app.config.from_object' in app_content:
            print("✓ Config loading present")
        else:
            print("✗ Config loading missing")
            issues.append("config_loading")
            
    except FileNotFoundError:
        print("✗ app.py not found")
        issues.append("app_py_missing")
    
    return issues

def main():
    """Main test function"""
    print("Smart-Google Code Analysis and Issue Detection")
    print("=" * 50)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    failed_imports = test_imports()
    missing_env_vars = test_environment_variables()
    missing_service_keys = test_service_account_file()
    missing_files, missing_dirs = test_file_structure()
    code_issues = analyze_code_issues()
    
    print("\n" + "=" * 50)
    print("SUMMARY OF ISSUES")
    print("=" * 50)
    
    if failed_imports:
        print(f"\n❌ Failed Imports ({len(failed_imports)}):")
        for module, package in failed_imports:
            print(f"   - {module} (install: pip install {package})")
    
    if missing_env_vars:
        print(f"\n❌ Missing Environment Variables ({len(missing_env_vars)}):")
        for var in missing_env_vars:
            print(f"   - {var}")
    
    if missing_service_keys:
        print(f"\n❌ Service Account Issues ({len(missing_service_keys)}):")
        for key in missing_service_keys:
            print(f"   - {key}")
    
    if missing_files:
        print(f"\n❌ Missing Files ({len(missing_files)}):")
        for file in missing_files:
            print(f"   - {file}")
    
    if missing_dirs:
        print(f"\n❌ Missing Directories ({len(missing_dirs)}):")
        for dir in missing_dirs:
            print(f"   - {dir}/")
    
    if code_issues:
        print(f"\n❌ Code Issues ({len(code_issues)}):")
        for issue in code_issues:
            print(f"   - {issue}")
    
    total_issues = len(failed_imports) + len(missing_env_vars) + len(missing_service_keys) + len(missing_files) + len(missing_dirs) + len(code_issues)
    
    if total_issues == 0:
        print("\n🎉 No issues found! The application should be ready to run.")
    else:
        print(f"\n📊 Total Issues Found: {total_issues}")
        print("\nRecommendations:")
        print("1. Fix dependency issues first (install missing packages)")
        print("2. Set up environment variables in .env file")
        print("3. Configure proper service account credentials")
        print("4. Ensure all required files are present")
    
    return total_issues

if __name__ == "__main__":
    main()