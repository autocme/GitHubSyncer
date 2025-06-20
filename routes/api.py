from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models import Repository, Container, OperationLog, ApiKey, GitKey, Setting
from services.auth_service import AuthService
from services.git_service import GitService
from services.docker_service import DockerService
from services.webhook_service import WebhookService
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

# Pydantic models for API
class RepositoryCreate(BaseModel):
    name: str
    url: str
    branch: str = "main"

class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    branch: Optional[str] = None
    is_active: Optional[bool] = None

class ApiKeyCreate(BaseModel):
    name: str

class GitKeyCreate(BaseModel):
    name: str

# Authentication dependency that supports both session cookies and API keys
def get_current_user(request: Request, authorization: str = Header(None), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    
    # First try session-based authentication (for web interface)
    try:
        user_id = request.session.get('user_id')
        logger.info(f"Session user_id: {user_id}")
        logger.info(f"Session data: {dict(request.session)}")
        
        if user_id:
            from models import User
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            logger.info(f"Found user: {user.username if user else None}")
            if user:
                return user
    except Exception as e:
        logger.error(f"Session auth error: {e}")
    
    # Try cookie-based JWT token
    try:
        auth_cookie = request.cookies.get("auth_token")
        if auth_cookie:
            user = auth_service.verify_jwt_token(auth_cookie)
            if user:
                logger.info(f"Authenticated via cookie: {user.username}")
                return user
    except Exception as e:
        logger.error(f"Cookie auth error: {e}")
    
    # Then try API key or JWT token from Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
        # Try JWT token first
        user = auth_service.verify_jwt_token(token)
        if user:
            return user
        
        # Try API key
        user = auth_service.verify_api_key(token)
        if user:
            return user
    
    logger.warning("All authentication methods failed")
    raise HTTPException(status_code=401, detail="Invalid token")

# Repository endpoints
@router.get("/repositories")
def get_repositories(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get all repositories"""
    repositories = db.query(Repository).all()
    return repositories

@router.post("/repositories")
def create_repository(repo_data: RepositoryCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Create a new repository"""
    try:
        git_service = GitService(db)
        
        # Validate repository URL
        if not git_service.validate_repository_url(repo_data.url):
            raise HTTPException(status_code=400, detail="Invalid or inaccessible repository URL")
        
        # Get configured main path from settings
        main_path_setting = db.query(Setting).filter(Setting.key == "main_path").first()
        main_path = main_path_setting.value if main_path_setting else "/repos"
        
        # Set the local path based on configured main path
        local_path = f"{main_path}/{repo_data.name}"
        
        repository = Repository(
            name=repo_data.name,
            url=repo_data.url,
            branch=repo_data.branch,
            local_path=local_path,
            is_active=True
        )
        
        db.add(repository)
        db.commit()
        db.refresh(repository)
        
        # After successful creation, restart containers with matching repo label
        from services.flask_docker_service import FlaskDockerService
        docker_service = FlaskDockerService()
        success_count, restart_results = docker_service.restart_containers_by_repo_label(repo_data.name)
        
        logger.info(f"Created repository: {repo_data.name}")
        logger.info(f"Container restart results: {success_count} containers restarted")
        for result in restart_results:
            logger.info(f"Restart result: {result}")
        
        return repository
        
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/repositories/{repo_id}")
def update_repository(repo_id: int, repo_data: RepositoryUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Update repository"""
    repository = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    update_data = repo_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repository, field, value)
    
    db.commit()
    db.refresh(repository)
    
    logger.info(f"Updated repository: {repository.name}")
    return repository

@router.delete("/repositories/{repo_id}")
def delete_repository(repo_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Delete repository"""
    repository = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db.delete(repository)
    db.commit()
    
    logger.info(f"Deleted repository: {repository.name}")
    return {"message": "Repository deleted successfully"}

@router.post("/repositories/{repo_id}/sync")
async def sync_repository(repo_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Manually sync a repository"""
    webhook_service = WebhookService(db)
    result = await webhook_service.manual_sync_repository(repo_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to sync repository"))
    
    return result

# Container endpoints
@router.get("/containers")
def get_containers(db: Session = Depends(get_db)):
    """Get all containers"""
    docker_service = DockerService(db)
    # Refresh container list
    docker_service.discover_containers()
    
    containers = db.query(Container).all()
    return containers

@router.post("/containers/discover")
def discover_containers(db: Session = Depends(get_db)):
    """Discover Docker containers"""
    docker_service = DockerService(db)
    containers = docker_service.discover_containers()
    return {"message": f"Discovered {len(containers)} containers", "containers": containers}

@router.post("/test/sync/{repo_name}")
def test_sync_repository(repo_name: str, db: Session = Depends(get_db)):
    """Test sync functionality without authentication"""
    from services.flask_docker_service import FlaskDockerService
    
    # Get repository
    repository = db.query(Repository).filter(Repository.name == repo_name).first()
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Simulate git pull success
    logger.info(f"Simulating git pull for repository: {repo_name}")
    
    # Test container restart functionality
    flask_docker = FlaskDockerService()
    success_count, results = flask_docker.restart_containers_by_repo_label(repo_name)
    
    return {
        "success": True,
        "message": f"Synced repository {repo_name}",
        "container_restarts": {
            "success_count": success_count,
            "results": results
        }
    }

@router.post("/containers/{container_id}/restart")
def restart_container(container_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Restart a container"""
    container = db.query(Container).filter(Container.container_id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = DockerService(db)
    success, message = docker_service.restart_container(container)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"message": message}

# Logs endpoints
@router.get("/logs")
def get_logs(limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get operation logs"""
    logs = db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(limit).all()
    return logs

@router.delete("/logs")
def clear_logs(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Clear all operation logs"""
    try:
        # Count logs before deletion
        log_count = db.query(OperationLog).count()
        
        # Delete all logs
        db.query(OperationLog).delete()
        db.commit()
        
        logger.info(f"Cleared {log_count} operation logs by user {current_user.username}")
        
        return {
            "success": True,
            "message": f"Successfully cleared {log_count} operation logs",
            "deleted_count": log_count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")

# API Key endpoints
@router.get("/api-keys")
def get_api_keys(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get user's API keys"""
    api_keys = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.is_active == True
    ).all()
    return api_keys

@router.post("/api-keys")
def create_api_key(key_data: ApiKeyCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Create a new API key"""
    auth_service = AuthService(db)
    success, message, api_key = auth_service.create_api_key(key_data.name, current_user.id)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"message": message, "api_key": api_key}

@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Revoke an API key"""
    auth_service = AuthService(db)
    success, message = auth_service.revoke_api_key(key_id)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {"message": message}

# Git Key endpoints
@router.get("/git-keys")
def get_git_keys(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get Git SSH keys"""
    git_keys = db.query(GitKey).filter(GitKey.is_active == True).all()
    # Return safe response without private keys
    return [
        {
            "id": key.id,
            "name": key.name,
            "public_key": key.public_key,
            "is_active": key.is_active,
            "created_at": key.created_at,
            "private_key": "[HIDDEN]"
        }
        for key in git_keys
    ]

@router.post("/git-keys")
def create_git_key(key_data: GitKeyCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Generate a new Git SSH key"""
    try:
        git_service = GitService(db)
        private_key, public_key = git_service.generate_ssh_key(key_data.name)
        
        git_key = GitKey(
            name=key_data.name,
            private_key=private_key,
            public_key=public_key,
            is_active=True
        )
        
        db.add(git_key)
        db.commit()
        db.refresh(git_key)
        
        logger.info(f"Created Git SSH key: {key_data.name}")
        return {
            "message": "Git SSH key created successfully",
            "public_key": public_key,
            "key_id": git_key.id
        }
        
    except Exception as e:
        logger.error(f"Error creating Git SSH key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/git-keys/{key_id}")
def delete_git_key(key_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Delete a Git SSH key"""
    git_key = db.query(GitKey).filter(GitKey.id == key_id).first()
    if not git_key:
        raise HTTPException(status_code=404, detail="Git key not found")
    
    # Update the record to mark as inactive
    db.query(GitKey).filter(GitKey.id == key_id).update({"is_active": False})
    db.commit()
    
    logger.info(f"Deleted Git SSH key: {git_key.name}")
    return {"message": "Git SSH key deleted successfully"}

# Public health check endpoint (no authentication required)
@router.get("/health")
@router.get("/v1/health")
def health_check():
    """Public health check endpoint for Docker health checks"""
    return {"status": "healthy", "message": "GitHub Sync Server is running"}

# System status endpoint
@router.get("/status")
def get_system_status(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get system status"""
    docker_service = DockerService(db)
    
    # Count repositories
    total_repos = db.query(Repository).count()
    active_repos = db.query(Repository).filter(Repository.is_active == True).count()
    
    # Count containers
    total_containers = db.query(Container).count()
    
    # Count recent logs
    recent_logs = db.query(OperationLog).count()
    
    # Docker status
    docker_available = docker_service.is_docker_available()
    docker_info = docker_service.get_docker_info() if docker_available else None
    
    return {
        "repositories": {
            "total": total_repos,
            "active": active_repos
        },
        "containers": {
            "total": total_containers
        },
        "logs": {
            "total": recent_logs
        },
        "docker": {
            "available": docker_available,
            "info": docker_info
        }
    }
