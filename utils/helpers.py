import re
import os
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from pathlib import Path
import json

def extract_repo_name_from_url(url: str) -> str:
    """
    Extract repository name from Git URL
    
    Args:
        url: Git repository URL (SSH or HTTPS)
    
    Returns:
        Repository name
    
    Examples:
        git@github.com:user/repo.git -> repo
        https://github.com/user/repo.git -> repo
        https://github.com/user/repo -> repo
    """
    if not url:
        return "unknown"
    
    # Handle SSH URLs (git@github.com:user/repo.git)
    if url.startswith("git@"):
        # Extract the part after the colon
        parts = url.split(":")
        if len(parts) > 1:
            path = parts[-1]
        else:
            return "unknown"
    else:
        # Handle HTTPS URLs
        parsed = urlparse(url)
        path = parsed.path
    
    # Remove leading slash and .git extension
    path = path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    
    # Extract the repository name (last part after /)
    repo_name = path.split("/")[-1] if "/" in path else path
    
    # Clean up the name - remove invalid characters for directory names
    repo_name = re.sub(r'[^\w\-_.]', '_', repo_name)
    
    return repo_name or "unknown"

def validate_git_url(url: str) -> bool:
    """
    Validate if the URL is a valid Git repository URL
    
    Args:
        url: Git repository URL
    
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    # SSH URL pattern
    ssh_pattern = r'^git@[\w\.-]+:[\w\.-]+/[\w\.-]+\.git$'
    
    # HTTPS URL pattern
    https_pattern = r'^https?://[\w\.-]+/[\w\.-]+/[\w\.-]+(\.git)?$'
    
    return bool(re.match(ssh_pattern, url) or re.match(https_pattern, url))

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove invalid characters for filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized or "unnamed"

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    
    Args:
        length: Token length in bytes
    
    Returns:
        URL-safe base64 encoded token
    """
    return secrets.token_urlsafe(length)

def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Hash a string using specified algorithm
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (sha256, sha1, md5)
    
    Returns:
        Hexadecimal hash string
    """
    if algorithm == "sha256":
        return hashlib.sha256(text.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(text.encode()).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely load JSON string with fallback
    
    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON or default value
    """
    if not json_string:
        return default
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default

def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump object to JSON string with fallback
    
    Args:
        obj: Object to serialize
        default: Default value if serialization fails
    
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, ensure_ascii=False, indent=None, separators=(',', ':'))
    except (TypeError, ValueError):
        return default

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and size_index < len(size_names) - 1:
        size /= 1024.0
        size_index += 1
    
    return f"{size:.1f} {size_names[size_index]}"

def validate_directory_path(path: str) -> bool:
    """
    Validate if path is a valid directory path
    
    Args:
        path: Directory path to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not path:
        return False
    
    try:
        # Check if path is absolute
        if not os.path.isabs(path):
            return False
        
        # Check if path contains invalid characters
        if any(char in path for char in ['<', '>', ':', '"', '|', '?', '*']):
            return False
        
        return True
    except Exception:
        return False

def ensure_directory_exists(path: str) -> bool:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        path: Directory path
    
    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False

def get_directory_size(path: str) -> int:
    """
    Calculate total size of directory and its contents
    
    Args:
        path: Directory path
    
    Returns:
        Total size in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
    except Exception:
        pass
    
    return total_size

def is_port_available(port: int, host: str = "localhost") -> bool:
    """
    Check if a port is available for binding
    
    Args:
        port: Port number
        host: Host address
    
    Returns:
        True if port is available, False otherwise
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
            return True
    except socket.error:
        return False

def parse_docker_labels(labels_str: str) -> Dict[str, str]:
    """
    Parse Docker labels from JSON string
    
    Args:
        labels_str: JSON string containing Docker labels
    
    Returns:
        Dictionary of labels
    """
    return safe_json_loads(labels_str, {})

def format_docker_labels(labels: Dict[str, str]) -> str:
    """
    Format Docker labels dictionary to JSON string
    
    Args:
        labels: Dictionary of labels
    
    Returns:
        JSON string
    """
    return safe_json_dumps(labels, "{}")

def extract_git_branch_from_ref(ref: str) -> Optional[str]:
    """
    Extract branch name from Git ref
    
    Args:
        ref: Git reference (e.g., refs/heads/main)
    
    Returns:
        Branch name or None
    """
    if not ref:
        return None
    
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/"):]
    
    return None

def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Validate GitHub webhook signature
    
    Args:
        payload: Webhook payload bytes
        signature: GitHub signature header
        secret: Webhook secret
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    try:
        # GitHub sends signature as sha256=<hash>
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = signature[7:]  # Remove 'sha256=' prefix
        
        # Calculate HMAC
        import hmac
        calculated_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(calculated_signature, expected_signature)
    
    except Exception:
        return False

def get_file_permissions(file_path: str) -> str:
    """
    Get file permissions in octal format
    
    Args:
        file_path: Path to file
    
    Returns:
        Octal permissions string (e.g., "755")
    """
    try:
        import stat
        file_stat = os.stat(file_path)
        return oct(stat.S_IMODE(file_stat.st_mode))[2:]
    except Exception:
        return "000"

def set_file_permissions(file_path: str, permissions: int) -> bool:
    """
    Set file permissions
    
    Args:
        file_path: Path to file
        permissions: Permissions in octal (e.g., 0o600)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        os.chmod(file_path, permissions)
        return True
    except Exception:
        return False

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to specified length
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def parse_environment_variables(env_string: str) -> Dict[str, str]:
    """
    Parse environment variables from string
    
    Args:
        env_string: String containing environment variables (KEY=value format)
    
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if not env_string:
        return env_vars
    
    for line in env_string.strip().split('\n'):
        line = line.strip()
        if line and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    
    return env_vars

def mask_sensitive_data(text: str, patterns: List[str] = None) -> str:
    """
    Mask sensitive data in text
    
    Args:
        text: Text to mask
        patterns: List of regex patterns to mask
    
    Returns:
        Text with sensitive data masked
    """
    if not text:
        return text
    
    if patterns is None:
        patterns = [
            r'password["\s]*[:=]["\s]*[^"\s,}]+',
            r'token["\s]*[:=]["\s]*[^"\s,}]+',
            r'secret["\s]*[:=]["\s]*[^"\s,}]+',
            r'key["\s]*[:=]["\s]*[^"\s,}]+',
        ]
    
    masked_text = text
    for pattern in patterns:
        masked_text = re.sub(pattern, lambda m: m.group().split('=')[0] + '=***', masked_text, flags=re.IGNORECASE)
    
    return masked_text
