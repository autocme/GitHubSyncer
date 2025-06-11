import os
import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Any, Optional

def setup_logger():
    """Setup loguru logger with enhanced formatting and comprehensive logging"""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Enhanced format with detailed context and colors
    detailed_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Simple format for production
    simple_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}"
    )
    
    # Console handler with colors and backtrace
    logger.add(
        sys.stdout,
        format=detailed_format,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
        filter=lambda record: record["level"].no < 40  # Below ERROR level
    )
    
    # Console error handler for critical issues
    logger.add(
        sys.stderr,
        format=detailed_format,
        level="ERROR",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Main application log file with rotation
    logger.add(
        logs_dir / "github_sync_{time:YYYY-MM-DD}.log",
        format=simple_format,
        level="DEBUG",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True  # Thread-safe logging
    )
    
    # Error-specific log file
    logger.add(
        logs_dir / "errors_{time:YYYY-MM-DD}.log",
        format=detailed_format,
        level="ERROR",
        rotation="50 MB",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # Operations log for tracking all system operations
    logger.add(
        logs_dir / "operations_{time:YYYY-MM-DD}.log",
        format=simple_format,
        level="INFO",
        rotation="200 MB",
        retention="60 days",
        compression="zip",
        filter=lambda record: any(tag in record["message"] for tag in ["[GIT]", "[DOCKER]", "[WEBHOOK]", "[API]"]),
        enqueue=True
    )
    
    return logger

def log_operation(operation: str, status: str, message: str, details: Optional[Dict[str, Any]] = None, repository: str = None, container: str = None):
    """
    Log an operation with structured context and detailed information
    
    Args:
        operation: Operation type (pull, clone, restart, sync, etc.)
        status: Operation status (success, error, warning, info)
        message: Main descriptive message
        details: Additional structured details
        repository: Repository name if applicable
        container: Container name if applicable
    """
    # Build structured log message
    context = {
        "operation": operation.upper(),
        "status": status.upper(),
        "message": message
    }
    
    if repository:
        context["repository"] = repository
    if container:
        context["container"] = container
    if details:
        context["details"] = details
    
    # Format message with operation context
    log_message = f"[{operation.upper()}] {message}"
    if repository:
        log_message += f" | Repository: {repository}"
    if container:
        log_message += f" | Container: {container}"
    
    # Add details if provided
    if details:
        details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        log_message += f" | {details_str}"
    
    # Log with appropriate level based on status
    if status.lower() == 'success':
        logger.info(log_message, **context)
    elif status.lower() == 'error':
        logger.error(log_message, **context)
    elif status.lower() == 'warning':
        logger.warning(log_message, **context)
    else:
        logger.info(log_message, **context)

def log_api_request(method: str, path: str, status_code: int, user: str = None, duration: float = None, ip: str = None):
    """
    Log API request with comprehensive details
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        user: Username if authenticated
        duration: Request duration in seconds
        ip: Client IP address
    """
    context = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "user": user or "anonymous",
        "ip": ip or "unknown"
    }
    
    if duration is not None:
        context["duration_ms"] = round(duration * 1000, 2)
    
    message = f"[API] {method} {path} - {status_code}"
    if user:
        message += f" | User: {user}"
    if duration is not None:
        message += f" | Duration: {round(duration * 1000, 2)}ms"
    if ip:
        message += f" | IP: {ip}"
    
    # Log level based on status code
    if status_code >= 500:
        logger.error(message, **context)
    elif status_code >= 400:
        logger.warning(message, **context)
    else:
        logger.info(message, **context)

def log_webhook_event(repository: str, event_type: str, status: str, message: str, payload_size: int = None, source_ip: str = None):
    """
    Log webhook event with detailed context
    
    Args:
        repository: Repository name
        event_type: Webhook event type (push, pull_request, etc.)
        status: Processing status
        message: Event description
        payload_size: Webhook payload size in bytes
        source_ip: Source IP address
    """
    context = {
        "repository": repository,
        "event_type": event_type,
        "status": status.upper(),
        "source_ip": source_ip or "unknown"
    }
    
    if payload_size is not None:
        context["payload_size_bytes"] = payload_size
    
    log_message = f"[WEBHOOK] {repository} - {event_type} | {status.upper()}: {message}"
    if payload_size is not None:
        log_message += f" | Payload: {payload_size} bytes"
    if source_ip:
        log_message += f" | Source: {source_ip}"
    
    if status.lower() == 'success':
        logger.info(log_message, **context)
    elif status.lower() == 'error':
        logger.error(log_message, **context)
    else:
        logger.info(log_message, **context)

def log_git_operation(operation: str, repository: str, success: bool, message: str, branch: str = None, commit_hash: str = None, duration: float = None):
    """
    Log Git operation with comprehensive details
    
    Args:
        operation: Git operation (clone, pull, fetch, etc.)
        repository: Repository name
        success: Operation success status
        message: Operation message
        branch: Git branch name
        commit_hash: Commit hash if applicable
        duration: Operation duration in seconds
    """
    context = {
        "operation": operation.upper(),
        "repository": repository,
        "success": success,
        "branch": branch or "unknown"
    }
    
    if commit_hash:
        context["commit"] = commit_hash[:8]  # Short hash
    if duration is not None:
        context["duration_ms"] = round(duration * 1000, 2)
    
    status = "SUCCESS" if success else "FAILED"
    log_message = f"[GIT] {operation.upper()} {repository} - {status}: {message}"
    
    if branch:
        log_message += f" | Branch: {branch}"
    if commit_hash:
        log_message += f" | Commit: {commit_hash[:8]}"
    if duration is not None:
        log_message += f" | Duration: {round(duration * 1000, 2)}ms"
    
    if success:
        logger.info(log_message, **context)
    else:
        logger.error(log_message, **context)

def log_docker_operation(operation: str, container: str, success: bool, message: str, image: str = None, duration: float = None, restart_count: int = None):
    """
    Log Docker operation with detailed context
    
    Args:
        operation: Docker operation (restart, start, stop, etc.)
        container: Container name or ID
        success: Operation success status
        message: Operation message
        image: Docker image name
        duration: Operation duration in seconds
        restart_count: Number of restart attempts
    """
    context = {
        "operation": operation.upper(),
        "container": container,
        "success": success
    }
    
    if image:
        context["image"] = image
    if duration is not None:
        context["duration_ms"] = round(duration * 1000, 2)
    if restart_count is not None:
        context["restart_attempts"] = restart_count
    
    status = "SUCCESS" if success else "FAILED"
    log_message = f"[DOCKER] {operation.upper()} {container} - {status}: {message}"
    
    if image:
        log_message += f" | Image: {image}"
    if duration is not None:
        log_message += f" | Duration: {round(duration * 1000, 2)}ms"
    if restart_count is not None:
        log_message += f" | Attempts: {restart_count}"
    
    if success:
        logger.info(log_message, **context)
    else:
        logger.error(log_message, **context)

def log_security_event(event_type: str, message: str, user: str = None, ip: str = None, severity: str = "info"):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event (login_failure, api_key_created, etc.)
        message: Event description
        user: Username if applicable
        ip: IP address
        severity: Event severity (info, warning, critical)
    """
    context = {
        "event_type": event_type,
        "user": user or "unknown",
        "ip": ip or "unknown",
        "severity": severity.upper()
    }
    
    log_message = f"[SECURITY] {event_type.upper()}: {message}"
    if user:
        log_message += f" | User: {user}"
    if ip:
        log_message += f" | IP: {ip}"
    
    if severity.lower() == 'critical':
        logger.critical(log_message, **context)
    elif severity.lower() == 'warning':
        logger.warning(log_message, **context)
    else:
        logger.info(log_message, **context)

def log_performance_metric(operation: str, duration: float, details: Optional[Dict[str, Any]] = None):
    """
    Log performance metrics for monitoring
    
    Args:
        operation: Operation name
        duration: Duration in seconds
        details: Additional performance details
    """
    context = {
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "duration_s": round(duration, 3)
    }
    
    if details:
        context.update(details)
    
    log_message = f"[PERFORMANCE] {operation} completed in {round(duration * 1000, 2)}ms"
    if details:
        details_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        log_message += f" | {details_str}"
    
    logger.info(log_message, **context)

def get_log_files():
    """
    Get list of available log files with metadata
    
    Returns:
        List of log file information dictionaries
    """
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return []
    
    log_files = []
    for log_file in logs_dir.glob("*.log*"):
        try:
            stat = log_file.stat()
            log_files.append({
                "name": log_file.name,
                "path": str(log_file),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
                "type": "compressed" if log_file.suffix == ".zip" else "active"
            })
        except Exception as e:
            logger.warning(f"Failed to get stats for log file {log_file.name}: {e}")
    
    return sorted(log_files, key=lambda x: x["modified"], reverse=True)

def setup_external_loggers():
    """Configure external library loggers to reduce noise"""
    import logging
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Setup logger on import
setup_logger()
setup_external_loggers()

# Export the main logger instance
__all__ = [
    'logger', 'log_operation', 'log_api_request', 'log_webhook_event',
    'log_git_operation', 'log_docker_operation', 'log_security_event',
    'log_performance_metric', 'get_log_files'
]