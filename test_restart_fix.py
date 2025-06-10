#!/usr/bin/env python3
"""
Test script to verify the container restart fix
"""

import sys
import os
sys.path.append('.')

from database import get_db_session
from services.docker_service import DockerService
from models import Container
from datetime import datetime

def test_restart_fix():
    """Test the fixed container restart functionality"""
    
    print("Testing container restart fix...")
    
    # Get database session
    db = get_db_session()
    
    try:
        # Initialize Docker service
        docker_service = DockerService(db)
        
        # Get the odoo-odoo-1 container
        container = db.query(Container).filter_by(name="odoo-odoo-1").first()
        if not container:
            print("ERROR: odoo-odoo-1 container not found")
            return False
        
        print(f"Found container: {container.name}")
        print(f"Container ID: {container.container_id}")
        print(f"Status: {container.status}")
        print(f"Restart after pull: {container.restart_after_pull}")
        
        # Test the restart function
        print("\nTesting container restart...")
        success, message = docker_service.restart_container(container)
        
        print(f"Restart result: {success}")
        print(f"Message: {message}")
        
        # Check updated status
        db.refresh(container)
        print(f"\nUpdated container status:")
        print(f"Last restart success: {container.last_restart_success}")
        print(f"Last restart time: {container.last_restart_time}")
        if container.last_restart_error:
            print(f"Last restart error: {container.last_restart_error}")
        
        # Test repository-based restart
        print("\nTesting repository-based restart...")
        results = docker_service.restart_containers_for_repository("server-backend")
        
        print(f"Found {len(results)} containers to restart for server-backend:")
        for container_name, restart_success, restart_message in results:
            status = "SUCCESS" if restart_success else "FAILED"
            print(f"  - {container_name}: {status} - {restart_message}")
        
        return success
        
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_restart_fix()
    if success:
        print("\nContainer restart fix verified successfully!")
    else:
        print("\nContainer restart test failed!")
    
    sys.exit(0 if success else 1)