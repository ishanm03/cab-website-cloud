# backend/app/routers/admin.py
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import SERVER_TIMESTAMP

from app.core.firebase import db
from app.core.auth import require_admin, AuthenticatedUser

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.patch("/bookings/{booking_id}")
async def update_booking(
    booking_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Update booking details, status, or driver assignment.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    try:
        doc_ref = db.collection("bookings").document(booking_id)
        if not doc_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking {booking_id} not found."
            )
        payload["updated_ts"] = SERVER_TIMESTAMP
        doc_ref.update(payload)
        return {"status": "success", "booking_id": booking_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update booking: {str(e)}"
        )

@router.post("/bookings/manual")
async def create_manual_booking(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Manually register a ride booking from the admin dashboard context.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    booking_id = payload.get("booking_id")
    if not booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing booking_id parameter."
        )
    try:
        payload["creation_ts"] = SERVER_TIMESTAMP
        payload["updated_ts"] = SERVER_TIMESTAMP
        db.collection("bookings").document(booking_id).set(payload)
        return {"status": "success", "booking_id": booking_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create manual booking: {str(e)}"
        )

@router.put("/settings/rates")
async def update_rates(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Update dynamic pricing rates in settings/rates and append to rates_history.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    try:
        import time
        version_id = f"R-{int(time.time() * 1000)}"
        rates = payload.get("rates", payload) # Support either wrapped in {"rates": ...} or raw
        
        # Write to rates_history version doc
        db.collection("rates_history").document(version_id).set({
            "rates": rates,
            "creation_ts": SERVER_TIMESTAMP
        })
        
        # Write to settings/rates active version doc
        db.collection("settings").document("rates").set({
            "rates": rates,
            "active_version_id": version_id,
            "updated_ts": SERVER_TIMESTAMP
        })
        return {"status": "success", "active_version_id": version_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save rates: {str(e)}"
        )

# ==========================================
# Fleet CRUD
# ==========================================

@router.post("/vehicles")
async def create_vehicle(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        vehicle_id = payload.get("id") or str(uuid.uuid4().hex[:8])
        db.collection("vehicles").document(vehicle_id).set(payload)
        return {"status": "success", "id": vehicle_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/vehicles/{vehicle_id}")
async def update_vehicle(
    vehicle_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("vehicles").document(vehicle_id).set(payload, merge=True)
        return {"status": "success", "id": vehicle_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str, 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("vehicles").document(vehicle_id).delete()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Drivers CRUD
# ==========================================

@router.post("/drivers")
async def create_driver(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        driver_id = payload.get("id") or str(uuid.uuid4().hex[:8])
        db.collection("drivers").document(driver_id).set(payload)
        return {"status": "success", "id": driver_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/drivers/{driver_id}")
async def update_driver(
    driver_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("drivers").document(driver_id).set(payload, merge=True)
        return {"status": "success", "id": driver_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/drivers/{driver_id}")
async def delete_driver(
    driver_id: str, 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("drivers").document(driver_id).delete()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Locations CRUD
# ==========================================

@router.post("/locations")
async def create_location(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        loc_id = payload.get("id") or str(uuid.uuid4().hex[:8])
        db.collection("locations").document(loc_id).set(payload)
        return {"status": "success", "id": loc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/locations/{location_id}")
async def update_location(
    location_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("locations").document(location_id).set(payload, merge=True)
        return {"status": "success", "id": location_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/locations/{location_id}")
async def delete_location(
    location_id: str, 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("locations").document(location_id).delete()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Flat Fares CRUD
# ==========================================

@router.post("/flat-fares")
async def create_flat_fare(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        fare_id = payload.get("id") or f"{payload['pickup_name'].lower().replace(' ', '_')}_{payload['drop_name'].lower().replace(' ', '_')}"
        db.collection("flat_fares").document(fare_id).set(payload)
        return {"status": "success", "id": fare_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/flat-fares/{fare_id}")
async def update_flat_fare(
    fare_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("flat_fares").document(fare_id).set(payload, merge=True)
        return {"status": "success", "id": fare_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/flat-fares/{fare_id}")
async def delete_flat_fare(
    fare_id: str, 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("flat_fares").document(fare_id).delete()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Offers/Promos CRUD
# ==========================================

@router.post("/offers")
async def create_offer(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing promo code.")
    try:
        db.collection("offers").document(code.upper()).set(payload)
        return {"status": "success", "code": code.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/offers/{offer_id}")
async def update_offer(
    offer_id: str, 
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("offers").document(offer_id.upper()).set(payload, merge=True)
        return {"status": "success", "code": offer_id.upper()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/offers/{offer_id}")
async def delete_offer(
    offer_id: str, 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        db.collection("offers").document(offer_id.upper()).delete()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed-fleet")
async def seed_fleet(
    payload: Dict[str, Any], 
    current_user: AuthenticatedUser = Depends(require_admin)
):
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        import random
        model_mapping = {
            "compact": "Maruti Alto K10",
            "premium": "Maruti Swift Dzire",
            "suv": "Hyundai Creta",
            "muv": "Toyota Innova"
        }
        
        count = 0
        for tier, drivers_list in payload.items():
            for item in drivers_list:
                vehicle_plate_clean = item["vehicle_number"].upper().strip()
                vehicle_id = "".join(c for c in vehicle_plate_clean if c.isalnum())
                
                driver_phone_clean = item["driver_phone"].strip()
                driver_id = "".join(c for c in driver_phone_clean if c.isdigit())
                
                random_license = f"DL-{random.randint(1000000000, 9999999999)}"
                
                db.collection("vehicles").document(vehicle_id).set({
                    "model": model_mapping.get(tier, "Fleet Car"),
                    "plate_number": vehicle_plate_clean,
                    "tier": tier,
                    "status": "active",
                    "assigned_driver_id": driver_id,
                    "passengers": 4 if tier == "compact" else (4 if tier == "premium" else (6 if tier == "suv" else 12)),
                    "address": "Main Garage, Kolkata",
                    "creation_ts": SERVER_TIMESTAMP
                })
                
                db.collection("drivers").document(driver_id).set({
                    "name": item["driver_name"],
                    "phone": driver_phone_clean,
                    "license_number": random_license,
                    "status": "active",
                    "assigned_vehicle_id": vehicle_id,
                    "address": "Kolkata City Depot",
                    "creation_ts": SERVER_TIMESTAMP
                })
                count += 1
                
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
