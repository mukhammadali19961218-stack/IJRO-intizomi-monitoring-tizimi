import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .database import get_db
from .models import Admin

SECRET_KEY = os.getenv("SECRET_KEY", "ijro-dashboard-super-secure-production-jwt-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def seed_default_users(db: Session):
    """
    Ensures default admin and viewer exist with secure password hashing.
    Passwords can be overridden via environment variables.
    """
    admin_user = db.query(Admin).filter(Admin.username == "admin").first()
    admin_pw = os.getenv("ADMIN_PASSWORD", "admin123")
    if not admin_user:
        admin_user = Admin(
            username="admin",
            hashed_password=get_password_hash(admin_pw),
            role="admin",
            created_at=datetime.utcnow()
        )
        db.add(admin_user)
        db.commit()
    else:
        if not admin_user.role:
            admin_user.role = "admin"
            db.commit()

    viewer_user = db.query(Admin).filter(Admin.username == "viewer").first()
    viewer_pw = os.getenv("VIEWER_PASSWORD", "viewer123")
    if not viewer_user:
        viewer_user = Admin(
            username="viewer",
            hashed_password=get_password_hash(viewer_pw),
            role="viewer",
            created_at=datetime.utcnow()
        )
        db.add(viewer_user)
        db.commit()
    else:
        if not viewer_user.role:
            viewer_user.role = "viewer"
            db.commit()

def get_current_user(
    request: Request,
    token_header: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db)
) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentifikatsiyadan o'tilmagan yoki sessiya muddati tugagan",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = token_header or token_query or request.cookies.get("access_token")
    if not token:
        # Fallback to authorization header if Bearer prefix present
        auth_hdr = request.headers.get("Authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ")[1]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(Admin).filter(Admin.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def require_admin(user: Admin = Depends(get_current_user)) -> Admin:
    """Requirement 14: Mandate ADMIN role on sensitive operations."""
    if (user.role or "admin").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat administrator amalga oshirishi mumkin. Kuzatuvchi (viewer) ushbu amalni bajara olmaydi."
        )
    return user

def require_auth(user: Admin = Depends(get_current_user)) -> Admin:
    """Accepts any valid authenticated user (admin or viewer) for read-only endpoints."""
    return user

# Alias for backward compatibility
get_current_admin = get_current_user
seed_default_admin = seed_default_users
