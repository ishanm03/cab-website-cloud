# backend/app/schemas/pydantic_models.py
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator

# ==========================================
# 1. Profile Schemas
# ==========================================

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    city: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    auth_provider: Optional[str] = Field(default=None)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        clean_phone = "".join(filter(str.isdigit, v))
        if len(clean_phone) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return clean_phone

class UserProfileResponse(BaseModel):
    uid: str
    name: str
    city: str
    phone: str
    email: Optional[str] = None
    auth_provider: str
    status: str
    creation_ts: Union[datetime, str, None] = None
    updated_ts: Union[datetime, str, None] = None

# ==========================================
# 2. Offer Validation Schemas
# ==========================================

class OfferValidationRequest(BaseModel):
    code: str
    base_fare: float

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        return v.strip().upper()

class OfferValidationResponse(BaseModel):
    valid: bool
    discount: float
    code: Optional[str] = None
    message: str

# ==========================================
# 3. Catalog Schemas
# ==========================================

class LocationResponse(BaseModel):
    id: str
    name: str
    type: str
    lat: float
    lng: float

class FlatFareResponse(BaseModel):
    id: str
    pickup_name: str
    drop_name: str
    fares: Dict[str, float]

# ==========================================
# 4. Settings Rates Schemas
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
    night_charge_start: str
    night_charge_end: str
    gst_percentage: float = 5.0

class SettingsRatesResponse(BaseModel):
    local: Dict[str, LocalRates]
    rental: Dict[str, RentalRates]
    intercity: Dict[str, IntercityRates]
    global_settings: GlobalRates = Field(..., alias="global")

    class Config:
        populate_by_name = True

# ==========================================
# 5. Availability & Booking Schemas
# ==========================================

class AvailabilityResponse(BaseModel):
    availability: Dict[str, bool]

class QuoteEstimateRequest(BaseModel):
    category: str
    pickup: str
    drop: str
    date_string: str
    time_string: str
    days: Optional[int] = None
    hours: Optional[int] = None
    km: float
    vehicle_tier: str
    promo_code: Optional[str] = None

class QuoteEstimateResponse(BaseModel):
    quote_id: str
    base_fare: float
    discount_amount: float
    estimated_fare: float
    promo_code: Optional[str] = None
    signature: str
    expires_at: str

class BookingCreateRequest(BaseModel):
    trip_details: Dict[str, Any]
    fare_details: Dict[str, Any]
    quote_signature: str
    quote_id: str
    expires_at: str

class FeedbackSubmitRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comments: str = Field(..., min_length=1)


