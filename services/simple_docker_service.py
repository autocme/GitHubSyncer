import docker
from typing import List, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SimpleDockerService:
    """
    Simplified Docker service using the exact pattern from your working example
    """
    
    def __init__(self):
        try:
            # Use the exact same pattern as your working Flask example
            self.client = docker.from_env()  # Connect to Docker daemon
            self.docker_available = True
            logger.info("Docker client initialized successfully")
        except Exception as e:
            self.client = None
            self.docker_available = False
            logger.error(f"Docker initialization failed: {e}")
    
    def restart_containers_by_label(self, label_value: str) -> Tuple[int, List[str]]:
        """
        Restart all Docker containers that have a specific label
        Uses the exact pattern from your working example
        """
        if not self.docker_available:
            return 0, [f"Docker not available - cannot restart containers for {label_value}"]
        
        results = []
        success_count = 0
        
        try:
            # Use exact same pattern as your example: client.containers.list(filters={"label": label})
            containers = self.client.containers.list(filters={"label": f"restart-after={label_value}"})
            
            if not containers:
                message = f"No containers found with label: restart-after={label_value}"
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
    
    def get_containers_with_label(self, label_value: str) -> List:
        """Get all containers with a specific restart-after label"""
        if not self.docker_available:
            return []
        
        try:
            return self.client.containers.list(filters={"label": f"restart-after={label_value}"})
        except Exception as e:
            logger.error(f"Error getting containers: {e}")
            return []