# backend/app/routers/profiles.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import SERVER_TIMESTAMP
from app.core.firebase import db
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.pydantic_models import UserProfileUpdate, UserProfileResponse

router = APIRouter(
    prefix="/me/profile",
    tags=["profile"]
)

@router.get("", response_model=UserProfileResponse)
async def get_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Fetch the logged-in user's Firestore profile record.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is offline."
        )
        
    try:
        user_doc_ref = db.collection("users").document(current_user.uid)
        doc_snap = user_doc_ref.get()
        
        if not doc_snap.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found in database."
            )
            
        data = doc_snap.to_dict()
        
        # Serialize datetime timestamps if they are raw Firestore timestamp objects
        for field in ["creation_ts", "updated_ts"]:
            if field in data and not isinstance(data[field], (str, type(None))):
                try:
                    data[field] = data[field].isoformat()
                except Exception:
                    data[field] = str(data[field])
                    
        return UserProfileResponse(
            uid=current_user.uid,
            name=data.get("name", ""),
            city=data.get("city", "Kolkata"),
            phone=data.get("phone", ""),
            email=data.get("email") or current_user.email,
            auth_provider=data.get("auth_provider", "password"),
            status=data.get("status", "active"),
            creation_ts=data.get("creation_ts"),
            updated_ts=data.get("updated_ts")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}"
        )

@router.put("", response_model=UserProfileResponse)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Create or merge updates into the logged-in user's Firestore profile record.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is offline."
        )
        
    try:
        user_doc_ref = db.collection("users").document(current_user.uid)
        doc_snap = user_doc_ref.get()
        
        update_data = {k: v for k, v in profile_update.model_dump().items() if v is not None}
        
        if not doc_snap.exists:
            # Create complete new profile structure
            new_profile = {
                "uid": current_user.uid,
                "name": update_data.get("name", ""),
                "city": update_data.get("city", "Kolkata"),
                "phone": update_data.get("phone", ""),
                "email": update_data.get("email") or current_user.email,
                "auth_provider": update_data.get("auth_provider", "password"),
                "status": "active",
                "creation_ts": SERVER_TIMESTAMP,
                "updated_ts": SERVER_TIMESTAMP
            }
            user_doc_ref.set(new_profile)
            
            # Fetch back to resolve timestamps
            final_doc = user_doc_ref.get().to_dict()
        else:
            # Update existing profile
            update_data["updated_ts"] = SERVER_TIMESTAMP
            user_doc_ref.update(update_data)
            
            # Merge client-side for immediate response data
            final_doc = doc_snap.to_dict().copy()
            final_doc.update(update_data)
            
        # Serialize datetime fields
        for field in ["creation_ts", "updated_ts"]:
            if field in final_doc and not isinstance(final_doc[field], (str, type(None))):
                try:
                    final_doc[field] = final_doc[field].isoformat()
                except Exception:
                    final_doc[field] = str(final_doc[field])

        return UserProfileResponse(
            uid=current_user.uid,
            name=final_doc.get("name", ""),
            city=final_doc.get("city", "Kolkata"),
            phone=final_doc.get("phone", ""),
            email=final_doc.get("email") or current_user.email,
            auth_provider=final_doc.get("auth_provider", "password"),
            status=final_doc.get("status", "active"),
            creation_ts=final_doc.get("creation_ts"),
            updated_ts=final_doc.get("updated_ts")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
