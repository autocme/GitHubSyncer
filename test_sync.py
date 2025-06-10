#!/usr/bin/env python3
"""
Test script to verify repository sync and container restart functionality
"""

import requests
import time
from datetime import datetime

def test_sync_functionality():
    """Test the complete sync workflow"""
    base_url = "http://localhost:5000"
    
    print("Testing GitHub Sync Server functionality...")
    print(f"Testing at: {base_url}")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    # Test 1: Simulate repository sync
    print("\n1. Testing repository sync...")
    try:
        # Use the webhook endpoint to simulate a GitHub push
        webhook_data = {
            "repository": {
                "name": "server-backend",
                "full_name": "user/server-backend",
                "clone_url": "https://github.com/user/server-backend.git"
            },
            "ref": "refs/heads/main",
            "pusher": {
                "name": "testuser"
            }
        }
        
        response = requests.post(f"{base_url}/webhook/github", 
                               json=webhook_data,
                               headers={"Content-Type": "application/json"})
        
        print(f"Webhook response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Sync result: {result}")
        else:
            print(f"Webhook failed: {response.text}")
            
    except Exception as e:
        print(f"Webhook test failed: {e}")
    
    # Test 2: Check repository status
    print("\n2. Checking repository status...")
    try:
        response = requests.get(f"{base_url}/repositories")
        if response.status_code == 200:
            print("Repository page accessible")
        else:
            print(f"Repository page failed: {response.status_code}")
    except Exception as e:
        print(f"Repository check failed: {e}")
    
    # Test 3: Check container status  
    print("\n3. Checking container status...")
    try:
        response = requests.get(f"{base_url}/containers")
        if response.status_code == 200:
            print("Container page accessible")
        else:
            print(f"Container page failed: {response.status_code}")
    except Exception as e:
        print(f"Container check failed: {e}")
    
    # Test 4: Check logs
    print("\n4. Checking operation logs...")
    try:
        response = requests.get(f"{base_url}/logs")
        if response.status_code == 200:
            print("Logs page accessible")
        else:
            print(f"Logs page failed: {response.status_code}")
    except Exception as e:
        print(f"Logs check failed: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed")

if __name__ == "__main__":
    test_sync_functionality()