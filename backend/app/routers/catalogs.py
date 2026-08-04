# backend/app/routers/catalogs.py
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.core.firebase import db
from app.schemas.pydantic_models import (
    OfferValidationRequest,
    OfferValidationResponse,
    LocationResponse,
    FlatFareResponse
)

router = APIRouter(
    tags=["catalogs"]
)

@router.get("/settings/rates")
async def get_rates():
    """
    Fetch the dynamic rates configuration for all vehicle tiers.
    """
    if db is None:
        # Fallback rates in case DB is offline or during testing
        return {
            "rates": {
                "compact": { "rate_per_km": 10.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 120.0, "base_cost": 250.0 },
                "premium": { "rate_per_km": 12.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 150.0, "base_cost": 300.0 },
                "suv": { "rate_per_km": 15.0, "driver_allowance_per_day": 400.0, "rate_per_hour": 200.0, "base_cost": 500.0 },
                "muv": { "rate_per_km": 18.0, "driver_allowance_per_day": 500.0, "rate_per_hour": 250.0, "base_cost": 700.0 }
            },
            "active_version_id": "legacy-static-v1"
        }
        
    try:
        rates_doc = db.collection("settings").document("rates").get()
        if not rates_doc.exists:
            # Seed default if document is missing
            default_rates = {
                "rates": {
                    "compact": { "rate_per_km": 10.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 120.0, "base_cost": 250.0 },
                    "premium": { "rate_per_km": 12.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 150.0, "base_cost": 300.0 },
                    "suv": { "rate_per_km": 15.0, "driver_allowance_per_day": 400.0, "rate_per_hour": 200.0, "base_cost": 500.0 },
                    "muv": { "rate_per_km": 18.0, "driver_allowance_per_day": 500.0, "rate_per_hour": 250.0, "base_cost": 700.0 }
                },
                "active_version_id": "legacy-static-v1"
            }
            db.collection("settings").document("rates").set(default_rates)
            return default_rates
            
        return rates_doc.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rates: {str(e)}"
        )

@router.get("/locations", response_model=List[LocationResponse])
async def get_locations():
    """
    Fetch all geocoded landmark pin locations.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
        
    try:
        docs = db.collection("locations").order_by("name").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append(LocationResponse(
                id=doc.id,
                name=data.get("name", ""),
                type=data.get("type", "both"),
                lat=float(data.get("lat", 0.0)),
                lng=float(data.get("lng", 0.0))
            ))
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch locations: {str(e)}"
        )

@router.get("/flat-fares", response_model=List[FlatFareResponse])
async def get_flat_fares():
    """
    Fetch all flat route matrix fare overrides.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
        
    try:
        docs = db.collection("flat_fares").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            fares_data = {k: float(v) for k, v in data.get("fares", {}).items()}
            results.append(FlatFareResponse(
                id=doc.id,
                pickup_name=data.get("pickup_name", ""),
                drop_name=data.get("drop_name", ""),
                fares=fares_data
            ))
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch flat fares: {str(e)}"
        )

@router.post("/offers/validate", response_model=OfferValidationResponse)
async def validate_offer(request: OfferValidationRequest):
    """
    Validate a promo code coupon against trip subtotal.
    """
    if db is None:
        return OfferValidationResponse(
            valid=False,
            discount=0.0,
            message="Database is offline. Promo codes cannot be validated."
        )
        
    try:
        offer_doc_ref = db.collection("offers").document(request.code)
        doc_snap = offer_doc_ref.get()
        
        if not doc_snap.exists:
            return OfferValidationResponse(
                valid=False,
                discount=0.0,
                message="Invalid promo code."
            )
            
        offer = doc_snap.to_dict()
        if offer.get("status") != "active":
            return OfferValidationResponse(
                valid=False,
                discount=0.0,
                message="This promo code is no longer active."
            )
            
        min_threshold = float(offer.get("min_fare_threshold", 0.0))
        if request.base_fare < min_threshold:
            return OfferValidationResponse(
                valid=False,
                discount=0.0,
                message=f"Minimum fare of ₹{int(min_threshold)} required to use this promo."
            )
            
        discount = 0.0
        val = float(offer.get("discount_value", 0.0))
        disc_type = offer.get("discount_type", "flat").lower()
        
        if disc_type == "flat":
            discount = val
        elif disc_type == "percentage":
            discount = round((request.base_fare * val) / 100.0)
            
        # Cap the discount at the base fare
        discount = min(discount, request.base_fare)
        
        return OfferValidationResponse(
            valid=True,
            discount=discount,
            code=request.code,
            message=f"Promo code {request.code} applied successfully!"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating promo code: {str(e)}"
        )

@router.get("/offers/visible")
async def get_visible_offers():
    """
    Fetch all active coupons that are visible to customers.
    """
    if db is None:
        return []
    try:
        docs = db.collection("offers").where("status", "==", "active").where("visible_to_customer", "==", True).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "code": doc.id,
                "discount_type": data.get("discount_type", "flat"),
                "discount_value": float(data.get("discount_value", 0.0)),
                "min_fare_threshold": float(data.get("min_fare_threshold", 0.0)),
                "status": data.get("status", "active"),
                "visible_to_customer": data.get("visible_to_customer", True)
            })
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active offers: {str(e)}"
        )

