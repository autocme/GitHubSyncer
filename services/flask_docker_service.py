import docker
import os
import subprocess
from typing import List, Tuple, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FlaskDockerService:
    """
    Docker service using the exact pattern from your working GitHub repository
    https://github.com/ahmedkhamis12/GitHub-Sync-Webhook-Service
    """
    
    def __init__(self):
        try:
            # Use the exact same pattern as your working Flask example
            self.client = docker.from_env()  # Connect to Docker daemon
            self.docker_available = True
            logger.info("Docker client initialized successfully using Flask pattern")
        except Exception as e:
            self.client = None
            self.docker_available = False
            logger.error(f"Docker initialization failed: {e}")
    
    def extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from Git URL - exact copy from your code"""
        if not repo_url:
            return None
        # Example: "git@github.com:user/odoo-project.git" -> "odoo-project"
        return repo_url.split("/")[-1].replace(".git", "")
    
    def pull_repo(self, repo_dir: str, repo_url: str) -> Tuple[bool, str]:
        """Clone or pull Git repository - exact copy from your code"""
        try:
            if not os.path.isdir(repo_dir):
                logger.info(f"Cloning repo {repo_url} into {repo_dir}")
                subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
                return True, f"Successfully cloned {repo_url}"
            else:
                logger.info(f"Pulling latest changes in {repo_dir}")
                subprocess.run(["git", "-C", repo_dir, "pull"], check=True)
                return True, f"Successfully pulled latest changes"
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Git operation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def restart_containers(self, label: str) -> Tuple[int, List[str]]:
        """
        Restart all Docker containers that have a specific label
        Exact copy of your working Flask implementation
        """
        if not self.docker_available:
            return 0, [f"Docker not available - cannot restart containers with label: {label}"]
        
        results = []
        success_count = 0
        
        try:
            # Use exact same pattern as your Flask example
            containers = self.client.containers.list(filters={"label": label})
            
            if not containers:
                message = f"No containers found with label: {label}"
                logger.info(message)
                return 0, [message]
            
            # Restart each container - exact same pattern as your example
            for container in containers:
                try:
                    logger.info(f"Restarting container {container.name}")
                    container.restart()  # Direct restart call like your example
                    success_count += 1
                    results.append(f"Successfully restarted container {container.name}")
                except Exception as e:
                    error_msg = f"Failed to restart {container.name}: {str(e)}"
                    logger.error(error_msg)
                    results.append(error_msg)
            
            return success_count, results
            
        except Exception as e:
            error_msg = f"Error accessing Docker: {str(e)}"
            logger.error(error_msg)
            return 0, [error_msg]
    
    def process_webhook_like_flask(self, repo_name: str, repo_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook exactly like your Flask implementation
        """
        result = {
            "success": False,
            "message": "",
            "git_result": "",
            "container_results": []
        }
        
        try:
            # Step 1: Pull repository (exact Flask pattern)
            pull_success, pull_message = self.pull_repo(repo_config["dir"], repo_config["url"])
            result["git_result"] = pull_message
            
            if not pull_success:
                result["message"] = f"Git command failed: {pull_message}"
                return result
            
            # Step 2: Restart containers (exact Flask pattern)
            success_count, restart_results = self.restart_containers(repo_config["label"])
            result["container_results"] = restart_results
            
            if success_count > 0:
                result["success"] = True
                result["message"] = f"Updated and restarted containers for {repo_name}"
            else:
                result["message"] = f"Repository updated but no containers restarted for {repo_name}"
            
            return result
            
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
            logger.error(f"Webhook processing error: {e}")
            return result
    
    def get_containers_with_label(self, label: str) -> List:
        """Get all containers with a specific label"""
        if not self.docker_available:
            return []
        
        try:
            return self.client.containers.list(filters={"label": label})
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
            return []