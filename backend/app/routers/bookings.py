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
from app.core.auth import get_current_user, require_admin, AuthenticatedUser
from app.schemas.pydantic_models import (
    AvailabilityResponse,
    QuoteEstimateRequest,
    QuoteEstimateResponse,
    BookingCreateRequest,
    FeedbackSubmitRequest
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

# Fallback rate parameters matching docs/fare_logic_design.md
FALLBACK_RATES = {
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
}

def is_night_time(time_str: str, start_str: str = "23:59", end_str: str = "06:00") -> bool:
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        
        if start > end:  # Over midnight (e.g. 23:59 to 06:00)
            return t >= start or t <= end
        else:
            return start <= t <= end
    except Exception:
        return False

def calculate_fare(
    ride_type: str, 
    distance: float, 
    days: Optional[int], 
    tier: str, 
    hours: Optional[int], 
    time_string: str,
    active_rates: Optional[dict], 
    flat_metrics: Optional[dict] = None
) -> float:
    actual_days = max(1, days or 1)
    actual_distance = float(distance or 0.0)
    actual_hours = max(1, hours or 1)
    
    # Resolve rate database configs
    rates_db = active_rates.get("rates", active_rates) if active_rates else FALLBACK_RATES
    global_cfg = rates_db.get("global", FALLBACK_RATES["global"])
    night_start = global_cfg.get("night_charge_start", "23:59")
    night_end = global_cfg.get("night_charge_end", "06:00")
    
    night_applies = is_night_time(time_string, night_start, night_end)

    # 1. Hourly Rental Packages
    if ride_type == "rental":
        category_rates = rates_db.get("rental", FALLBACK_RATES["rental"])
        config = category_rates.get(tier, FALLBACK_RATES["rental"][tier])
        
        base_fare = float(config.get("base_fare", 2300.0))
        incl_km = float(config.get("included_km", 60.0))
        incl_hours = float(config.get("included_hours", 6.0))
        
        extra_km_charge = max(0.0, actual_distance - incl_km) * float(config.get("extra_km_rate", 12.0))
        extra_hour_charge = max(0.0, float(actual_hours) - incl_hours) * float(config.get("extra_hour_rate", 180.0))
        night_charge = float(config.get("night_charge", 200.0)) if night_applies else 0.0
        discount = float(config.get("default_discount", 500.0))
        
        subtotal = base_fare + extra_km_charge + extra_hour_charge + night_charge - discount
        return float(max(0.0, round(subtotal)))

    # 2. Flat routes matrix override (Local or Intercity)
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

    # 3. Intercity Outstation (Round-Trip pricing)
    if ride_type == "outstation":
        category_rates = rates_db.get("intercity", FALLBACK_RATES["intercity"])
        config = category_rates.get(tier, FALLBACK_RATES["intercity"][tier])
        
        round_trip_dist = actual_distance * 2.0
        min_billed_km = float(config.get("min_km_per_day", 250.0)) * actual_days
        billable_km = max(round_trip_dist, min_billed_km)
        
        base_fare = billable_km * float(config.get("rate_per_km", 12.0))
        driver_allowance = float(config.get("driver_allowance", 600.0)) * actual_days
        night_halt = float(config.get("night_halt", 500.0)) * max(0, actual_days - 1)
        
        total = base_fare + driver_allowance + night_halt
        return float(round(total))
        
    # 4. Fallback Local Ride pricing
    else:
        category_rates = rates_db.get("local", FALLBACK_RATES["local"])
        config = category_rates.get(tier, FALLBACK_RATES["local"][tier])
        
        base_fare = float(config.get("base_fare", 550.0))
        extra_km_charge = max(0.0, actual_distance - 10.0) * float(config.get("extra_km_rate", 12.0))
        night_charge = float(config.get("night_charge", 200.0)) if night_applies else 0.0
        
        total = base_fare + extra_km_charge + night_charge
        return float(round(total))

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
            time_string=request.time_string,
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

@router.get("/bookings")
async def list_rider_bookings(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Fetch all bookings owned by the authenticated rider, sorted by creation timestamp descending.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    try:
        docs = db.collection("bookings").where("customer_id", "==", current_user.uid).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            # Convert datetime timestamps
            for ts_field in ["creation_ts", "updated_ts"]:
                if ts_field in data and not isinstance(data[ts_field], (str, type(None))):
                    try:
                        data[ts_field] = data[ts_field].isoformat()
                    except Exception:
                        data[ts_field] = str(data[ts_field])
            results.append(data)
            
        # In-memory sorting (fallback in case composite indexes are not built yet in firestore)
        results.sort(key=lambda x: x.get("creation_ts") or "", reverse=True)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bookings: {str(e)}"
        )

@router.get("/admin/bookings")
async def list_all_bookings(current_user: AuthenticatedUser = Depends(require_admin)):
    """
    Fetch all booking records globally, sorted by creation timestamp descending.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    try:
        docs = db.collection("bookings").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            for ts_field in ["creation_ts", "updated_ts"]:
                if ts_field in data and not isinstance(data[ts_field], (str, type(None))):
                    try:
                        data[ts_field] = data[ts_field].isoformat()
                    except Exception:
                        data[ts_field] = str(data[ts_field])
            results.append(data)
            
        results.sort(key=lambda x: x.get("creation_ts") or "", reverse=True)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch admin bookings list: {str(e)}"
        )

@router.post("/bookings/{booking_id}/feedback")
async def submit_booking_feedback(
    booking_id: str,
    request: FeedbackSubmitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Rider reviews a completed booking and submits star rating & comments.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database offline."
        )
    try:
        doc_ref = db.collection("bookings").document(booking_id)
        doc_snap = doc_ref.get()
        if not doc_snap.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found."
            )
        booking = doc_snap.to_dict()
        
        # Verify ownership
        if booking.get("customer_id") != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You can only review your own rides."
            )
        
        # Verify status is completed
        if booking.get("status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed rides can be reviewed."
            )
            
        # Prevent duplicates
        if booking.get("feedback") is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feedback has already been submitted for this ride."
            )
            
        feedback_payload = {
            "feedback": {
                "rating": request.rating,
                "comments": request.comments,
                "submitted_ts": SERVER_TIMESTAMP
            },
            "updated_ts": SERVER_TIMESTAMP
        }
        doc_ref.update(feedback_payload)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )

