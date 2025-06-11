import os
import json
import time
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from database import init_db, get_db
from routes import api, web, webhook
from services.auth_service import AuthService
from utils.logger import logger, log_api_request, log_performance_metric

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_time = time.time()
    logger.info("Starting GitHub Sync Server with enhanced logging capabilities...")
    
    try:
        init_db()
        startup_duration = time.time() - start_time
        log_performance_metric("application_startup", startup_duration, {
            "database_initialized": True,
            "loguru_enabled": True
        })
        logger.success(f"GitHub Sync Server started successfully in {round(startup_duration * 1000, 2)}ms")
    except Exception as e:
        logger.error(f"Failed to start GitHub Sync Server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down GitHub Sync Server...")
    logger.info("Server shutdown completed")

app = FastAPI(
    title="GitHub Sync Server",
    description="FastAPI-based GitHub webhook server with Docker container management",
    version="1.0.0",
    lifespan=lifespan
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "github-sync-secret-key-change-in-production"))

# API request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Get user from session if available
    user = None
    if hasattr(request.state, 'current_user') and request.state.current_user:
        user = request.state.current_user.username
    
    # Log the request
    log_api_request(
        method=request.method,
        path=str(request.url.path),
        status_code=response.status_code,
        response_time=duration,
        user=user,
        ip=client_ip
    )
    
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(web.router, prefix="", tags=["web"])
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(api.router, prefix="/api/v1", tags=["api-v1"])
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])

# Templates with custom filters
templates = Jinja2Templates(directory="templates")

# Add custom filters
def from_json_filter(value):
    """Parse JSON string to Python object"""
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}

templates.env.filters["from_json"] = from_json_filter

if __name__ == "__main__":
    import os
    
    # Get port from environment variable or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
