import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(web.router, prefix="", tags=["web"])
app.include_router(api.router, prefix="/api/v1", tags=["api"])
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])

# Templates
templates = Jinja2Templates(directory="templates")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
