import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models import User, ApiKey, Setting, LoginAttempt
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.secret_key = self._get_or_create_secret_key()
    
    def _get_or_create_secret_key(self) -> str:
        """Get or create JWT secret key"""
        setting = self.db.query(Setting).filter(Setting.key == "jwt_secret").first()
        if not setting:
            secret = secrets.token_urlsafe(32)
            setting = Setting(
                key="jwt_secret",
                value=secret,
                description="JWT secret key for authentication"
            )
            self.db.add(setting)
            self.db.commit()
        return setting.value
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    def create_user(self, username: str, password: str, email: str = None) -> Tuple[bool, str]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(User.username == username).first()
            if existing_user:
                return False, "Username already exists"
            
            # Create new user
            user = User(
                username=username,
                password_hash=self.hash_password(password),
                email=email,
                is_active=True
            )
            
            self.db.add(user)
            self.db.commit()
            
            logger.info(f"Created new user: {username}")
            return True, "User created successfully"
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return False, f"Error creating user: {str(e)}"
    
    def check_login_rate_limit(self, username: str, ip_address: str) -> Tuple[bool, Optional[str]]:
        """Check if login attempts are rate limited"""
        try:
            now = datetime.utcnow()
            
            # Get failed attempts for this username/IP in the last 24 hours
            failed_attempts = self.db.query(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.ip_address == ip_address,
                LoginAttempt.success == False,
                LoginAttempt.attempt_time > now - timedelta(hours=24)
            ).order_by(LoginAttempt.attempt_time.desc()).all()
            
            if not failed_attempts:
                return True, None
            
            failed_count = len(failed_attempts)
            last_attempt = failed_attempts[0].attempt_time
            
            # Progressive rate limiting
            if failed_count >= 12:
                # 12+ attempts: 1 hour wait
                wait_until = last_attempt + timedelta(hours=1)
                if now < wait_until:
                    remaining = int((wait_until - now).total_seconds())
                    return False, f"Too many failed attempts. Try again in {remaining // 60} minutes."
                    
            elif failed_count >= 6:
                # 6+ attempts: 30 minutes wait
                wait_until = last_attempt + timedelta(minutes=30)
                if now < wait_until:
                    remaining = int((wait_until - now).total_seconds())
                    return False, f"Too many failed attempts. Try again in {remaining // 60} minutes."
                    
            elif failed_count >= 3:
                # 3+ attempts: 30 seconds wait
                wait_until = last_attempt + timedelta(seconds=30)
                if now < wait_until:
                    remaining = int((wait_until - now).total_seconds())
                    return False, f"Too many failed attempts. Try again in {remaining} seconds."
            
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return True, None  # Allow login on error to avoid lockout
    
    def record_login_attempt(self, username: str, ip_address: str, success: bool, user_agent: str = None):
        """Record a login attempt"""
        try:
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                success=success,
                user_agent=user_agent,
                attempt_time=datetime.utcnow()
            )
            self.db.add(attempt)
            self.db.commit()
            
            # Clean up old attempts (older than 7 days)
            cutoff = datetime.utcnow() - timedelta(days=7)
            self.db.query(LoginAttempt).filter(
                LoginAttempt.attempt_time < cutoff
            ).delete()
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to record login attempt: {str(e)}")
    
    def authenticate_user(self, username: str, password: str, ip_address: str = "unknown", user_agent: str = None) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user with username and password"""
        try:
            # Check rate limiting first
            allowed, rate_limit_msg = self.check_login_rate_limit(username, ip_address)
            if not allowed:
                return None, rate_limit_msg
            
            user = self.db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if user and self.verify_password(password, user.password_hash):
                # Successful login
                self.record_login_attempt(username, ip_address, True, user_agent)
                logger.info(f"User authenticated: {username}")
                return user, None
            else:
                # Failed login
                self.record_login_attempt(username, ip_address, False, user_agent)
                logger.warning(f"Authentication failed for user: {username}")
                return None, "Invalid username or password"
                
        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            return None, "Authentication error occurred"
    
    def create_jwt_token(self, user: User) -> str:
        """Create JWT token for user"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_jwt_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if user_id:
                user = self.db.query(User).filter(
                    User.id == user_id,
                    User.is_active == True
                ).first()
                return user
            
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            logger.error(f"Error verifying JWT token: {e}")
            return None
    
    def create_api_key(self, name: str, user_id: int) -> Tuple[bool, str, str]:
        """Create a new API key"""
        try:
            # Generate API key
            api_key = f"gs_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Create API key record
            api_key_record = ApiKey(
                name=name,
                key_hash=key_hash,
                user_id=user_id,
                is_active=True
            )
            
            self.db.add(api_key_record)
            self.db.commit()
            
            logger.info(f"Created API key: {name} for user ID: {user_id}")
            return True, "API key created successfully", api_key
            
        except Exception as e:
            logger.error(f"Error creating API key {name}: {e}")
            return False, f"Error creating API key: {str(e)}", ""
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key and return associated user"""
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            api_key_record = self.db.query(ApiKey).filter(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True
            ).first()
            
            if api_key_record:
                # Update last used timestamp
                api_key_record.last_used = datetime.utcnow()
                self.db.commit()
                
                return api_key_record.user
            
            return None
            
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None
    
    def revoke_api_key(self, api_key_id: int) -> Tuple[bool, str]:
        """Revoke an API key"""
        try:
            api_key = self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
            if not api_key:
                return False, "API key not found"
            
            api_key.is_active = False
            self.db.commit()
            
            logger.info(f"Revoked API key: {api_key.name}")
            return True, "API key revoked successfully"
            
        except Exception as e:
            logger.error(f"Error revoking API key {api_key_id}: {e}")
            return False, f"Error revoking API key: {str(e)}"
    
    def is_setup_complete(self) -> bool:
        """Check if initial setup is complete"""
        try:
            setting = self.db.query(Setting).filter(Setting.key == "setup_complete").first()
            return setting and setting.value.lower() == "true"
        except Exception:
            return False
    
    def complete_setup(self) -> None:
        """Mark setup as complete"""
        try:
            setting = self.db.query(Setting).filter(Setting.key == "setup_complete").first()
            if setting:
                setting.value = "true"
            else:
                setting = Setting(
                    key="setup_complete",
                    value="true",
                    description="Whether initial setup is complete"
                )
                self.db.add(setting)
            
            self.db.commit()
            logger.info("Setup marked as complete")
            
        except Exception as e:
            logger.error(f"Error completing setup: {e}")
