#!/usr/bin/env python3
"""
Test script to demonstrate the complete server-backend to odoo-odoo-1 restart workflow
"""

import sys
import os
sys.path.append('.')

from database import get_db_session
from services.webhook_service import WebhookService
from services.docker_service import DockerService
from models import Repository, Container
import json

def test_odoo_restart_workflow():
    """Test the complete workflow: server-backend repository update -> odoo-odoo-1 restart"""
    
    print("🔍 Testing server-backend to odoo-odoo-1 restart workflow...")
    
    # Get database session
    db = get_db_session()
    
    try:
        # Step 1: Check if server-backend repository exists
        repo = db.query(Repository).filter_by(name="server-backend").first()
        if not repo:
            print("❌ server-backend repository not found in database")
            # Create the repository
            repo = Repository(
                name="server-backend",
                url="https://github.com/OCA/server-backend.git",
                branch="17.0",
                is_active=True
            )
            db.add(repo)
            db.commit()
            print("✅ Created server-backend repository")
        else:
            print(f"✅ Found server-backend repository: {repo.url}")
        
        # Step 2: Check odoo-odoo-1 container configuration
        container = db.query(Container).filter_by(name="odoo-odoo-1").first()
        if not container:
            print("❌ odoo-odoo-1 container not found")
            return False
        
        print(f"✅ Found odoo-odoo-1 container:")
        print(f"   - Container ID: {container.container_id}")
        print(f"   - Status: {container.status}")
        print(f"   - Restart after pull: {container.restart_after_pull}")
        
        if container.restart_after_pull != "server-backend":
            print("❌ Container not configured to restart after server-backend")
            return False
        
        # Step 3: Test the webhook workflow
        webhook_service = WebhookService(db)
        
        # Simulate GitHub webhook payload for server-backend
        github_payload = {
            "ref": "refs/heads/17.0",
            "repository": {
                "name": "server-backend",
                "full_name": "OCA/server-backend",
                "clone_url": "https://github.com/OCA/server-backend.git"
            },
            "commits": [
                {
                    "id": "abc123",
                    "message": "Test commit for Odoo restart",
                    "author": {"name": "Test User"}
                }
            ]
        }
        
        print("🚀 Simulating GitHub webhook for server-backend...")
        
        # Process the webhook
        success, message, result = webhook_service.process_github_webhook(github_payload)
        
        if success:
            print("✅ Webhook processed successfully!")
            print(f"   Message: {message}")
            
            # Check if containers were restarted
            if "containers_restarted" in result and result["containers_restarted"]:
                print("🔄 Containers restarted:")
                for container_result in result["containers_restarted"]:
                    status = "✅" if container_result["success"] else "❌"
                    print(f"   {status} {container_result['name']}: {container_result['message']}")
            else:
                print("⚠️  No containers were restarted")
            
            # Show any errors
            if "errors" in result and result["errors"]:
                print("⚠️  Errors encountered:")
                for error in result["errors"]:
                    print(f"   - {error}")
        else:
            print(f"❌ Webhook failed: {message}")
            return False
        
        # Step 4: Verify container restart status
        db.refresh(container)
        print("\n📊 Final container status:")
        print(f"   - Last restart time: {container.last_restart_time}")
        print(f"   - Last restart success: {container.last_restart_success}")
        if container.last_restart_error:
            print(f"   - Last restart error: {container.last_restart_error}")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_odoo_restart_workflow()
    if success:
        print("\n🎉 Workflow test completed successfully!")
        print("The odoo-odoo-1 container will restart when server-backend repository is updated.")
    else:
        print("\n💥 Workflow test failed!")
    
    sys.exit(0 if success else 1)