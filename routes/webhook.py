from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from database import get_db
from services.webhook_service import WebhookService
from utils.logger import setup_logger
import json

logger = setup_logger(__name__)
router = APIRouter()

@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub webhook"""
    try:
        # Get webhook payload
        payload = await request.json()
        
        logger.info(f"Received GitHub webhook: {json.dumps(payload, indent=2)}")
        
        # Process webhook
        webhook_service = WebhookService(db)
        
        # Validate payload
        is_valid, validation_message = webhook_service.validate_webhook_payload(payload)
        if not is_valid:
            logger.warning(f"Invalid webhook payload: {validation_message}")
            raise HTTPException(status_code=400, detail=validation_message)
        
        # Process webhook
        result = await webhook_service.process_github_webhook(payload)
        
        # Handle response safely
        success = result.get("success", False)
        message = result.get("message", "Unknown result")
        
        if success:
            logger.info(f"Webhook processed successfully: {message}")
            return {
                "status": "success",
                "message": message,
                "details": result
            }
        else:
            logger.error(f"Webhook processing failed: {message}")
            return {
                "status": "error",
                "message": message,
                "details": result
            }
    
    except json.JSONDecodeError:
        error_msg = "Invalid JSON payload"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    except Exception as e:
        error_msg = f"Error processing webhook: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/test")
async def test_webhook(db: Session = Depends(get_db)):
    """Test webhook endpoint"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@router.post("/test-repository/{repo_name}")
async def test_repository_webhook(repo_name: str, db: Session = Depends(get_db)):
    """Test webhook for a specific repository"""
    try:
        # Create test payload
        test_payload = {
            "repository": {
                "name": repo_name
            },
            "ref": "refs/heads/main",
            "head_commit": {
                "id": "test-commit-id",
                "message": "Test webhook",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com"
                }
            }
        }
        
        # Process webhook
        webhook_service = WebhookService(db)
        result = await webhook_service.process_github_webhook(test_payload)
        
        return {
            "status": "test_completed",
            "repository": repo_name,
            "result": result
        }
        
    except Exception as e:
        error_msg = f"Error testing webhook for repository {repo_name}: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
