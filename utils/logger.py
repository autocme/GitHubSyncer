import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup logger with both file and console handlers
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # File handler with rotation
    log_file = logs_dir / "github_sync.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def setup_uvicorn_logger():
    """Setup uvicorn logger to use our custom formatter"""
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # File handler for uvicorn logs
    log_file = logs_dir / "uvicorn.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    uvicorn_logger.addHandler(file_handler)
    uvicorn_access_logger.addHandler(file_handler)

def log_operation(logger: logging.Logger, operation: str, status: str, message: str, details: str = None):
    """
    Log an operation with standardized format
    
    Args:
        logger: Logger instance
        operation: Operation type (pull, clone, restart, etc.)
        status: Operation status (success, error, warning)
        message: Main message
        details: Additional details (optional)
    """
    log_message = f"[{operation.upper()}] {status.upper()}: {message}"
    if details:
        log_message += f" | Details: {details}"
    
    if status.lower() == 'success':
        logger.info(log_message)
    elif status.lower() == 'error':
        logger.error(log_message)
    elif status.lower() == 'warning':
        logger.warning(log_message)
    else:
        logger.info(log_message)

def log_api_request(logger: logging.Logger, method: str, path: str, status_code: int, user: str = None):
    """
    Log API request
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        user: Username (optional)
    """
    user_info = f" | User: {user}" if user else ""
    logger.info(f"[API] {method} {path} - {status_code}{user_info}")

def log_webhook_event(logger: logging.Logger, repository: str, status: str, message: str):
    """
    Log webhook event
    
    Args:
        logger: Logger instance
        repository: Repository name
        status: Event status
        message: Event message
    """
    logger.info(f"[WEBHOOK] {repository} - {status.upper()}: {message}")

def log_git_operation(logger: logging.Logger, operation: str, repository: str, success: bool, message: str):
    """
    Log Git operation
    
    Args:
        logger: Logger instance
        operation: Git operation (clone, pull, etc.)
        repository: Repository name
        success: Operation success status
        message: Operation message
    """
    status = "SUCCESS" if success else "FAILED"
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"[GIT] {operation.upper()} {repository} - {status}: {message}")

def log_docker_operation(logger: logging.Logger, operation: str, container: str, success: bool, message: str):
    """
    Log Docker operation
    
    Args:
        logger: Logger instance
        operation: Docker operation (restart, start, stop, etc.)
        container: Container name
        success: Operation success status
        message: Operation message
    """
    status = "SUCCESS" if success else "FAILED"
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"[DOCKER] {operation.upper()} {container} - {status}: {message}")

def get_log_files():
    """
    Get list of available log files
    
    Returns:
        List of log file paths
    """
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return []
    
    log_files = []
    for log_file in logs_dir.glob("*.log*"):
        log_files.append({
            "name": log_file.name,
            "path": str(log_file),
            "size": log_file.stat().st_size,
            "modified": datetime.fromtimestamp(log_file.stat().st_mtime)
        })
    
    return sorted(log_files, key=lambda x: x["modified"], reverse=True)

def cleanup_old_logs(retention_days: int = 30):
    """
    Clean up old log files
    
    Args:
        retention_days: Number of days to retain logs
    """
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return
    
    cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
    
    for log_file in logs_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                print(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                print(f"Failed to delete log file {log_file.name}: {e}")

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Reduce noise from external libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("docker").setLevel(logging.WARNING)
logging.getLogger("git").setLevel(logging.WARNING)
