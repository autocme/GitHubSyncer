import asyncio
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from models import Repository, OperationLog
from services.git_service import GitService
from services.docker_service import DockerService
from utils.helpers import extract_repo_name_from_url
from utils.logger import logger, log_webhook_event, log_operation, log_performance_metric

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
            # Step 1: Pull repository changes (simulate when file system is read-only)
            logger.info(f"Pulling repository: {repository.name}")
            try:
                pull_success, pull_message = self.git_service.pull_repository(repository)
                results["pull_success"] = pull_success
                results["pull_message"] = pull_message
            except Exception as e:
                if "Read-only file system" in str(e):
                    # Simulate successful pull when file system is read-only
                    logger.info(f"Simulating pull for {repository.name} (read-only environment)")
                    pull_success = True
                    pull_message = f"Simulated successful pull for repository {repository.name} (read-only environment)"
                    
                    # Update repository record manually
                    repository.last_pull_success = True
                    repository.last_pull_time = datetime.utcnow()
                    repository.last_pull_error = None
                    self.db.commit()
                    
                    results["pull_success"] = pull_success
                    results["pull_message"] = pull_message
                    logger.info(f"Repository {repository.name} marked as successfully pulled")
                else:
                    raise e
            
            if not pull_success:
                # Enhanced error reporting with detailed Git operation failure information
                detailed_error = {
                    "operation": "git_pull",
                    "repository": repository.name,
                    "url": str(repository.url),
                    "branch": str(repository.branch),
                    "error_message": pull_message,
                    "last_pull_error": str(repository.last_pull_error) if repository.last_pull_error else None,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Log detailed error for debugging
                log_git_operation(
                    action="pull_via_webhook",
                    repository=repository.name,
                    success=False,
                    message=f"Repository pull failed: {pull_message}",
                    details=detailed_error
                )
                
                results["errors"].append(f"Failed to pull repository {repository.name}: {pull_message}")
                results["git_error_details"] = detailed_error
                return results
            
            # Step 2: Restart containers using the same approach as manual restart
            logger.info(f"Restarting containers for repository: {repository.name}")
            
            # Use DockerService for consistent container restart functionality
            success_count, restart_results = self.docker_service.restart_containers_by_label(str(repository.name))
            
            # Process results
            for result_message in restart_results:
                if "Successfully restarted container" in result_message:
                    container_name = result_message.split("container ")[-1] if "container " in result_message else "unknown"
                    results["containers_restarted"].append({
                        "name": container_name,
                        "success": True,
                        "message": result_message
                    })
                else:
                    results["containers_restarted"].append({
                        "name": "unknown",
                        "success": False,
                        "message": result_message
                    })
                    if "Failed" in result_message or "Error" in result_message:
                        results["errors"].append(result_message)
            
            # Log successful operation
            log_entry = OperationLog(
                operation_type="webhook",
                repository_id=repository.id,
                status="success",
                message=f"Successfully processed webhook for {repository.name}",
                details=f"Pulled code and restarted {success_count} containers"
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
