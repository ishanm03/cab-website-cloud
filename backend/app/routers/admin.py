# backend/app/routers/admin.py
import uuid
import json
import os
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import SERVER_TIMESTAMP

from app.core.firebase import db
from app.core.auth import require_admin, AuthenticatedUser
from app.schemas.pydantic_models import DbCleanupRequest

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

@router.post("/sync-schemas")
async def sync_schemas(current_user: AuthenticatedUser = Depends(require_admin)):
    """
    Run retrospective schema upgrades, database checks, and seed initial catalogs if empty.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database offline.")
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        seed_path = os.path.join(current_dir, "..", "resources", "initial_seed_rates.json")
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_data = json.load(f)

        # 1. Check vehicles for address
        vehicles_ref = db.collection("vehicles")
        for doc_snap in vehicles_ref.stream():
            data = doc_snap.to_dict()
            if "address" not in data:
                doc_snap.reference.update({"address": "Main Garage, Kolkata"})
                
        # 2. Check drivers for address
        drivers_ref = db.collection("drivers")
        for doc_snap in drivers_ref.stream():
            data = doc_snap.to_dict()
            if "address" not in data:
                doc_snap.reference.update({"address": "Kolkata City Depot"})
                
        # 3. Check settings/rates and migrate legacy 'sedan' key to 'premium', or seed if missing
        rates_ref = db.collection("settings").document("rates")
        rates_snap = rates_ref.get()
        if rates_snap.exists:
            rates_data = rates_snap.to_dict()
            rates = rates_data.get("rates", {})
            rates_need_update = False
            
            if "sedan" in rates and "premium" not in rates:
                rates["premium"] = rates["sedan"]
                del rates["sedan"]
                rates_need_update = True
                
            if "compact" not in rates:
                rates["compact"] = {
                    "base_cost": 250.0,
                    "rate_per_km": 10.00,
                    "rate_per_hour": 120.00,
                    "driver_allowance_per_day": 300.00
                }
                rates_need_update = True
                
            if rates_need_update:
                rates_ref.update({"rates": rates})
        else:
            # Seed default rates and fleet sizes from JSON
            rates_ref.set({
                "rates": seed_data["rates"],
                "default_fleet_sizes": seed_data["default_fleet_sizes"],
                "active_version_id": "seed-v1",
                "updated_ts": SERVER_TIMESTAMP
            })
            db.collection("rates_history").document("seed-v1").set({
                "rates": seed_data["rates"],
                "creation_ts": SERVER_TIMESTAMP
            })
                
        # 4. Seed Predefined Locations if empty
        locations_ref = db.collection("locations")
        if len(list(locations_ref.limit(1).stream())) == 0:
            for item in seed_data.get("locations", []):
                name = item["name"]
                coords = item["coords"]
                loc_id = name.lower().replace(" ", "_").strip()
                loc_id = "".join(c for c in loc_id if c.isalnum() or c == "_")
                locations_ref.document(loc_id).set({
                    "id": loc_id,
                    "name": name,
                    "lat": coords[0],
                    "lng": coords[1],
                    "type": "both",
                    "creation_ts": SERVER_TIMESTAMP
                })
                
        # 5. Seed Predefined Flat Fares if empty
        flat_fares_ref = db.collection("flat_fares")
        if len(list(flat_fares_ref.limit(1).stream())) == 0:
            for item in seed_data.get("flat_fares", []):
                pickup_name = item["pickup_name"]
                drop_name = item["drop_name"]
                km = item["km"]
                base_sedan = item["base_fare_sedan"]
                base_suv = item["base_fare_suv"]
                
                pickup_id = pickup_name.lower().replace(" ", "_").strip()
                pickup_id = "".join(c for c in pickup_id if c.isalnum() or c == "_")
                drop_id = drop_name.lower().replace(" ", "_").strip()
                drop_id = "".join(c for c in drop_id if c.isalnum() or c == "_")
                combined_id = f"{pickup_id}_{drop_id}"
                
                flat_fares_ref.document(combined_id).set({
                    "id": combined_id,
                    "pickup_name": pickup_name,
                    "drop_name": drop_name,
                    "fares": {
                        "compact": round(base_sedan * 0.85),
                        "premium": base_sedan,
                        "suv": base_suv,
                        "muv": round(base_suv * 1.25)
                    },
                    "creation_ts": SERVER_TIMESTAMP
                })
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/db/cleanup")
async def db_cleanup(
    request: DbCleanupRequest,
    current_user: AuthenticatedUser = Depends(require_admin)
):
    """
    Delete either all documents in a collection or selected documents by ID.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
        
    collection_name = request.collection_name.strip()
    if not collection_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection name cannot be empty."
        )

    try:
        deleted_count = 0
        batch = db.batch()
        
        # Scenario A: Delete selected document IDs
        if request.document_ids is not None and len(request.document_ids) > 0:
            for doc_id in request.document_ids:
                doc_ref = db.collection(collection_name).document(doc_id)
                batch.delete(doc_ref)
                deleted_count += 1
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = db.batch()
            if deleted_count % 500 != 0:
                batch.commit()
                
        # Scenario B: Delete ALL documents in collection
        else:
            if not request.confirm_delete_all:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Confirm delete all flag must be set to true to clear the entire collection."
                )
            
            # Retrieve all documents in collection
            docs = db.collection(collection_name).stream()
            for doc_snap in docs:
                batch.delete(doc_snap.reference)
                deleted_count += 1
                if deleted_count % 500 == 0:
                    batch.commit()
                    batch = db.batch()
            if deleted_count % 500 != 0:
                batch.commit()
                
        return {
            "status": "success",
            "collection_name": collection_name,
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database cleanup failed: {str(e)}"
        )

