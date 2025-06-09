import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./github_sync.db")

# Configure engine based on database type
if "postgresql" in DATABASE_URL:
    # PostgreSQL configuration with connection pooling and SSL handling
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
            "application_name": "github_sync_server"
        }
    )
elif "sqlite" in DATABASE_URL:
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # Default configuration
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database and create tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize default settings
        with SessionLocal() as db:
            from models import Setting
            default_settings = [
                {"key": "main_path", "value": "/home/runner/workspace/repos", "description": "Main path for repositories"},
                {"key": "log_retention_days", "value": "30", "description": "Number of days to retain logs"},
                {"key": "setup_complete", "value": "false", "description": "Whether initial setup is complete"},
            ]
            
            for setting_data in default_settings:
                existing = db.query(Setting).filter(Setting.key == setting_data["key"]).first()
                if not existing:
                    setting = Setting(**setting_data)
                    db.add(setting)
            
            db.commit()
            logger.info("Default settings initialized")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """Get database session for direct use"""
    return SessionLocal()
