import json
from fastapi import APIRouter, Request, Depends, HTTPException, Form, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import Repository, Container, OperationLog, User, GitKey, ApiKey, Setting
from services.auth_service import AuthService
from services.git_service import GitService
from services.docker_service import DockerService
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Add JSON filter for templates
def from_json_filter(value):
    """Parse JSON string to Python object"""
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}

templates.env.filters["from_json"] = from_json_filter

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from session cookie"""
    token = request.cookies.get("auth_token")
    if not token:
        return None
    
    auth_service = AuthService(db)
    return auth_service.verify_jwt_token(token)

def require_auth(request: Request, db: Session = Depends(get_db)):
    """Require authentication for protected routes"""
    user = get_current_user_from_cookie(request, db)
    if not user:
        # For web routes, we need to handle redirects in the route handler itself
        # This dependency will return None and the route will check for it
        return None
    return user

@router.get("/favicon.ico")
def favicon():
    """Serve favicon from static directory"""
    return FileResponse("static/favicon.ico")

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Main index page - redirect to setup or dashboard"""
    auth_service = AuthService(db)
    
    if not auth_service.is_setup_complete():
        return RedirectResponse(url="/setup")
    
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    return RedirectResponse(url="/dashboard")

@router.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, db: Session = Depends(get_db)):
    """Setup wizard page"""
    auth_service = AuthService(db)
    
    if auth_service.is_setup_complete():
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("setup.html", {"request": request})

@router.post("/setup")
def complete_setup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(None),
    main_path: str = Form("/repos"),
    db: Session = Depends(get_db)
):
    """Complete initial setup"""
    auth_service = AuthService(db)
    
    if auth_service.is_setup_complete():
        return RedirectResponse(url="/dashboard")
    
    try:
        # Create admin user
        success, message = auth_service.create_user(username, password, email)
        if not success:
            return templates.TemplateResponse("setup.html", {
                "request": request,
                "error": message
            })
        
        # Update main path setting
        setting = db.query(Setting).filter(Setting.key == "main_path").first()
        if setting:
            setting.value = main_path
            db.commit()
        
        # Mark setup as complete
        auth_service.complete_setup()
        
        logger.info("Initial setup completed successfully")
        return RedirectResponse(url="/login?setup=complete", status_code=302)
        
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return templates.TemplateResponse("setup.html", {
            "request": request,
            "error": f"Setup failed: {str(e)}"
        })

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login page"""
    setup_complete = request.query_params.get("setup") == "complete"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "setup_complete": setup_complete
    })

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login"""
    # Get client IP and user agent for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    auth_service = AuthService(db)
    user, error_msg = auth_service.authenticate_user(username, password, client_ip, user_agent)
    
    if not user:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": error_msg or "Invalid username or password"
        })
    
    # Set session data for API authentication
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    
    # Also create JWT token for cookie-based auth (optional)
    token = auth_service.create_jwt_token(user)
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
    
    return response

@router.get("/logout")
def logout(request: Request):
    """Handle logout"""
    # Clear session data
    request.session.clear()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("auth_token")
    return response

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Dashboard page"""
    # Get statistics
    total_repos = db.query(Repository).count()
    active_repos = db.query(Repository).filter(Repository.is_active == True).count()
    total_containers = db.query(Container).count()
    recent_logs = db.query(OperationLog).order_by(OperationLog.created_at.desc()).limit(5).all()
    
    # Docker service status
    docker_service = DockerService(db)
    docker_available = docker_service.is_docker_available()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "stats": {
            "total_repos": total_repos,
            "active_repos": active_repos,
            "total_containers": total_containers,
            "docker_available": docker_available
        },
        "recent_logs": recent_logs
    })

@router.get("/repositories", response_class=HTMLResponse)
def repositories_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Repositories management page"""
    repositories = db.query(Repository).all()
    return templates.TemplateResponse("repositories.html", {
        "request": request,
        "user": current_user,
        "repositories": repositories
    })

@router.get("/containers", response_class=HTMLResponse)
def containers_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Containers management page"""
    # Refresh container list
    docker_service = DockerService(db)
    docker_service.discover_containers()
    
    containers = db.query(Container).all()
    return templates.TemplateResponse("containers.html", {
        "request": request,
        "user": current_user,
        "containers": containers
    })

@router.post("/containers/{container_id}/restart")
def restart_container_web(request: Request, container_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Restart container via web interface"""
    from fastapi.responses import RedirectResponse
    
    container = db.query(Container).filter(Container.container_id == container_id).first()
    if not container:
        # Redirect back with error
        return RedirectResponse(url="/containers?error=Container not found", status_code=302)
    
    docker_service = DockerService(db)
    success, message = docker_service.restart_container(container)
    
    if success:
        return RedirectResponse(url="/containers?success=Container restarted successfully", status_code=302)
    else:
        return RedirectResponse(url=f"/containers?error={message}", status_code=302)

@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, page: int = 1, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Logs page with pagination"""
    per_page = 20
    offset = (page - 1) * per_page
    
    # Get total count for pagination
    total_logs = db.query(OperationLog).count()
    total_pages = (total_logs + per_page - 1) // per_page
    
    # Get logs for current page
    logs = db.query(OperationLog).order_by(OperationLog.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Calculate pagination info
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "user": current_user,
        "logs": logs,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_logs": total_logs,
            "per_page": per_page,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_page": prev_page,
            "next_page": next_page,
            "start_record": offset + 1,
            "end_record": min(offset + per_page, total_logs)
        }
    })

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db), current_user = Depends(require_auth)):
    """Settings page"""
    # Check authentication
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get all settings
    settings = db.query(Setting).all()
    settings_dict = {s.key: s.value for s in settings}
    
    # Get Git keys
    git_keys = db.query(GitKey).filter(GitKey.is_active == True).all()
    
    # Get API keys
    api_keys = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.is_active == True
    ).all()
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
        "settings": settings_dict,
        "git_keys": git_keys,
        "api_keys": api_keys
    })

@router.post("/settings/general")
def update_general_settings(
    request: Request,
    main_path: str = Form(...),
    log_retention_days: int = Form(...),
    ssh_keygen_path: str = Form("auto"),
    git_path: str = Form("auto"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """Update general settings"""
    try:
        # Update main path
        main_path_setting = db.query(Setting).filter(Setting.key == "main_path").first()
        if main_path_setting:
            main_path_setting.value = main_path
        
        # Update log retention
        log_retention_setting = db.query(Setting).filter(Setting.key == "log_retention_days").first()
        if log_retention_setting:
            log_retention_setting.value = str(log_retention_days)
        
        # Update SSH keygen path
        ssh_keygen_setting = db.query(Setting).filter(Setting.key == "ssh_keygen_path").first()
        if not ssh_keygen_setting:
            ssh_keygen_setting = Setting(key="ssh_keygen_path", value=ssh_keygen_path, description="Path to ssh-keygen binary")
            db.add(ssh_keygen_setting)
        else:
            ssh_keygen_setting.value = ssh_keygen_path
        
        # Update git path
        git_path_setting = db.query(Setting).filter(Setting.key == "git_path").first()
        if not git_path_setting:
            git_path_setting = Setting(key="git_path", value=git_path, description="Path to git binary")
            db.add(git_path_setting)
        else:
            git_path_setting.value = git_path
        
        db.commit()
        logger.info("General settings updated")
        
        return RedirectResponse(url="/settings?success=general", status_code=302)
        
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return RedirectResponse(url="/settings?error=general", status_code=302)
