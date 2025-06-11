"""
Enhanced logging utilities using loguru for structured logging
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

def setup_logger():
    """
    Setup logger configuration - kept for backward compatibility
    The logger is already configured on module import
    """
    pass

# Remove default logger
logger.remove()

# Configure enhanced structured logging with multiple outputs
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True,
    enqueue=True
)

# File logging with rotation
logger.add(
    "logs/github_sync_{time}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
    enqueue=True
)

# Error-only file logging
logger.add(
    "logs/errors_{time}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message} | {extra}",
    level="ERROR",
    rotation="5 MB",
    retention="30 days",
    compression="gz",
    backtrace=True,
    diagnose=True,
    enqueue=True
)

# Operation-specific file logging with custom formatter
def operations_formatter(record):
    operation_type = record["extra"].get("operation_type", "GENERAL").upper()
    return "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | " + operation_type + " | {message} | {extra}\n"

logger.add(
    "logs/operations_{time}.log",
    format=operations_formatter,
    level="INFO",
    filter=lambda record: any(tag in record["message"] for tag in ["[GIT]", "[DOCKER]", "[WEBHOOK]", "[API]"]),
    enqueue=True
)

def log_operation(operation: str, status: str, message: str, details: Optional[Dict[str, Any]] = None, repository: Optional[str] = None, container: Optional[str] = None):
    """Log an operation with structured context"""
    context = {
        "operation_type": operation,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    if repository:
        context["repository"] = repository
    if container:
        context["container"] = container
    
    with logger.contextualize(**context):
        if status == "success":
            logger.info(f"[{operation.upper()}] {message}")
        elif status == "error":
            logger.error(f"[{operation.upper()}] {message}")
        else:
            logger.warning(f"[{operation.upper()}] {message}")

def log_git_operation(action: str, repository: str, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
    """Log Git-specific operations"""
    context = {
        "operation_type": "git",
        "action": action,
        "repository": repository,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if success:
            logger.info(f"[GIT] {action} on {repository}: {message}")
        else:
            logger.error(f"[GIT] {action} on {repository} failed: {message}")

def log_docker_operation(action: str, container_name: str, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
    """Log Docker-specific operations"""
    context = {
        "operation_type": "docker",
        "action": action,
        "container": container_name,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if success:
            logger.info(f"[DOCKER] {action} on {container_name}: {message}")
        else:
            logger.error(f"[DOCKER] {action} on {container_name} failed: {message}")

def log_webhook_event(event_type: str, repository: str, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
    """Log webhook-specific events"""
    context = {
        "operation_type": "webhook",
        "event_type": event_type,
        "repository": repository,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if success:
            logger.info(f"[WEBHOOK] {event_type} for {repository}: {message}")
        else:
            logger.error(f"[WEBHOOK] {event_type} for {repository} failed: {message}")

def log_api_request(method: str, path: str, status_code: int, response_time: float, user: Optional[str] = None, ip: Optional[str] = None):
    """Log API request details"""
    context = {
        "operation_type": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time": response_time,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user:
        context["user"] = user
    if ip:
        context["ip"] = ip
    
    with logger.contextualize(**context):
        logger.info(f"[API] {method} {path} - {status_code} ({response_time:.3f}s)")

def log_security_event(event_type: str, user: Optional[str], ip: str, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
    """Log security-related events"""
    context = {
        "operation_type": "security",
        "event_type": event_type,
        "ip": ip,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user:
        context["user"] = user
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if success:
            logger.info(f"[SECURITY] {event_type}: {message}")
        else:
            logger.warning(f"[SECURITY] {event_type} failed: {message}")

def log_database_operation(operation: str, table: str, count: int, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
    """Log database operations"""
    context = {
        "operation_type": "database",
        "operation": operation,
        "table": table,
        "count": count,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if success:
            logger.info(f"[DATABASE] {operation} on {table}: {message} (count: {count})")
        else:
            logger.error(f"[DATABASE] {operation} on {table} failed: {message}")

def log_performance_metric(operation: str, duration: float, details: Optional[Dict[str, Any]] = None):
    """Log performance metrics"""
    context = {
        "operation_type": "performance",
        "operation": operation,
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if duration > 5.0:
            logger.warning(f"[PERFORMANCE] {operation} took {duration:.3f}s (slow)")
        else:
            logger.info(f"[PERFORMANCE] {operation} completed in {duration:.3f}s")

def log_system_status(component: str, status: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Log system status updates"""
    context = {
        "operation_type": "system",
        "component": component,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        context.update(details)
    
    with logger.contextualize(**context):
        if status == "healthy":
            logger.info(f"[SYSTEM] {component}: {message}")
        elif status == "warning":
            logger.warning(f"[SYSTEM] {component}: {message}")
        else:
            logger.error(f"[SYSTEM] {component}: {message}")

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Export the configured logger
__all__ = [
    "logger",
    "setup_logger",
    "log_operation",
    "log_git_operation", 
    "log_docker_operation",
    "log_webhook_event",
    "log_api_request",
    "log_security_event",
    "log_database_operation",
    "log_performance_metric",
    "log_system_status"
]