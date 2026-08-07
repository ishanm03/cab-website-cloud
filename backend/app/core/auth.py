# backend/app/core/auth.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

# Standard Bearer scheme helper
security_scheme = HTTPBearer(auto_error=False)

class AuthenticatedUser(BaseModel):
    uid: str
    email: Optional[str] = None
    admin: bool = False

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> AuthenticatedUser:
    """
    FastAPI dependency to extract and verify the Firebase JWT token from the Authorization header.
    Returns AuthenticatedUser context or raises HTTP 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    try:
        # Decodes and verifies token via Firebase Admin SDK
        # This checks token signature, expiration, and audience parameters
        decoded_claims = firebase_auth.verify_id_token(token)
        
        return AuthenticatedUser(
            uid=decoded_claims.get("uid"),
            email=decoded_claims.get("email"),
            admin=decoded_claims.get("admin") is True
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

from app.core.config import settings

async def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    RBAC dependency ensuring the authenticated user has the 'admin' custom claim set to True.
    """
    if not current_user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin permissions are required to perform this action."
        )
    return current_user

async def require_super_admin(
    current_user: AuthenticatedUser = Depends(require_admin)
) -> AuthenticatedUser:
    """
    RBAC dependency ensuring the user email matches the SUPER_ADMIN_EMAILS configuration list.
    """
    super_admin_list = [e.strip().lower() for e in settings.SUPER_ADMIN_EMAILS]
    user_email = (current_user.email or "").strip().lower()
    
    if not user_email or user_email not in super_admin_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Super Admin permissions required to manage user roles."
        )
    return current_user
