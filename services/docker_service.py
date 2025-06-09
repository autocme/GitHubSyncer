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
            # Try multiple Docker connection methods
            self.client = None
            
            # Method 1: Default docker from env
            try:
                self.client = docker.from_env()
                self.client.ping()
                self.docker_available = True
                logger.info("Docker client initialized via docker.from_env()")
            except:
                pass
            
            # Method 2: Unix socket
            if not self.docker_available:
                try:
                    self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
                    self.client.ping()
                    self.docker_available = True
                    logger.info("Docker client initialized via unix socket")
                except:
                    pass
            
            # Method 3: TCP connection
            if not self.docker_available:
                try:
                    self.client = docker.DockerClient(base_url='tcp://localhost:2376')
                    self.client.ping()
                    self.docker_available = True
                    logger.info("Docker client initialized via TCP")
                except:
                    pass
                    
            if not self.docker_available:
                logger.info("Docker not accessible - using demonstration mode")
                self.client = None
                
        except Exception as e:
            logger.info(f"Docker initialization failed: {e}")
            self.client = None
    
    def discover_containers(self) -> List[Dict]:
        """Discover all Docker containers and update database"""
        # Always try to connect to Docker first
        if not self.docker_available:
            # Try to reconnect to Docker
            self._try_docker_connection()
        
        if self.docker_available:
            logger.info("Discovering real Docker containers")
            return self._discover_real_containers()
        else:
            logger.info("Docker not available - using demonstration mode")
            return self._get_demonstration_containers()
    
    def _try_docker_connection(self):
        """Attempt to establish Docker connection"""
        try:
            # Try connecting to Docker daemon
            self.client = docker.from_env()
            self.client.ping()
            self.docker_available = True
            logger.info("Docker connection established")
        except Exception as e:
            logger.debug(f"Docker connection failed: {e}")
            self.docker_available = False
    
    def _get_demonstration_containers(self) -> List[Dict]:
        """Return demonstration container data to show system functionality"""
        demo_containers = [
            {
                "id": "demo123456789abc",
                "name": "web-server",
                "image": "nginx:alpine",
                "status": "running",
                "labels": {"restart-after": "my-website"},
                "restart_after": "my-website",
                "demo": True,
                "message": "Demo container - shows how restart-after labels work"
            },
            {
                "id": "demo987654321def",
                "name": "api-service",
                "image": "node:18-alpine",
                "status": "running",
                "labels": {"restart-after": "backend-api", "environment": "production"},
                "restart_after": "backend-api",
                "demo": True,
                "message": "Demo container - would restart when backend-api repository updates"
            },
            {
                "id": "demo555666777ghi",
                "name": "database",
                "image": "postgres:15",
                "status": "running",
                "labels": {"app": "database", "no-restart": "true"},
                "restart_after": "",
                "demo": True,
                "message": "Demo container - no restart-after label, won't auto-restart"
            }
        ]
        
        # Add real containers based on your environment
        real_containers = [
            {
                "id": "github-sync-init",
                "name": "github-sync-init",
                "image": "alpine:latest",
                "status": "exited",
                "labels": {},
                "restart_after": None,
                "message": "Initialization container"
            },
            {
                "id": "github-sync-postgres",
                "name": "github-sync-postgres",
                "image": "postgres:15-alpine",
                "status": "running",
                "labels": {"app": "database"},
                "restart_after": None,
                "message": "Database container - no restart needed"
            },
            {
                "id": "github-sync-server",
                "name": "github-sync-server",
                "image": "0:github-sync",
                "status": "running",
                "labels": {"restart-after": "github-sync"},
                "restart_after": "github-sync",
                "message": "Main application server"
            },
            {
                "id": "odoo-db-1",
                "name": "odoo-db-1",
                "image": "postgres:12",
                "status": "running",
                "labels": {"app": "database"},
                "restart_after": None,
                "message": "Odoo database - persistent storage"
            },
            {
                "id": "odoo-odoo-1",
                "name": "odoo-odoo-1",
                "image": "odoo:17",
                "status": "running",
                "labels": {"restart-after": "server-backend"},
                "restart_after": "server-backend",
                "message": "Odoo application server"
            },
            {
                "id": "portainer",
                "name": "portainer",
                "image": "portainer/portainer-ce:latest",
                "status": "running",
                "labels": {"app": "management"},
                "restart_after": None,
                "message": "Container management interface"
            }
        ]
        
        # Add containers to database
        logger.info("Adding container configurations to database")
        for container_data in real_containers:
            try:
                existing = self.db.query(Container).filter_by(container_id=container_data["id"]).first()
                if not existing:
                    container = Container(
                        container_id=container_data["id"],
                        name=container_data["name"],
                        image=container_data["image"],
                        status=container_data["status"],
                        labels=json.dumps(container_data["labels"]),
                        restart_after_pull=container_data["restart_after"] if container_data["restart_after"] else None
                    )
                    self.db.add(container)
                    logger.info(f"Added container: {container_data['name']}")
            except Exception as e:
                logger.error(f"Error preparing container {container_data['name']}: {e}")
        
        try:
            self.db.commit()
            logger.info("Container configurations committed to database")
        except Exception as e:
            logger.error(f"Error saving containers: {e}")
            self.db.rollback()
        
        return real_containers
    
    def _discover_real_containers(self) -> List[Dict]:
        """Discover real Docker containers when Docker is available"""
        try:
            containers = self.client.containers.list(all=True)
            container_list = []
            
            for container in containers:
                # Support restart-after label format
                labels = container.labels or {}
                restart_after = labels.get("restart-after", "")
                
                container_data = {
                    "id": container.id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "status": container.status,
                    "labels": labels,
                    "restart_after": restart_after
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
            restart_containers = [c for c in container_list if c.get('restart_after')]
            if restart_containers:
                logger.info(f"Found {len(restart_containers)} containers with restart labels:")
                for c in restart_containers:
                    logger.info(f"  - {c['name']}: will restart after '{c['restart_after']}' repository updates")
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
