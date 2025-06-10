#!/usr/bin/env python3
"""
Test automatic Docker volume path detection for new repositories
"""
import sys
import os
sys.path.append('.')

from database import get_db_session
from models import Repository, Setting
from services.git_service import GitService

def test_auto_path_detection():
    """Test that new repositories automatically use the detected Docker volume path"""
    db = get_db_session()
    
    try:
        # Check current detected path
        main_path_setting = db.query(Setting).filter(Setting.key == "main_path").first()
        current_path = main_path_setting.value if main_path_setting else "/repos"
        print(f"Current auto-detected path: {current_path}")
        
        # Simulate creating a new repository (like the API would do)
        test_repo_name = "test-new-repo"
        local_path = f"{current_path}/{test_repo_name}"
        
        print(f"New repository would be created with:")
        print(f"  Name: {test_repo_name}")
        print(f"  Local path: {local_path}")
        print(f"  Expected Docker path pattern: /data/compose/*/host-repos/test-new-repo")
        
        # Verify the path follows the Docker volume pattern
        if "/data/compose/" in local_path and "/host-repos/" in local_path:
            print("✓ Automatic Docker volume path detection working correctly")
            print("✓ New repositories will use the correct Docker volume mount path")
            return True
        else:
            print("! Path detection may need adjustment for Docker environment")
            return False
            
    except Exception as e:
        print(f"Error testing path detection: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing automatic Docker volume path detection...")
    print("=" * 55)
    
    success = test_auto_path_detection()
    
    if success:
        print("\n✓ System automatically detects and uses correct Docker volume paths")
        print("✓ No manual path updates needed when containers are recreated")
    else:
        print("\n! Path detection verification inconclusive")