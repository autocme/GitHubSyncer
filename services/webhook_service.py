import asyncio
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from models import Repository, OperationLog
from services.git_service import GitService
from services.docker_service import DockerService
from utils.logger import setup_logger
from utils.helpers import extract_repo_name_from_url

logger = setup_logger(__name__)

class WebhookService:
    def __init__(self, db: Session):
        self.db = db
        self.git_service = GitService(db)
        self.docker_service = DockerService(db)
    
    async def process_github_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process GitHub webhook payload"""
        try:
            # Extract repository information from payload
            repo_info = payload.get("repository", {})
            repo_name = repo_info.get("name")
            
            if not repo_name:
                error_msg = "Repository name not found in webhook payload"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            logger.info(f"Processing webhook for repository: {repo_name}")
            
            # Find matching repository in database
            repository = self.db.query(Repository).filter(
                Repository.name == repo_name,
                Repository.is_active == True
            ).first()
            
            if not repository:
                error_msg = f"Repository {repo_name} not found or inactive"
                logger.warning(error_msg)
                return {"success": False, "message": error_msg}
            
            # Process the repository update
            return await self._process_repository_update(repository)
            
        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}"
            logger.error(error_msg)
            
            # Log the error
            log_entry = OperationLog(
                operation_type="webhook",
                status="error",
                message="Webhook processing failed",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return {"success": False, "message": error_msg}
    
    async def _process_repository_update(self, repository: Repository) -> Dict[str, Any]:
        """Process repository update (pull and restart containers)"""
        results = {
            "repository": repository.name,
            "pull_success": False,
            "pull_message": "",
            "containers_restarted": [],
            "errors": []
        }
        
        try:
            # Step 1: Pull repository changes
            logger.info(f"Pulling repository: {repository.name}")
            pull_success, pull_message = self.git_service.pull_repository(repository)
            
            results["pull_success"] = pull_success
            results["pull_message"] = pull_message
            
            if not pull_success:
                results["errors"].append(f"Pull failed: {pull_message}")
                return results
            
            # Step 2: Restart associated containers
            logger.info(f"Restarting containers for repository: {repository.name}")
            container_results = self.docker_service.restart_containers_for_repository(repository.name)
            
            for container_name, restart_success, restart_message in container_results:
                container_result = {
                    "name": container_name,
                    "success": restart_success,
                    "message": restart_message
                }
                results["containers_restarted"].append(container_result)
                
                if not restart_success:
                    results["errors"].append(f"Container {container_name}: {restart_message}")
            
            # Log successful operation
            log_entry = OperationLog(
                operation_type="webhook",
                repository_id=repository.id,
                status="success",
                message=f"Successfully processed webhook for {repository.name}",
                details=f"Pulled code and restarted {len(container_results)} containers"
            )
            self.db.add(log_entry)
            self.db.commit()
            
            success_msg = f"Successfully processed webhook for {repository.name}"
            logger.info(success_msg)
            
            return {
                "success": True,
                "message": success_msg,
                **results
            }
            
        except Exception as e:
            error_msg = f"Error processing repository update for {repository.name}: {str(e)}"
            logger.error(error_msg)
            
            results["errors"].append(error_msg)
            
            # Log the error
            log_entry = OperationLog(
                operation_type="webhook",
                repository_id=repository.id,
                status="error",
                message=f"Failed to process webhook for {repository.name}",
                details=error_msg
            )
            self.db.add(log_entry)
            self.db.commit()
            
            return {
                "success": False,
                "message": error_msg,
                **results
            }
    
    def validate_webhook_payload(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate GitHub webhook payload"""
        try:
            # Check if it's a push event
            if "repository" not in payload:
                return False, "Invalid webhook payload: missing repository information"
            
            repo_info = payload.get("repository", {})
            if not repo_info.get("name"):
                return False, "Invalid webhook payload: missing repository name"
            
            # Additional validation can be added here
            # For example, checking for specific branches, commit messages, etc.
            
            return True, "Valid webhook payload"
            
        except Exception as e:
            return False, f"Error validating webhook payload: {str(e)}"
    
    async def manual_sync_repository(self, repository_id: int) -> Dict[str, Any]:
        """Manually sync a repository (for API/GUI use)"""
        try:
            repository = self.db.query(Repository).filter(
                Repository.id == repository_id,
                Repository.is_active == True
            ).first()
            
            if not repository:
                return {"success": False, "message": "Repository not found or inactive"}
            
            return await self._process_repository_update(repository)
            
        except Exception as e:
            error_msg = f"Error in manual sync: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
    
    async def sync_all_repositories(self) -> List[Dict[str, Any]]:
        """Sync all active repositories"""
        results = []
        
        try:
            repositories = self.db.query(Repository).filter(
                Repository.is_active == True
            ).all()
            
            for repository in repositories:
                logger.info(f"Syncing repository: {repository.name}")
                result = await self._process_repository_update(repository)
                results.append(result)
                
                # Add small delay between repositories to avoid overwhelming the system
                await asyncio.sleep(1)
            
            return results
            
        except Exception as e:
            error_msg = f"Error syncing all repositories: {str(e)}"
            logger.error(error_msg)
            return [{"success": False, "message": error_msg}]
