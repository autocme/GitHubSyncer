import json
import docker
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from models import Container, OperationLog, Repository
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DockerService:
    def __init__(self, db: Session):
        self.db = db
        self.docker_available = False
        try:
            self.client = docker.from_env()
            self.client.ping()  # Test connection
            self.docker_available = True
            logger.info("Docker client initialized successfully")
        except Exception as e:
            # Only log at debug level to reduce noise
            logger.debug(f"Docker client not available: {e}")
            self.client = None
    
    def discover_containers(self) -> List[Dict]:
        """Discover all Docker containers and update database"""
        if not self.docker_available:
            return [{
                "error": "Docker not available",
                "message": "Docker socket not accessible. This is normal when running outside Docker.",
                "suggestion": "Deploy using Docker Compose for full container management features"
            }]
        
        try:
            containers = self.client.containers.list(all=True)
            container_list = []
            
            for container in containers:
                # Support multiple label formats for restart functionality
                labels = container.labels or {}
                restart_after = (
                    labels.get("restart_after_pull") or 
                    labels.get("github-sync.restart-after") or 
                    labels.get("restart-after") or
                    ""
                )
                
                container_data = {
                    "id": container.id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "status": container.status,
                    "labels": labels,
                    "restart_after_pull": restart_after
                }
                
                container_list.append(container_data)
                
                # Update or create container record in database
                db_container = self.db.query(Container).filter(
                    Container.container_id == container.id
                ).first()
                
                if db_container:
                    # Update existing record
                    db_container.name = container.name
                    db_container.image = container_data["image"]
                    db_container.status = container.status
                    db_container.labels = json.dumps(container.labels)
                    db_container.restart_after_pull = restart_after
                else:
                    # Create new record
                    db_container = Container(
                        container_id=container.id,
                        name=container.name,
                        image=container_data["image"],
                        status=container.status,
                        labels=json.dumps(container.labels),
                        restart_after_pull=container_data["restart_after_pull"]
                    )
                    self.db.add(db_container)
            
            self.db.commit()
            logger.info(f"Discovered {len(container_list)} containers")
            
            # Log containers with restart labels
            restart_containers = [c for c in container_list if c.get('restart_after_pull')]
            if restart_containers:
                logger.info(f"Found {len(restart_containers)} containers with restart labels:")
                for c in restart_containers:
                    logger.info(f"  - {c['name']}: will restart after '{c['restart_after_pull']}' repository updates")
            else:
                logger.info("No containers found with restart labels")
            
            return container_list
            
        except Exception as e:
            logger.error(f"Failed to discover containers: {e}")
            return []
    
    def get_containers_for_repository(self, repository_name: str) -> List[Container]:
        """Get containers that should be restarted for a specific repository"""
        try:
            containers = self.db.query(Container).filter(
                Container.restart_after_pull == repository_name,
                Container.status.in_(["running", "exited"])  # Only restart manageable containers
            ).all()
            
            logger.info(f"Found {len(containers)} containers to restart for repository {repository_name}")
            return containers
            
        except Exception as e:
            logger.error(f"Failed to get containers for repository {repository_name}: {e}")
            return []
    
    def restart_container(self, container: Container) -> Tuple[bool, str]:
        """Restart a Docker container"""
        if not self.docker_available:
            error_msg = "Docker not available - container restart skipped (normal when running outside Docker)"
            logger.debug(error_msg)
            return False, error_msg
        
        try:
            docker_container = self.client.containers.get(container.container_id)
            
            logger.info(f"Restarting container {container.name} ({container.container_id})")
            docker_container.restart()
            
            # Update container record
            container.last_restart_success = True
            container.last_restart_time = None
            container.last_restart_error = None
            container.status = "running"
            
            # Log operation
            log_entry = OperationLog(
                operation_type="restart",
                container_id=container.container_id,
                status="success",
                message=f"Successfully restarted container {container.name}",
                details=f"Container ID: {container.container_id}"
            )
            self.db.add(log_entry)
            self.db.commit()
            
            success_msg = f"Successfully restarted container {container.name}"
            logger.info(success_msg)
            return True, success_msg
            
        except docker.errors.NotFound:
            error_msg = f"Container {container.name} not found"
            logger.error(error_msg)
            
            container.last_restart_success = False
            container.last_restart_error = error_msg
            
            # Log operation
            log_entry = OperationLog(
                operation_type="restart",
                container_id=container.container_id,
                status="error",
                message=f"Container {container.name} not found",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Failed to restart container {container.name}: {str(e)}"
            logger.error(error_msg)
            
            container.last_restart_success = False
            container.last_restart_error = error_msg
            
            # Log operation
            log_entry = OperationLog(
                operation_type="restart",
                container_id=container.container_id,
                status="error",
                message=f"Failed to restart container {container.name}",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return False, error_msg
    
    def restart_containers_for_repository(self, repository_name: str) -> List[Tuple[str, bool, str]]:
        """Restart all containers associated with a repository"""
        results = []
        containers = self.get_containers_for_repository(repository_name)
        
        for container in containers:
            success, message = self.restart_container(container)
            results.append((container.name, success, message))
        
        return results
    
    def get_container_status(self, container_id: str) -> Optional[Dict]:
        """Get detailed status of a container"""
        if not self.client:
            return None
        
        try:
            container = self.client.containers.get(container_id)
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "started": container.attrs["State"].get("StartedAt"),
                "labels": container.labels,
                "ports": container.ports,
                "mounts": [mount["Source"] + ":" + mount["Destination"] for mount in container.attrs["Mounts"]]
            }
            
        except Exception as e:
            logger.error(f"Failed to get container status for {container_id}: {e}")
            return None
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and accessible"""
        return self.client is not None
    
    def get_docker_info(self) -> Optional[Dict]:
        """Get Docker system information"""
        if not self.client:
            return None
        
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Failed to get Docker info: {e}")
            return None
