import os
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from database import init_db, get_db
from routes import api, web, webhook
from services.auth_service import AuthService
from utils.logger import setup_logger

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting GitHub Sync Server...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down GitHub Sync Server...")

app = FastAPI(
    title="GitHub Sync Server",
    description="FastAPI-based GitHub webhook server with Docker container management",
    version="1.0.0",
    lifespan=lifespan
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "github-sync-secret-key-change-in-production"))

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(web.router, prefix="", tags=["web"])
app.include_router(api.router, prefix="/api", tags=["api"])
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
