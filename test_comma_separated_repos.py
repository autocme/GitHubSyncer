#!/usr/bin/env python3
"""
Test script to verify comma-separated repository names in restart-after labels
"""

import json
from database import get_db_session
from models import Container
from services.docker_service import DockerService

def test_comma_separated_repos():
    """Test that comma-separated repository names work correctly"""
    print("Testing comma-separated repository names in restart-after labels")
    print("=" * 60)
    
    # Get database session
    db = get_db_session()
    docker_service = DockerService(db)
    
    # Test case 1: Single repository name
    print("\n1. Testing single repository name:")
    containers = docker_service.get_containers_for_repository("server-backend")
    print(f"   Found {len(containers)} containers for 'server-backend'")
    
    for container in containers:
        print(f"   - {container.name}: restart_after_pull = '{container.restart_after_pull}'")
    
    # Test case 2: Comma-separated repository names
    print("\n2. Testing comma-separated repository names:")
    
    # First, let's see what containers exist
    all_containers = db.query(Container).all()
    print(f"   Total containers in database: {len(all_containers)}")
    
    for container in all_containers:
        if container.restart_after_pull:
            print(f"   - {container.name}: restart_after_pull = '{container.restart_after_pull}'")
    
    # Test specific repository searches
    test_repos = ["server-backend", "Dnsmain", "frontend-web", "api-service"]
    
    for repo in test_repos:
        containers = docker_service.get_containers_for_repository(repo)
        print(f"\n   Repository '{repo}': {len(containers)} containers")
        for container in containers:
            print(f"     - {container.name}")
    
    # Test case 3: Create a test container with comma-separated repos
    print("\n3. Testing container with multiple repositories:")
    
    # Update an existing container to test comma-separated repos
    test_container = db.query(Container).first()
    if test_container:
        original_restart_after = test_container.restart_after_pull
        test_container.restart_after_pull = "server-backend,Dnsmain,test-repo"
        db.commit()
        
        print(f"   Updated container '{test_container.name}' restart_after_pull to: '{test_container.restart_after_pull}'")
        
        # Test that all three repos find this container
        for repo in ["server-backend", "Dnsmain", "test-repo"]:
            containers = docker_service.get_containers_for_repository(repo)
            found = any(c.name == test_container.name for c in containers)
            status = "✓" if found else "✗"
            print(f"   {status} Repository '{repo}': container found = {found}")
        
        # Restore original value
        test_container.restart_after_pull = original_restart_after
        db.commit()
        print(f"   Restored original restart_after_pull: '{original_restart_after}'")
    
    # Test case 4: Simulate Docker label parsing
    print("\n4. Testing Docker label parsing logic:")
    
    test_labels = [
        "server-backend",
        "server-backend,Dnsmain",
        "frontend-web,api-service,worker-queue",
        "single-repo",
        " spaced-repo , another-repo "  # Test with spaces
    ]
    
    for label in test_labels:
        repo_names = [name.strip() for name in label.split(",")]
        print(f"   Label: '{label}' -> Repos: {repo_names}")
        
        # Test if specific repos would be found
        test_searches = ["server-backend", "Dnsmain", "frontend-web", "spaced-repo"]
        for search_repo in test_searches:
            found = search_repo in repo_names
            if found:
                print(f"     ✓ '{search_repo}' would be found")
    
    print("\n" + "=" * 60)
    print("COMMA-SEPARATED REPOSITORY TEST COMPLETE")
    print("=" * 60)
    
    db.close()

if __name__ == "__main__":
    test_comma_separated_repos()