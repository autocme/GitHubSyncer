#!/usr/bin/env python3
"""
Test the simplified Docker service using your exact working pattern
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.simple_docker_service import SimpleDockerService

def test_simple_docker_pattern():
    """Test Docker restart using your exact working pattern"""
    print("=== Testing Simple Docker Pattern (Your Working Example) ===")
    
    # Initialize simple docker service
    docker_service = SimpleDockerService()
    
    print(f"Docker available: {docker_service.docker_available}")
    
    # Test restart using your exact pattern
    test_repo = "server-backend"
    success_count, results = docker_service.restart_containers_by_label(test_repo)
    
    print(f"\nRepository: {test_repo}")
    print(f"Success count: {success_count}")
    print("Results:")
    for result in results:
        print(f"  - {result}")
    
    # Test getting containers with label
    containers = docker_service.get_containers_with_label(test_repo)
    print(f"\nContainers found with restart-after={test_repo}: {len(containers)}")
    for container in containers:
        print(f"  - {container.name} (ID: {container.id[:12]})")
    
    print("\n=== Test Complete ===")
    print("This uses the exact same pattern as your working Flask example:")
    print("1. client = docker.from_env()")
    print("2. containers = client.containers.list(filters={'label': label})")
    print("3. container.restart()")

if __name__ == "__main__":
    test_simple_docker_pattern()