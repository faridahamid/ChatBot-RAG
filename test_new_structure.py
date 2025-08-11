#!/usr/bin/env python3
"""
Test script to verify the new frontend/backend structure is working correctly.
"""

import os
import requests
import time

# Configuration
BASE_URL = "http://localhost:8000"

def test_file_structure():
    """Test if the new folder structure exists."""
    print("🔍 Testing file structure...")
    
    required_dirs = [
        "Frontend",
        "Frontend/css",
        "Frontend/js", 
        "Frontend/pages",
        "Backend"
    ]
    
    required_files = [
        "Frontend/css/main.css",
        "Frontend/js/common.js",
        "Frontend/js/dashboard.js",
        "Frontend/js/login.js",
        "Frontend/js/welcome.js",
        "Frontend/pages/welcome.html",
        "Frontend/pages/login.html",
        "Frontend/pages/dashboard.html",
        "Frontend/pages/admin_register.html",
        "Frontend/pages/admin_upload.html",
        "Frontend/pages/admin_users.html",
        "Backend/main.py",
        "Backend/admin_auth.py",
        "Backend/database.py",
        "Backend/models.py",
        "Backend/schemas.py"
    ]
    
    # Check directories
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Directory missing: {dir_path}")
            return False
    
    # Check files
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ File missing: {file_path}")
            return False
    
    print("✅ All required files and directories exist!")
    return True

def test_server_health():
    """Test if the server is running and accessible."""
    print("\n🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and accessible")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing server health: {e}")
        return False

def test_frontend_routes():
    """Test if frontend routes are accessible."""
    print("\n🔍 Testing frontend routes...")
    
    routes = [
        ("/", "Welcome Page"),
        ("/login", "Login Page"),
        ("/admin-register", "Admin Registration Page"),
        ("/dashboard", "Dashboard Page"),
        ("/admin-upload", "Admin Upload Page"),
        ("/admin-users", "Admin Users Page")
    ]
    
    for path, name in routes:
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is accessible")
            else:
                print(f"❌ {name} returned status code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error accessing {name}: {e}")

def test_static_files():
    """Test if static files (CSS/JS) are accessible."""
    print("\n🔍 Testing static files...")
    
    static_files = [
        ("/css/main.css", "Main CSS"),
        ("/js/common.js", "Common JavaScript"),
        ("/js/dashboard.js", "Dashboard JavaScript"),
        ("/js/login.js", "Login JavaScript"),
        ("/js/welcome.js", "Welcome JavaScript")
    ]
    
    for path, name in static_files:
        try:
            response = requests.get(f"{BASE_URL}{path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is accessible")
            else:
                print(f"❌ {name} returned status code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error accessing {name}: {e}")

def main():
    """Main test function."""
    print("🚀 Testing New Frontend/Backend Structure")
    print("=" * 50)
    
    # Test file structure
    if not test_file_structure():
        print("\n❌ File structure test failed. Exiting tests.")
        return
    
    # Test server health
    if not test_server_health():
        print("\n❌ Server health check failed. Exiting tests.")
        return
    
    # Test frontend routes
    test_frontend_routes()
    
    # Test static files
    test_static_files()
    
    print("\n" + "=" * 50)
    print("🏁 Structure tests completed!")
    
    print("\n💡 To start using the new structure:")
    print("1. Start the server: cd Backend && uvicorn main:app --reload")
    print("2. Open http://localhost:8000/ in your browser")
    print("3. Navigate through the pages to test functionality")

if __name__ == "__main__":
    main()
