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
    default_nested_rates = {
        "rates": {
            "local": {
                "compact": { "base_fare": 550.0, "extra_km_rate": 12.0, "waiting_rate": 3.0, "night_charge": 200.0 },
                "premium": { "base_fare": 650.0, "extra_km_rate": 13.0, "waiting_rate": 4.0, "night_charge": 300.0 },
                "suv":     { "base_fare": 750.0, "extra_km_rate": 14.0, "waiting_rate": 5.0, "night_charge": 400.0 },
                "muv":     { "base_fare": 850.0, "extra_km_rate": 15.0, "waiting_rate": 5.0, "night_charge": 500.0 }
            },
            "rental": {
                "compact": { "base_fare": 2300.0, "included_hours": 6, "included_km": 60, "extra_km_rate": 12.0, "extra_hour_rate": 180.0, "night_charge": 200.0, "default_discount": 500.0 },
                "premium": { "base_fare": 2500.0, "included_hours": 6, "included_km": 60, "extra_km_rate": 13.0, "extra_hour_rate": 240.0, "night_charge": 300.0, "default_discount": 500.0 },
                "suv":     { "base_fare": 2800.0, "included_hours": 6, "included_km": 60, "extra_km_rate": 14.0, "extra_hour_rate": 300.0, "night_charge": 400.0, "default_discount": 500.0 },
                "muv":     { "base_fare": 3300.0, "included_hours": 6, "included_km": 60, "extra_km_rate": 16.0, "extra_hour_rate": 360.0, "night_charge": 500.0, "default_discount": 500.0 }
            },
            "intercity": {
                "compact": { "rate_per_km": 12.0, "driver_allowance": 600.0, "min_km_per_day": 250.0, "night_halt": 500.0 },
                "premium": { "rate_per_km": 14.0, "driver_allowance": 600.0, "min_km_per_day": 250.0, "night_halt": 500.0 },
                "suv":     { "rate_per_km": 18.0, "driver_allowance": 800.0, "min_km_per_day": 250.0, "night_halt": 500.0 },
                "muv":     { "rate_per_km": 22.0, "driver_allowance": 800.0, "min_km_per_day": 250.0, "night_halt": 500.0 }
            },
            "global": {
                "night_charge_start": "23:59",
                "night_charge_end": "06:00"
            }
        },
        "default_fleet_sizes": {
            "compact": 5,
            "premium": 5,
            "suv": 3,
            "muv": 2
        },
        "active_version_id": "seed-v1"
    }

    if db is None:
        return default_nested_rates
        
    try:
        rates_doc = db.collection("settings").document("rates").get()
        if not rates_doc.exists:
            db.collection("settings").document("rates").set(default_nested_rates)
            return default_nested_rates
            
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

