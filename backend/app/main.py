# backend/app/main.py
from datetime import datetime
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Initialize Firebase SDK globally
import app.core.firebase

from app.core.config import settings
from app.core.auth import get_current_user, require_admin, AuthenticatedUser
from app.routers import profiles, catalogs

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(profiles.router, prefix=settings.API_V1_STR)
app.include_router(catalogs.router, prefix=settings.API_V1_STR)

# ==========================================
# Exception Handlers
# ==========================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format request validation errors into standard API error envelopes.
    """
    details = []
    for err in exc.errors():
        details.append({
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", "")
        })
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request body or parameters failed validation rules.",
                "details": details
            }
        }
    )

# ==========================================
# Routes & Endpoints
# ==========================================

@app.get(f"{settings.API_V1_STR}/health", tags=["system"])
async def health_check():
    """
    Standard health check endpoint returning HTTP 200.
    """
    return {
        "data": {
            "status": "healthy",
            "service": settings.PROJECT_NAME
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    }

@app.get(f"{settings.API_V1_STR}/me/test-auth", tags=["auth"])
async def test_auth(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Protected route to test valid authentication tokens.
    """
    return {
        "data": {
            "uid": current_user.uid,
            "email": current_user.email,
            "admin": current_user.admin
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    }

@app.get(f"{settings.API_V1_STR}/admin/test-rbac", tags=["auth"])
async def test_rbac(admin_user: AuthenticatedUser = Depends(require_admin)):
    """
    Admin-only route to test RBAC verification claims.
    """
    return {
        "data": {
            "uid": admin_user.uid,
            "email": admin_user.email,
            "admin": admin_user.admin,
            "message": "Welcome, Admin! RBAC verified successfully."
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0"
        }
    }

# Entrypoint for quick testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

