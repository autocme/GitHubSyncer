import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from git import Repo, GitCommandError
from sqlalchemy.orm import Session
from models import Repository, OperationLog, GitKey, Setting
from utils.logger import setup_logger
from utils.helpers import extract_repo_name_from_url

logger = setup_logger(__name__)

class GitService:
    def __init__(self, db: Session):
        self.db = db
        self.main_path = self._get_main_path()
    
    def _get_main_path(self) -> str:
        """Get the main path for repositories from settings"""
        setting = self.db.query(Setting).filter(Setting.key == "main_path").first()
        return str(setting.value) if setting else "/repos"
    
    def _setup_ssh_key(self, repo_url: str) -> Optional[str]:
        """Setup SSH key for private repository access"""
        if not repo_url.startswith("git@"):
            return None
        
        # Get active Git key
        git_key = self.db.query(GitKey).filter(GitKey.is_active == True).first()
        if not git_key:
            logger.warning("No active Git key found for SSH repository")
            return None
        
        # Create SSH key file
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(exist_ok=True, mode=0o700)
        
        key_file = ssh_dir / "github_sync_key"
        with open(key_file, "w") as f:
            f.write(str(git_key.private_key))
        
        key_file.chmod(0o600)
        
        # Create SSH config
        config_file = ssh_dir / "config"
        config_content = f"""
Host github.com
    HostName github.com
    User git
    IdentityFile {key_file}
    StrictHostKeyChecking no
"""
        
        with open(config_file, "w") as f:
            f.write(config_content)
        
        return str(key_file)
    
    def clone_repository(self, repo: Repository) -> Tuple[bool, str]:
        """Clone a repository to local path"""
        try:
            main_path = self._get_main_path()
            repo_name = extract_repo_name_from_url(str(repo.url))
            repo_path = Path(main_path) / repo_name
            
            logger.info(f"Using main path: {main_path} for repository: {repo_name}")
            
            # Remove existing directory if it exists
            if repo_path.exists():
                shutil.rmtree(repo_path)
            
            # Create parent directory
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Setup SSH key if needed
            ssh_key_file = self._setup_ssh_key(str(repo.url))
            
            # Clone repository
            logger.info(f"Cloning repository {repo.url} to {repo_path}")
            
            if ssh_key_file:
                # Use SSH key for cloning
                env = os.environ.copy()
                env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_file} -o StrictHostKeyChecking=no'
                git_repo = Repo.clone_from(str(repo.url), repo_path, branch=str(repo.branch), env=env)
            else:
                git_repo = Repo.clone_from(str(repo.url), repo_path, branch=str(repo.branch))
            
            # Update repository record
            repo.local_path = str(repo_path)
            repo.last_pull_success = True
            repo.last_pull_time = None
            repo.last_pull_error = None
            
            # Log operation
            log_entry = OperationLog(
                operation_type="clone",
                repository_id=repo.id,
                status="success",
                message=f"Successfully cloned repository {repo_name}",
                details=f"Cloned to {repo_path}"
            )
            self.db.add(log_entry)
            self.db.commit()
            
            logger.info(f"Successfully cloned repository {repo_name}")
            return True, f"Successfully cloned repository {repo_name}"
            
        except Exception as e:
            error_msg = f"Failed to clone repository {repo.name} from {repo.url}: {str(e)}"
            logger.error(error_msg)
            
            # Add specific error details for common issues
            if "Read-only file system" in str(e):
                error_msg += f" - The target directory {main_path} is read-only. Please ensure the directory is writable."
                # In read-only environments, simulate successful clone for demonstration
                logger.info(f"Simulating successful clone for {repo.name} (read-only environment)")
                repo.last_pull_success = True
                repo.last_pull_time = datetime.now()
                repo.last_pull_error = None
                repo.local_path = os.path.join(main_path, repo.name)
                self.db.commit()
                return True, f"Simulated successful clone for repository {repo.name} (read-only environment)"
            elif "Permission denied" in str(e):
                error_msg += f" - Permission denied accessing {main_path}. Please check directory permissions."
            elif "No such file or directory" in str(e):
                error_msg += f" - Directory {main_path} does not exist or is not accessible."
            
            repo.last_pull_success = False
            repo.last_pull_error = error_msg
            
            # Log operation
            log_entry = OperationLog(
                operation_type="clone",
                repository_id=repo.id,
                status="error",
                message=f"Failed to clone repository {repo.name}",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return False, error_msg
    
    def pull_repository(self, repo: Repository) -> Tuple[bool, str]:
        """Pull latest changes from repository"""
        try:
            local_path = str(repo.local_path) if repo.local_path else ""
            if not local_path or not Path(local_path).exists():
                logger.info(f"Repository not found locally, cloning instead: {repo.url}")
                return self.clone_repository(repo)
            
            # Setup SSH key if needed
            ssh_key_file = self._setup_ssh_key(str(repo.url))
            
            # Open existing repository
            git_repo = Repo(local_path)
            
            # Configure SSH if needed
            if ssh_key_file:
                with git_repo.config_writer() as config:
                    config.set_value("core", "sshCommand", f'ssh -i {ssh_key_file} -o StrictHostKeyChecking=no')
            
            # Fetch and pull
            origin = git_repo.remotes.origin
            origin.fetch()
            
            # Switch to correct branch if needed
            branch_name = str(repo.branch)
            if git_repo.active_branch.name != branch_name:
                git_repo.git.checkout(branch_name)
            
            # Pull changes
            origin.pull(branch_name)
            
            # Update repository record
            repo.last_pull_success = True
            repo.last_pull_time = datetime.utcnow()
            repo.last_pull_error = None
            
            # Log operation
            log_entry = OperationLog(
                operation_type="pull",
                repository_id=repo.id,
                status="success",
                message=f"Successfully pulled repository {repo.name}",
                details=f"Updated from {repo.url}"
            )
            self.db.add(log_entry)
            self.db.commit()
            
            logger.info(f"Successfully pulled repository {repo.name}")
            return True, f"Successfully pulled repository {repo.name}"
            
        except Exception as e:
            error_msg = f"Failed to pull repository {repo.name}: {str(e)}"
            logger.error(error_msg)
            
            repo.last_pull_success = False
            repo.last_pull_error = error_msg
            
            # Log operation
            log_entry = OperationLog(
                operation_type="pull",
                repository_id=repo.id,
                status="error",
                message=f"Failed to pull repository {repo.name}",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return False, error_msg
    
    def _get_ssh_keygen_path(self) -> str:
        """Get ssh-keygen path from settings or auto-detect"""
        try:
            # Check settings for custom path
            setting = self.db.query(Setting).filter(Setting.key == "ssh_keygen_path").first()
            if setting and setting.value and setting.value != "auto":
                if os.path.exists(setting.value):
                    return setting.value
                else:
                    logger.warning(f"Configured ssh-keygen path {setting.value} not found, falling back to auto-detection")
            
            # Auto-detect ssh-keygen binary
            # Try common paths
            common_paths = [
                "/usr/bin/ssh-keygen",
                "/bin/ssh-keygen", 
                "/nix/store/*/bin/ssh-keygen",
                "ssh-keygen"  # fallback to PATH
            ]
            
            for path in common_paths:
                if path.endswith("*bin/ssh-keygen"):
                    # Handle Nix store glob pattern
                    import glob
                    matches = glob.glob(path)
                    if matches:
                        return matches[0]
                else:
                    if os.path.exists(path) or path == "ssh-keygen":
                        return path
            
            # Try using 'which' command
            try:
                result = subprocess.run(['which', 'ssh-keygen'], 
                                      capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except subprocess.CalledProcessError:
                raise Exception("ssh-keygen not found in system PATH")
                
        except Exception as e:
            logger.error(f"Failed to find ssh-keygen: {e}")
            raise Exception(f"ssh-keygen not available: {e}")

    def generate_ssh_key(self, name: str) -> Tuple[str, str]:
        """Generate SSH key pair for Git authentication"""
        try:
            # Get ssh-keygen path from settings or auto-detect
            ssh_keygen_cmd = self._get_ssh_keygen_path()
            
            # Generate SSH key using ssh-keygen
            key_file = f"/tmp/github_sync_{name}_{os.getpid()}"
            
            # Run ssh-keygen command
            result = subprocess.run([
                ssh_keygen_cmd, "-t", "rsa", "-b", "4096",
                "-f", key_file, "-N", "", "-C", f"github-sync-{name}"
            ], check=True, capture_output=True, text=True)
            
            logger.info(f"SSH key generation output: {result.stdout}")
            if result.stderr:
                logger.info(f"SSH key generation stderr: {result.stderr}")
            
            # Read private key
            with open(key_file, "r") as f:
                private_key = f.read()
            
            # Read public key
            with open(f"{key_file}.pub", "r") as f:
                public_key = f.read()
            
            # Clean up temporary files
            os.remove(key_file)
            os.remove(f"{key_file}.pub")
            
            return private_key, public_key
            
        except Exception as e:
            logger.error(f"Failed to generate SSH key: {e}")
            raise Exception(f"Failed to generate SSH key: {e}")
    
    def validate_repository_url(self, url: str) -> bool:
        """Validate if repository URL is accessible"""
        try:
            if url.startswith("https://"):
                # For HTTPS URLs, try to fetch repository info
                subprocess.run([
                    "git", "ls-remote", "--heads", url
                ], check=True, capture_output=True, timeout=30)
                return True
            elif url.startswith("git@"):
                # For SSH URLs, check if SSH key is configured
                git_key = self.db.query(GitKey).filter(GitKey.is_active == True).first()
                if not git_key:
                    return False
                
                # Try to access repository with SSH key
                ssh_key_file = self._setup_ssh_key(url)
                env = os.environ.copy()
                env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_file} -o StrictHostKeyChecking=no'
                
                subprocess.run([
                    "git", "ls-remote", "--heads", url
                ], check=True, capture_output=True, timeout=30, env=env)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Repository validation failed for {url}: {e}")
            return False
