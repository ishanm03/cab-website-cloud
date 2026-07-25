# docs/scratch/pydantic_schemas.py
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

# ==========================================
# 1. Base / Shared Submodels
# ==========================================

class Coordinates(BaseModel):
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")

# ==========================================
# 2. Collection Schemas
# ==========================================

class UserProfileSchema(BaseModel):
    uid: str = Field(..., description="Firebase Authentication UID")
    name: str = Field(..., min_length=1, description="Full name of user")
    city: str = Field(default="Kolkata", description="Registered city")
    phone: str = Field(..., description="10-digit phone number")
    email: Optional[str] = Field(default=None, description="Email address")
    auth_provider: str = Field(..., description="Authentication provider (e.g. password, google)")
    status: str = Field(default="active", description="Status of profile: active, suspended")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)
    updated_ts: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_phone = "".join(filter(str.isdigit, v))
        if len(clean_phone) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return clean_phone

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"active", "suspended"}
        if v.lower() not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v.lower()


class VehicleSchema(BaseModel):
    model: str = Field(..., description="Model string (e.g. Suzuki WagonR)")
    plate_number: str = Field(..., description="Unique license plate number")
    tier: str = Field(..., description="Vehicle class: compact, premium, suv, muv")
    status: str = Field(default="active", description="Status: active, inactive, maintenance")
    assigned_driver_id: Optional[str] = Field(default=None, description="Phone number or unique ID of the driver")
    passengers: int = Field(..., description="Passenger seat capacity")
    address: str = Field(default="Main Garage, Kolkata", description="Associated garage depot")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        allowed = {"compact", "premium", "suv", "muv"}
        if v.lower() not in allowed:
            raise ValueError(f"Tier must be one of {allowed}")
        return v.lower()


class DriverSchema(BaseModel):
    name: str = Field(..., description="Driver full name")
    phone: str = Field(..., description="Unique contact number")
    license_number: str = Field(..., description="Driving License number")
    status: str = Field(default="active", description="Working status: active, inactive, on_trip")
    assigned_vehicle_id: Optional[str] = Field(default=None, description="Plate number of assigned vehicle")
    address: str = Field(default="Kolkata City Depot", description="Local depot base")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)


class OfferSchema(BaseModel):
    code: str = Field(..., description="Uppercase promo coupon name")
    discount_type: str = Field(..., description="Discount style: flat, percentage")
    discount_value: float = Field(..., description="Value to subtract or discount percentage")
    min_fare_threshold: float = Field(default=0.0, description="Minimum base fare required")
    status: str = Field(default="active", description="Status: active, inactive")
    visible_to_customer: bool = Field(default=True, description="Should show in promotional lists")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, v: str) -> str:
        allowed = {"flat", "percentage"}
        if v.lower() not in allowed:
            raise ValueError(f"Discount type must be one of {allowed}")
        return v.lower()


class LocationSchema(BaseModel):
    id: str = Field(..., description="Snake-cased unique name identifier")
    name: str = Field(..., description="Human-readable name (e.g. Howrah Station)")
    type: str = Field(default="both", description="Pin type: pickup, drop, both")
    lat: float = Field(..., description="Latitude decimal")
    lng: float = Field(..., description="Longitude decimal")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"pickup", "drop", "both"}
        if v.lower() not in allowed:
            raise ValueError(f"Type must be one of {allowed}")
        return v.lower()


class FlatFareSchema(BaseModel):
    id: str = Field(..., description="Composite ID: pickupId_dropId")
    pickup_name: str = Field(..., description="Origin name")
    drop_name: str = Field(..., description="Destination name")
    fares: Dict[str, float] = Field(..., description="Fares mapped per category (compact, premium, suv, muv)")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("fares")
    @classmethod
    def validate_fares(cls, v: Dict[str, float]) -> Dict[str, float]:
        required_tiers = {"compact", "premium", "suv", "muv"}
        missing = required_tiers - set(v.keys())
        if missing:
            raise ValueError(f"Missing price keys in fares dictionary: {missing}")
        return v


# ==========================================
# 3. Dynamic settings/rates configuration
# ==========================================

class LocalRates(BaseModel):
    base_fare: float
    extra_km_rate: float
    waiting_rate: float
    night_charge: float

class RentalRates(BaseModel):
    base_fare: float
    included_hours: int
    included_km: int
    extra_km_rate: float
    extra_hour_rate: float
    night_charge: float
    default_discount: float

class IntercityRates(BaseModel):
    rate_per_km: float
    driver_allowance: float
    min_km_per_day: float
    night_halt: float

class GlobalRates(BaseModel):
    night_charge_start: str = Field(default="23:59")
    night_charge_end: str = Field(default="06:00")
    gst_percentage: float = Field(default=5.0)

class SettingsRatesSchema(BaseModel):
    local: Dict[str, LocalRates] = Field(..., description="Local ride rates mapped by tier")
    rental: Dict[str, RentalRates] = Field(..., description="Rental ride rates mapped by tier")
    intercity: Dict[str, IntercityRates] = Field(..., description="Intercity ride rates mapped by tier")
    global_settings: GlobalRates = Field(..., alias="global", description="Global timing and pricing options")

    class Config:
        populate_by_name = True


# ==========================================
# 4. Bookings Schema and Submodels
# ==========================================

class DriverAssignment(BaseModel):
    driver_id: str = Field(..., description="Driver identity key")
    driver_name: str = Field(..., description="Driver full name")
    vehicle_id: str = Field(..., description="Vehicle registration plate")
    vehicle_model: str = Field(..., description="Vehicle type details")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class TripDetails(BaseModel):
    ride_type: str = Field(..., description="Category: local, rental, outstation, intercity")
    pickup_location: str = Field(..., description="Pickup location string")
    drop_location: str = Field(..., description="Drop location string")
    pickup_date: str = Field(..., description="YYYY-MM-DD")
    pickup_time: str = Field(..., description="HH:MM")
    outstation_days: Optional[int] = Field(default=None, description="Outstation duration")
    rental_hours: Optional[int] = Field(default=None, description="Rental package duration")
    pickup_coords: Optional[Coordinates] = Field(default=None)
    drop_coords: Optional[Coordinates] = Field(default=None)
    route_polyline: Optional[str] = Field(default=None)

    @field_validator("ride_type")
    @classmethod
    def validate_ride_type(cls, v: str) -> str:
        allowed = {"local", "rental", "outstation", "intercity"}
        if v.lower() not in allowed:
            raise ValueError(f"Ride type must be one of {allowed}")
        return v.lower()

class FareDetails(BaseModel):
    vehicle_tier: str = Field(..., description="Vehicle tier: compact, premium, suv, muv")
    estimated_km: float = Field(..., description="Calculated trip distance")
    base_fare: float = Field(..., description="Tier base pricing")
    extra_distance_charge: float = Field(default=0.0)
    waiting_charge: float = Field(default=0.0)
    night_charge: float = Field(default=0.0)
    toll_charges: float = Field(default=0.0)
    parking_charges: float = Field(default=0.0)
    driver_allowance: float = Field(default=0.0)
    discount_amount: float = Field(default=0.0)
    promo_code: Optional[str] = Field(default=None)
    estimated_fare: float = Field(..., description="Final target fare client will pay")
    rates_version_id: Optional[str] = Field(default=None)
    quote_signature: Optional[str] = Field(default=None, description="HMAC-SHA256 signature generated by server")

class BookingSchema(BaseModel):
    booking_id: str = Field(..., description="Date-based alphanumeric booking ID")
    customer_id: str = Field(..., description="Auth user ID of customer")
    booking_channel: str = Field(default="website", description="Booking channel origin")
    status: str = Field(default="pending_approval", description="Status string")
    payment_status: str = Field(default="pending", description="Payment state")
    driver_assignment: Optional[DriverAssignment] = Field(default=None)
    trip_details: TripDetails = Field(..., description="Details of route and type")
    fare_details: FareDetails = Field(..., description="Financial calculation audit breakdown")
    creation_ts: datetime = Field(default_factory=datetime.utcnow)
    updated_ts: datetime = Field(default_factory=datetime.utcnow)


# ==========================================
# 5. Standard API HTTP Envelope Models
# ==========================================

class SuccessEnvelope(BaseModel):
    data: Any
    meta: Dict[str, Any] = Field(default_factory=lambda: {"version": "1.0", "timestamp": datetime.utcnow().isoformat()})

class ErrorDetail(BaseModel):
    loc: List[Union[str, int]]
    msg: str
    type: str

class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None

class ErrorEnvelope(BaseModel):
    error: ErrorBody
