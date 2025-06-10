#!/usr/bin/env python3
"""
Test script to verify git operations work with the actual Docker volume path
"""
import sys
import os
sys.path.append('.')

from database import get_db_session
from models import Repository, Setting
from services.git_service import GitService

def test_real_git_operations():
    """Test actual git operations with Docker volume path"""
    db = get_db_session()
    
    try:
        # Get the configured path
        main_path_setting = db.query(Setting).filter(Setting.key == "main_path").first()
        configured_path = main_path_setting.value if main_path_setting else "/repos"
        print(f"Configured main path: {configured_path}")
        
        # Get the existing repository
        repo = db.query(Repository).filter(Repository.name == "server-backend").first()
        if not repo:
            print("No server-backend repository found")
            return False
            
        print(f"Repository found:")
        print(f"  Name: {repo.name}")
        print(f"  URL: {repo.url}")
        print(f"  Local path: {repo.local_path}")
        print(f"  Branch: {repo.branch}")
        
        # Check if the path exists
        import pathlib
        path_obj = pathlib.Path(repo.local_path)
        print(f"Path exists: {path_obj.exists()}")
        if path_obj.exists():
            print(f"Path contents: {list(path_obj.iterdir())}")
        
        # Update repository URL to a real public repository for testing
        original_url = repo.url
        repo.url = "https://github.com/OCA/server-backend.git"
        repo.branch = "17.0"
        db.commit()
        
        print(f"\nUpdated repository URL to: {repo.url}")
        print(f"Branch: {repo.branch}")
        
        # Test git service
        git_service = GitService(db)
        
        # Try to pull/clone the repository
        print("\nTesting git operations...")
        success, message = git_service.pull_repository(repo)
        
        print(f"Git operation result: {success}")
        print(f"Message: {message}")
        
        # Restore original URL
        repo.url = original_url
        db.commit()
        
        return success
        
    except Exception as e:
        print(f"Error testing git operations: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing real git operations with Docker volume path...")
    print("=" * 60)
    
    success = test_real_git_operations()
    
    if success:
        print("\n✓ Git operations working correctly with Docker volume path")
    else:
        print("\n! Git operations need configuration")