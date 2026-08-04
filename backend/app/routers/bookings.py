# backend/app/routers/bookings.py
import hmac
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud.firestore import SERVER_TIMESTAMP

from app.core.firebase import db
from app.core.config import settings
from app.core.auth import get_current_user, AuthenticatedUser
from app.schemas.pydantic_models import (
    AvailabilityResponse,
    QuoteEstimateRequest,
    QuoteEstimateResponse,
    BookingCreateRequest
)

router = APIRouter(
    prefix="",
    tags=["bookings"]
)

# Static configurations
DEFAULT_FLEET_SIZES = {
    "compact": 5,
    "premium": 5,
    "suv": 3,
    "muv": 2
}

RATE_CONFIG = {
    "compact": { "rate_per_km": 10.00, "driver_allowance_per_day": 300.00, "rate_per_hour": 120.00, "base_cost": 250.00 },
    "premium": { "rate_per_km": 12.00, "driver_allowance_per_day": 300.00, "rate_per_hour": 150.00, "base_cost": 300.00 },
    "suv":     { "rate_per_km": 15.00, "driver_allowance_per_day": 400.00, "rate_per_hour": 200.00, "base_cost": 500.00 },
    "muv":     { "rate_per_km": 18.00, "driver_allowance_per_day": 500.00, "rate_per_hour": 250.00, "base_cost": 700.00 }
}

def calculate_fare(
    ride_type: str, 
    distance: float, 
    days: Optional[int], 
    tier: str, 
    hours: Optional[int], 
    active_rates: Optional[dict], 
    flat_metrics: Optional[dict] = None
) -> float:
    actual_days = max(1, days or 1)
    actual_distance = float(distance or 0.0)
    actual_hours = max(1, hours or 1)
    
    rates = active_rates.get("rates", RATE_CONFIG) if active_rates else RATE_CONFIG
    config = rates.get(tier, RATE_CONFIG.get(tier, RATE_CONFIG["premium"]))
    
    if ride_type == "rental":
        hourly_rate = float(config.get("rate_per_hour", 120.0 if tier == "compact" else (150.0 if tier == "premium" else (200.0 if tier == "suv" else 250.0))))
        return float(round(hourly_rate * actual_hours))
        
    if (ride_type == "local" or ride_type == "intercity") and flat_metrics:
        if tier == "compact":
            val = flat_metrics.get("base_fare_compact") or round((flat_metrics.get("base_fare_premium") or flat_metrics.get("base_fare_sedan") or 999) * 0.85)
            return float(val)
        if tier == "premium":
            val = flat_metrics.get("base_fare_premium") or flat_metrics.get("base_fare_sedan") or 999
            return float(val)
        if tier == "suv":
            val = flat_metrics.get("base_fare_suv") or 1000
            return float(val)
        if tier == "muv":
            val = flat_metrics.get("base_fare_muv") or round((flat_metrics.get("base_fare_suv") or 1000) * 1.25)
            return float(val)
            
    if ride_type == "outstation":
        round_trip = actual_distance * 2
        min_billed = actual_days * 250
        final_billed = max(round_trip, min_billed)
        distance_cost = final_billed * float(config.get("rate_per_km", 12.0))
        allowance_cost = actual_days * float(config.get("driver_allowance_per_day", 300.0))
        return float(round(distance_cost + allowance_cost))
    else:
        distance_cost = actual_distance * float(config.get("rate_per_km", 12.0))
        base_cost = float(config.get("base_cost", 250.0 if tier == "compact" else (300.0 if tier == "premium" else (500.0 if tier == "suv" else 700.0))))
        return float(round(base_cost + distance_cost))

def compute_hmac_signature(
    quote_id: str, 
    customer_id: str, 
    vehicle_tier: str, 
    base_fare: float, 
    estimated_fare: float, 
    expires_at: str, 
    secret: str
) -> str:
    message = f"{quote_id}|{customer_id}|{vehicle_tier}|{int(base_fare)}|{int(estimated_fare)}|{expires_at}"
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

@router.get("/bookings/availability", response_model=AvailabilityResponse)
async def get_availability(date: str):
    """
    Overbooking inventory check: returns availability status for each vehicle class.
    """
    if db is None:
        # DB offline fallback
        return AvailabilityResponse(availability={k: True for k in DEFAULT_FLEET_SIZES.keys()})
        
    try:
        # 1. Fetch fleet configurations
        fleet_sizes = DEFAULT_FLEET_SIZES.copy()
        vehicles = db.collection("vehicles").where("status", "==", "active").stream()
        vehicle_list = [v.to_dict() for v in vehicles]
        if vehicle_list:
            # Recompute size from DB
            counts = {}
            for v in vehicle_list:
                tier = v.get("tier", "premium")
                counts[tier] = counts.get(tier, 0) + 1
            for k in fleet_sizes.keys():
                if k in counts:
                    fleet_sizes[k] = counts[k]

        # 2. Fetch active conflicting bookings for the date
        active_bookings = db.collection("bookings") \
            .where("trip_details.pickup_date", "==", date) \
            .where("status", "in", ["pending_approval", "confirmed", "active"]) \
            .stream()
            
        booking_counts = {}
        for b in active_bookings:
            data = b.to_dict()
            tier = data.get("fare_details", {}).get("vehicle_tier")
            if tier:
                booking_counts[tier] = booking_counts.get(tier, 0) + 1
                
        # 3. Compile availability map
        avail = {}
        for tier in DEFAULT_FLEET_SIZES.keys():
            avail[tier] = booking_counts.get(tier, 0) < fleet_sizes.get(tier, DEFAULT_FLEET_SIZES[tier])
            
        return AvailabilityResponse(availability=avail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check availability: {str(e)}"
        )

@router.post("/quotes/estimate", response_model=QuoteEstimateResponse)
async def estimate_quote(
    request: QuoteEstimateRequest, 
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Calculate and cryptographically sign a ride quote package.
    """
    try:
        # Load active rates configuration from DB
        active_rates = None
        if db is not None:
            doc = db.collection("settings").document("rates").get()
            if doc.exists:
                active_rates = doc.to_dict()
                
        # Query flat fare overrides
        flat_metrics = None
        if db is not None:
            flat_fares = db.collection("flat_fares") \
                .where("pickup_name", "==", request.pickup) \
                .where("drop_name", "==", request.drop) \
                .stream()
            flat_fare_list = list(flat_fares)
            if flat_fare_list:
                flat_data = flat_fare_list[0].to_dict()
                flat_metrics = {
                    "km": flat_data.get("km"),
                    "base_fare_compact": flat_data.get("fares", {}).get("compact"),
                    "base_fare_premium": flat_data.get("fares", {}).get("premium"),
                    "base_fare_suv": flat_data.get("fares", {}).get("suv"),
                    "base_fare_muv": flat_data.get("fares", {}).get("muv")
                }

        # Calculate base fare
        base_fare = calculate_fare(
            ride_type=request.category,
            distance=request.km,
            days=request.days,
            tier=request.vehicle_tier,
            hours=request.hours,
            active_rates=active_rates,
            flat_metrics=flat_metrics
        )

        # Validate and apply promo code
        discount = 0.0
        if request.promo_code and db is not None:
            offer_doc = db.collection("offers").document(request.promo_code).get()
            if offer_doc.exists:
                offer = offer_doc.to_dict()
                if offer.get("status") == "active" and base_fare >= float(offer.get("min_fare_threshold", 0.0)):
                    val = float(offer.get("discount_value", 0.0))
                    disc_type = offer.get("discount_type", "flat").lower()
                    if disc_type == "flat":
                        discount = val
                    elif disc_type == "percentage":
                        discount = round((base_fare * val) / 100.0)
                    discount = min(discount, base_fare)

        estimated_fare = base_fare - discount
        quote_id = f"QT-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:4].upper()}"
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()

        # Compute tamper-proof signature
        sig = compute_hmac_signature(
            quote_id=quote_id,
            customer_id=current_user.uid,
            vehicle_tier=request.vehicle_tier,
            base_fare=base_fare,
            estimated_fare=estimated_fare,
            expires_at=expires_at,
            secret=settings.HMAC_QUOTE_SECRET
        )

        return QuoteEstimateResponse(
            quote_id=quote_id,
            base_fare=base_fare,
            discount_amount=discount,
            estimated_fare=estimated_fare,
            promo_code=request.promo_code or None,
            signature=sig,
            expires_at=expires_at
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quote calculation error: {str(e)}"
        )

@router.post("/bookings")
async def create_booking(
    request: BookingCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Verify quote signature integrity and write a secure booking request to Firestore.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline. Booking cannot be committed."
        )

    try:
        # Check if the quote has expired
        exp_time = datetime.fromisoformat(request.expires_at)
        if datetime.now(timezone.utc) > exp_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking transaction failed: The quote has expired. Please re-estimate."
            )

        # Validate signature
        recomputed_sig = compute_hmac_signature(
            quote_id=request.quote_id,
            customer_id=current_user.uid,
            vehicle_tier=request.fare_details.get("vehicle_tier", ""),
            base_fare=float(request.fare_details.get("base_fare", 0.0)),
            estimated_fare=float(request.fare_details.get("estimated_fare", 0.0)),
            expires_at=request.expires_at,
            secret=settings.HMAC_QUOTE_SECRET
        )

        if not hmac.compare_digest(recomputed_sig, request.quote_signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking transaction failed: Quote signature is invalid or has been modified."
            )

        # Generate unique Booking ID (BK-YYYYMMDD-XXXX)
        date_stamp = datetime.now().strftime("%Y%m%d")
        random_hex = str(uuid.uuid4().int)[:4]
        booking_id = f"BK-{date_stamp}-{random_hex}"

        # Build final secure database payload
        booking_payload = {
            "booking_id": booking_id,
            "customer_id": current_user.uid,
            "booking_channel": "website",
            "status": "pending_approval",
            "payment_status": "pending",
            "driver_assignment": None,
            "trip_details": request.trip_details,
            "fare_details": {
                "vehicle_tier": request.fare_details.get("vehicle_tier"),
                "estimated_km": request.fare_details.get("estimated_km"),
                "base_fare": request.fare_details.get("base_fare"),
                "discount_amount": request.fare_details.get("discount_amount"),
                "promo_code": request.fare_details.get("promo_code"),
                "estimated_fare": request.fare_details.get("estimated_fare"),
                "rates_version_id": request.fare_details.get("rates_version_id"),
                "quote_id": request.quote_id
            },
            "creation_ts": SERVER_TIMESTAMP,
            "updated_ts": SERVER_TIMESTAMP
        }

        # Save to database
        db.collection("bookings").document(booking_id).set(booking_payload)
        return {
            "status": "success",
            "booking_id": booking_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log booking: {str(e)}"
        )
