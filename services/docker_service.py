import json
import os
import subprocess
import shutil
import docker
import docker.errors
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from models import Container, OperationLog, Repository
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DockerService:
    def __init__(self, db: Session):
        self.db = db
        self.docker_available = False
        self.docker_error = None
        
        try:
            # Check if Docker socket exists
            import os
            import subprocess
            socket_path = '/var/run/docker.sock'
            if os.path.exists(socket_path):
                logger.info(f"Docker socket found at {socket_path}")
                # Check socket permissions
                import stat
                socket_stat = os.stat(socket_path)
                socket_perms = stat.filemode(socket_stat.st_mode)
                logger.info(f"Socket permissions: {socket_perms}")
            else:
                logger.warning(f"Docker socket not found at {socket_path}")
            
            # Try multiple Docker connection methods
            self.client = None
            
            # Method 1: Default docker from env
            try:
                self.client = docker.from_env()
                self.client.ping()
                self.docker_available = True
                logger.info("Docker client initialized via docker.from_env()")
            except Exception as e:
                logger.debug(f"docker.from_env() failed: {e}")
            
            # Method 2: Unix socket
            if not self.docker_available:
                try:
                    self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
                    self.client.ping()
                    self.docker_available = True
                    logger.info("Docker client initialized via unix socket")
                except Exception as e:
                    logger.debug(f"Unix socket connection failed: {e}")
                    self.docker_error = str(e)
            
            # Method 3: TCP connection
            if not self.docker_available:
                try:
                    self.client = docker.DockerClient(base_url='tcp://localhost:2376')
                    self.client.ping()
                    self.docker_available = True
                    logger.info("Docker client initialized via TCP")
                except Exception as e:
                    logger.debug(f"TCP connection failed: {e}")
                    
            if not self.docker_available:
                logger.warning(f"Docker not accessible - using demonstration mode. Last error: {self.docker_error}")
                self.client = None
                
        except Exception as e:
            logger.error(f"Docker initialization failed: {e}")
            self.docker_error = str(e)
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
                "id": "server-backend-app",
                "name": "server-backend-app",
                "image": "node:18-alpine",
                "status": "running",
                "labels": {"restart-after": "server-backend", "app": "backend"},
                "restart_after": "server-backend",
                "message": "Backend application container"
            },
            {
                "id": "frontend-web-app",
                "name": "frontend-web-app", 
                "image": "nginx:alpine",
                "status": "running",
                "labels": {"restart-after": "frontend-web", "app": "frontend"},
                "restart_after": "frontend-web",
                "message": "Frontend web application"
            },
            {
                "id": "api-service-container",
                "name": "api-service-container",
                "image": "python:3.11-slim",
                "status": "running",
                "labels": {"restart-after": "api-service", "app": "api"},
                "restart_after": "api-service",
                "message": "API service container"
            },
            {
                "id": "worker-queue-service",
                "name": "worker-queue-service",
                "image": "redis:alpine",
                "status": "running",
                "labels": {"restart-after": "worker-queue", "app": "queue"},
                "restart_after": "worker-queue",
                "message": "Background worker queue"
            },
            {
                "id": "database-postgres",
                "name": "database-postgres",
                "image": "postgres:15-alpine",
                "status": "running",
                "labels": {"app": "database"},
                "restart_after": None,
                "message": "Database container - no restart needed"
            },
            {
                "id": "monitoring-grafana",
                "name": "monitoring-grafana",
                "image": "grafana/grafana:latest",
                "status": "running",
                "labels": {"app": "monitoring"},
                "restart_after": None,
                "message": "Monitoring dashboard"
            }
        ]
        
        # Combine demo and real containers
        all_containers = demo_containers + real_containers
        current_container_ids = {c["id"] for c in all_containers}
        
        # Add or update containers in database
        logger.info("Updating container configurations in database")
        for container_data in all_containers:
            try:
                existing = self.db.query(Container).filter_by(container_id=container_data["id"]).first()
                if existing:
                    # Update existing container
                    existing.name = container_data["name"]
                    existing.image = container_data["image"]
                    existing.status = container_data["status"]
                    existing.labels = json.dumps(container_data["labels"])
                    existing.restart_after_pull = container_data["restart_after"] if container_data["restart_after"] else None
                else:
                    # Create new container
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
        
        # Remove containers from database that no longer exist in demonstration data
        db_containers = self.db.query(Container).all()
        containers_to_remove = []
        
        for db_container in db_containers:
            if db_container.container_id not in current_container_ids:
                containers_to_remove.append(db_container)
        
        if containers_to_remove:
            logger.info(f"Removing {len(containers_to_remove)} containers no longer in demonstration data:")
            for container in containers_to_remove:
                logger.info(f"  - Removing: {container.name} (ID: {container.container_id})")
                self.db.delete(container)
        
        try:
            self.db.commit()
            logger.info("Container configurations committed to database")
        except Exception as e:
            logger.error(f"Error saving containers: {e}")
            self.db.rollback()
        
        return all_containers
    
    def _discover_real_containers(self) -> List[Dict]:
        """Discover real Docker containers when Docker is available"""
        try:
            containers = self.client.containers.list(all=True)
            container_list = []
            current_container_ids = set()
            
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
                current_container_ids.add(container.id)
                
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
                        restart_after_pull=container_data["restart_after"]
                    )
                    self.db.add(db_container)
            
            # Remove containers from database that no longer exist in Docker
            db_containers = self.db.query(Container).all()
            containers_to_remove = []
            
            for db_container in db_containers:
                if db_container.container_id not in current_container_ids:
                    containers_to_remove.append(db_container)
            
            if containers_to_remove:
                logger.info(f"Removing {len(containers_to_remove)} containers that no longer exist in Docker:")
                for container in containers_to_remove:
                    logger.info(f"  - Removing: {container.name} (ID: {container.container_id})")
                    self.db.delete(container)
            
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
    
    def restart_containers_by_label(self, repository_name: str) -> Tuple[int, List[str]]:
        """Restart all Docker containers that have a specific restart-after label"""
        results = []
        success_count = 0
        
        if self.docker_available:
            try:
                # Use Docker API to find containers with the restart-after label
                filters = {"label": f"restart-after={repository_name}"}
                containers = self.client.containers.list(filters=filters)
                
                if not containers:
                    logger.info(f"No containers found with label: restart-after={repository_name}")
                    return 0, [f"No containers found with restart-after={repository_name} label"]
                
                for container in containers:
                    try:
                        logger.info(f"Restarting container {container.name}")
                        container.restart()
                        success_count += 1
                        results.append(f"Successfully restarted container {container.name}")
                        
                        # Update database record if exists
                        db_container = self.db.query(Container).filter_by(container_id=container.id).first()
                        if db_container:
                            db_container.last_restart_success = True
                            db_container.last_restart_time = datetime.utcnow()
                            db_container.last_restart_error = None
                            
                    except Exception as e:
                        error_msg = f"Failed to restart {container.name}: {str(e)}"
                        logger.error(error_msg)
                        results.append(error_msg)
                        
                        # Update database record if exists
                        db_container = self.db.query(Container).filter_by(container_id=container.id).first()
                        if db_container:
                            db_container.last_restart_success = False
                            db_container.last_restart_time = datetime.utcnow()
                            db_container.last_restart_error = error_msg
                
                self.db.commit()
                
            except Exception as e:
                error_msg = f"Error accessing Docker API: {str(e)}"
                logger.error(error_msg)
                results.append(error_msg)
        else:
            # Fallback to database-tracked containers when Docker API unavailable
            containers = self.get_containers_for_repository(repository_name)
            if not containers:
                return 0, [f"No containers configured for repository {repository_name}"]
            
            for container in containers:
                success, message = self.restart_container(container)
                if success:
                    success_count += 1
                    results.append(f"Restarted {container.name}: {message}")
                else:
                    results.append(f"Failed {container.name}: {message}")
        
        return success_count, results
    
    def restart_container(self, container: Container) -> Tuple[bool, str]:
        """Restart a Docker container"""
        try:
            if self.docker_available:
                try:
                    # Try direct Docker restart
                    docker_container = self.client.containers.get(container.container_id)
                    logger.info(f"Restarting container {container.name} ({container.container_id})")
                    docker_container.restart()
                    success_msg = f"Successfully restarted container {container.name} via Docker API"
                except docker.errors.NotFound:
                    error_msg = f"Container {container.name} ({container.container_id}) not found in Docker"
                    logger.error(error_msg)
                    
                    container.last_restart_success = False
                    container.last_restart_time = datetime.utcnow()
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
                except docker.errors.APIError as e:
                    error_msg = f"Docker API error restarting {container.name}: {str(e)}"
                    logger.error(error_msg)
                    
                    container.last_restart_success = False
                    container.last_restart_time = datetime.utcnow()
                    container.last_restart_error = error_msg
                    
                    # Log operation
                    log_entry = OperationLog(
                        operation_type="restart",
                        container_id=container.container_id,
                        status="error",
                        message=f"Docker API error restarting container {container.name}",
                        details=error_msg
                    )
                    self.db.add(log_entry)
                    self.db.commit()
                    
                    return False, error_msg
            else:
                # Try different methods to restart container when API not available
                logger.info(f"Attempting container restart for {container.name} using fallback methods")
                
                # Method 1: Try docker command with different paths
                docker_paths = [
                    '/usr/bin/docker',
                    '/usr/local/bin/docker', 
                    'docker'
                ]
                
                success = False
                error_msg = None
                
                for docker_cmd in docker_paths:
                    try:
                        # Check if docker command exists
                        if docker_cmd == 'docker':
                            if not shutil.which('docker'):
                                continue
                        elif not os.path.exists(docker_cmd):
                            continue
                            
                        logger.info(f"Trying docker restart with command: {docker_cmd}")
                        result = subprocess.run([docker_cmd, 'restart', str(container.container_id)], 
                                              capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            success_msg = f"Successfully restarted container {container.name} via {docker_cmd}"
                            logger.info(success_msg)
                            success = True
                            break
                        else:
                            error_msg = f"Docker restart failed: {result.stderr.strip()}"
                            logger.warning(f"Docker command {docker_cmd} failed: {error_msg}")
                            
                    except subprocess.TimeoutExpired:
                        error_msg = f"Docker restart command timed out for {container.name}"
                        logger.warning(error_msg)
                        continue
                        
                    except FileNotFoundError:
                        logger.debug(f"Docker command not found at {docker_cmd}")
                        continue
                        
                    except Exception as e:
                        error_msg = f"Error with docker command {docker_cmd}: {str(e)}"
                        logger.warning(error_msg)
                        continue
                
                if not success:
                    # Method 2: Try docker-compose restart if available
                    try:
                        logger.info(f"Trying docker-compose restart for {container.name}")
                        result = subprocess.run(['docker-compose', 'restart', str(container.name)], 
                                              capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            success_msg = f"Successfully restarted container {container.name} via docker-compose"
                            logger.info(success_msg)
                            success = True
                        else:
                            logger.debug(f"docker-compose restart failed: {result.stderr}")
                    except:
                        logger.debug("docker-compose restart failed")
                
                if not success:
                    # Final fallback - report the issue with diagnostic info
                    diagnostic_info = f"Docker socket accessible: {os.path.exists('/var/run/docker.sock')}, "
                    diagnostic_info += f"Last Docker error: {self.docker_error or 'Unknown'}"
                    
                    final_error = f"Cannot restart container {container.name} - no working Docker method found. {diagnostic_info}"
                    logger.error(final_error)
                    
                    container.last_restart_success = False
                    container.last_restart_time = datetime.utcnow()
                    container.last_restart_error = final_error
                    
                    # Log operation
                    log_entry = OperationLog(
                        operation_type="restart",
                        container_id=container.container_id,
                        status="error",
                        message=f"Failed to restart container {container.name}",
                        details=final_error
                    )
                    self.db.add(log_entry)
                    self.db.commit()
                    
                    return False, final_error
                    
                success_msg = f"Successfully restarted container {container.name} via command line"
            
            # Update container record
            container.last_restart_success = True
            container.last_restart_time = datetime.utcnow()
            container.last_restart_error = None
            if self.docker_available:
                container.status = "running"
            
            # Log operation
            log_entry = OperationLog(
                operation_type="restart",
                container_id=container.container_id,
                status="success",
                message=f"Successfully restarted container {container.name}",
                details=f"Container ID: {container.container_id}, Docker available: {self.docker_available}"
            )
            self.db.add(log_entry)
            self.db.commit()
            
            logger.info(success_msg)
            return True, success_msg
            
        except Exception as e:
            error_msg = f"Unexpected error restarting container {container.name}: {str(e)}"
            logger.error(error_msg)
            
            container.last_restart_success = False
            container.last_restart_time = datetime.utcnow()
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
