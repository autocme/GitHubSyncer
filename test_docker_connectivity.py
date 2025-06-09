#!/usr/bin/env python3
"""
Test Docker connectivity and permissions for GitHub Sync Server
"""
import docker
import os
import stat
import grp
import pwd

def test_docker_connectivity():
    print("=== Docker Connectivity Test ===")
    
    # Check if Docker socket exists
    socket_path = "/var/run/docker.sock"
    if os.path.exists(socket_path):
        print(f"✓ Docker socket exists: {socket_path}")
        
        # Check permissions
        stat_info = os.stat(socket_path)
        print(f"Socket permissions: {oct(stat_info.st_mode)[-3:]}")
        print(f"Socket owner: {pwd.getpwuid(stat_info.st_uid).pw_name}")
        print(f"Socket group: {grp.getgrgid(stat_info.st_gid).gr_name}")
    else:
        print(f"✗ Docker socket not found: {socket_path}")
        return False
    
    # Check current user groups
    print(f"\nCurrent user: {pwd.getpwuid(os.getuid()).pw_name}")
    print(f"User groups: {[grp.getgrgid(g).gr_name for g in os.getgroups()]}")
    
    # Test Docker client connection
    try:
        client = docker.from_env()
        print("\n✓ Docker client created successfully")
        
        # Test ping
        client.ping()
        print("✓ Docker daemon ping successful")
        
        # List containers
        containers = client.containers.list(all=True)
        print(f"✓ Found {len(containers)} containers")
        
        for container in containers:
            labels = container.labels or {}
            restart_after = labels.get("restart-after", "")
            print(f"  - {container.name}: {container.status} (restart-after: {restart_after or 'none'})")
        
        return True
        
    except Exception as e:
        print(f"✗ Docker connection failed: {e}")
        return False

if __name__ == "__main__":
    test_docker_connectivity()