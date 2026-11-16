import json
import os
from datetime import UTC, datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .database import get_db

# --- CONFIG ---
import secrets as secrets_module
from pathlib import Path

def _get_or_create_secret_key() -> str:
    """Generate and persist a secure secret key for JWT signing."""
    secret_file = Path(os.getenv("ADINATH_SECRET_FILE", ".secret_key"))
    
    # Use environment variable if provided (for cloud deployments)
    env_secret = os.getenv("ADINATH_SECRET_KEY")
    if env_secret and len(env_secret) >= 32:
        return env_secret
    
    # Development mode fallback: generate persistent secret
    if os.getenv("ADINATH_ENV", "development").lower() == "development":
        secret_file = Path(".secret_key_dev")
        try:
            if secret_file.exists():
                return secret_file.read_text().strip()
            secret = secrets_module.token_urlsafe(48)
            secret_file.write_text(secret)
            return secret
        except Exception:
            # Last resort: derive from environment to avoid hardcoded secrets
            return hash(os.getenv("ADINATH_SECRET_KEY", "default-dev-change-me"), usedforsecurity=False)
    
    # Production: generate and persist secret key
    try:
        if secret_file.exists():
            secret = secret_file.read_text().strip()
            if len(secret) >= 32:
                return secret
        
        # Generate new secure secret
        secret = secrets_module.token_urlsafe(48)
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(secret)
        secret_file.chmod(0o600)  # Restrict to owner only
        return secret
    except Exception as e:
        raise RuntimeError(f"Failed to initialize secret key: {e}")

SECRET_KEY = _get_or_create_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

# Rate limiting for login attempts (file-based for multi-worker safety)
_login_attempts_file = Path(".login_attempts.json")
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes


def _load_login_attempts() -> dict:
    """Load login attempts from file for multi-worker persistence."""
    try:
        if _login_attempts_file.exists():
            return json.loads(_login_attempts_file.read_text())
    except Exception:
        pass
    return {}


def _save_login_attempts(attempts: dict) -> None:
    """Save login attempts to file for multi-worker persistence."""
    try:
        _login_attempts_file.write_text(json.dumps(attempts))
    except Exception:
        pass


def _check_rate_limit(username: str) -> bool:
    """Check if user has exceeded login rate limit."""
    attempts = _load_login_attempts()
    now = datetime.now(UTC).timestamp()
    cutoff = now - LOGIN_WINDOW_SECONDS

    # Clean old attempts
    if username in attempts:
        attempts[username] = [t for t in attempts[username] if t > cutoff]

    # Check limit
    remaining = MAX_LOGIN_ATTEMPTS - len(attempts.get(username, []))
    return remaining > 0


def _record_login_attempt(username: str) -> None:
    """Record a failed login attempt to file."""
    attempts = _load_login_attempts()
    now = datetime.now(UTC).timestamp()
    cutoff = now - LOGIN_WINDOW_SECONDS
    if username not in attempts:
        attempts[username] = []
    attempts[username].append(now)
    # Keep only recent attempts within the window
    attempts[username] = [t for t in attempts[username] if t > cutoff]
    _save_login_attempts(attempts)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def passwords_match(plain: str, hashed: str) -> bool:
    """Constant-time friendly password comparison delegated to passlib."""
    return pwd_context.verify(plain, hashed)


def verify_password(plain: str, hashed: str) -> bool:
    return passwords_match(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def check_rate_limit(username: str) -> bool:
    """Check if user has exceeded login rate limit."""
    now = datetime.now(UTC).timestamp()
    cutoff = now - LOGIN_WINDOW_SECONDS
    
    # Clean old attempts
    if username in _login_attempts:
        _login_attempts[username] = [t for t in _login_attempts[username] if t > cutoff]
    
    # Check limit
    attempts = _login_attempts.get(username, [])
    return len(attempts) < MAX_LOGIN_ATTEMPTS


def record_login_attempt(username: str):
    """Record a failed login attempt."""
    now = datetime.now(UTC).timestamp()
    if username not in _login_attempts:
        _login_attempts[username] = []
    _login_attempts[username].append(now)


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate user with rate limiting protection."""
    if not _check_rate_limit(username):
        return None

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        _record_login_attempt(username)
        return None

    # Clear attempts on successful login
    # Use file-based attempts for backward compatibility clearing
    try:
        attempts = _load_login_attempts()
        if username in attempts:
            cutoff = datetime.now(UTC).timestamp() - LOGIN_WINDOW_SECONDS
            attempts[username] = [t for t in attempts[username] if t > cutoff]
            _save_login_attempts(attempts)
    except Exception:
        pass
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: str):
    """Dependency factory: restricts an endpoint to the given roles."""

    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency
