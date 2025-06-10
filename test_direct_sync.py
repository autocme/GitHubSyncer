#!/usr/bin/env python3
"""
Direct test of sync functionality bypassing web interface
"""

import sys
import os
sys.path.append('.')

from database import get_db_session
from models import Repository, Container, User
from services.webhook_service import WebhookService
from services.docker_service import DockerService
from services.auth_service import AuthService
import asyncio
from datetime import datetime

def setup_test_data():
    """Setup test data for sync testing"""
    db = get_db_session()
    
    # Create admin user if not exists
    auth_service = AuthService(db)
    if not auth_service.is_setup_complete():
        success, message = auth_service.create_user("admin", "admin123", "admin@example.com")
        if success:
            auth_service.complete_setup()
            print(f"✓ Created admin user: {message}")
        else:
            print(f"✗ Failed to create admin user: {message}")
    
    # Create test repository if not exists
    existing_repo = db.query(Repository).filter(Repository.name == "server-backend").first()
    if not existing_repo:
        test_repo = Repository(
            name="server-backend",
            url="https://github.com/example/server-backend.git",
            branch="main",
            local_path="/repos/server-backend",
            is_active=True
        )
        db.add(test_repo)
        print("✓ Created test repository: server-backend")
    else:
        print("✓ Test repository already exists: server-backend")
    
    # Ensure containers are discovered
    docker_service = DockerService(db)
    containers = docker_service.discover_containers()
    print(f"✓ Discovered {len(containers)} containers")
    
    # Check for containers with restart label
    restart_containers = db.query(Container).filter(Container.restart_after_pull == "server-backend").all()
    print(f"✓ Found {len(restart_containers)} containers with server-backend restart label")
    
    for container in restart_containers:
        print(f"  - {container.name} (ID: {container.container_id})")
    
    db.commit()
    db.close()
    
    return len(restart_containers) > 0

async def test_sync_workflow():
    """Test the complete sync workflow"""
    print("=" * 60)
    print("Testing GitHub Sync Server - Direct Sync Test")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    # Setup test data
    has_containers = setup_test_data()
    
    if not has_containers:
        print("\n⚠ No containers with 'server-backend' restart label found")
        print("This is expected in a read-only environment")
    
    # Test webhook processing
    print("\n1. Testing webhook processing...")
    
    db = get_db_session()
    webhook_service = WebhookService(db)
    
    test_payload = {
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
    
    try:
        result = await webhook_service.process_github_webhook(test_payload)
        print(f"✓ Webhook result: {result}")
        
        if result.get("success"):
            print("✓ Repository sync completed successfully")
            print(f"✓ Pull message: {result.get('pull_message', 'N/A')}")
            
            containers_restarted = result.get('containers_restarted', [])
            print(f"✓ Containers processed: {len(containers_restarted)}")
            
            for container in containers_restarted:
                status = "✓" if container.get('success') else "✗"
                print(f"  {status} {container.get('name')}: {container.get('message')}")
        else:
            print(f"✗ Webhook failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Webhook processing failed: {str(e)}")
    
    # Check repository status after sync
    print("\n2. Checking repository status...")
    
    repo = db.query(Repository).filter(Repository.name == "server-backend").first()
    if repo:
        print(f"✓ Repository found: {repo.name}")
        print(f"✓ Last pull success: {repo.last_pull_success}")
        print(f"✓ Last pull time: {repo.last_pull_time}")
        if repo.last_pull_error:
            print(f"✗ Last pull error: {repo.last_pull_error}")
    else:
        print("✗ Repository not found")
    
    db.close()
    print("\n" + "=" * 60)
    print("Direct sync test completed")

if __name__ == "__main__":
    asyncio.run(test_sync_workflow())