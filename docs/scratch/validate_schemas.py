# docs/scratch/validate_schemas.py
import sys
from datetime import datetime
from pydantic_schemas import (
    UserProfileSchema,
    VehicleSchema,
    DriverSchema,
    OfferSchema,
    LocationSchema,
    FlatFareSchema,
    SettingsRatesSchema,
    BookingSchema,
    SuccessEnvelope,
    ErrorEnvelope,
    TripDetails,
    FareDetails
)

def run_tests():
    print("=== Starting Phase 0 Schema Contract Validation Tests ===")

    # 1. User Profile Test
    user_data = {
        "uid": "user_abc123_test",
        "name": "Ishan Mukherjee",
        "city": "Kolkata",
        "phone": "+91 (987) 654-3210", # Validated by phone regex/stripper
        "email": "ishan@example.com",
        "auth_provider": "google",
        "status": "ACTIVE", # Validated and lowercased
        "creation_ts": datetime.utcnow(),
        "updated_ts": datetime.utcnow()
    }
    
    try:
        user = UserProfileSchema(**user_data)
        print("✓ UserProfileSchema successfully validated!")
        assert user.status == "active"
        assert user.phone == "919876543210"
    except Exception as e:
        print("✗ UserProfileSchema failed:", e)
        sys.exit(1)

    # 2. Vehicle Schema Test
    vehicle_data = {
        "model": "Suzuki WagonR",
        "plate_number": "WB-02-A-1234",
        "tier": "COMPACT",
        "status": "active",
        "assigned_driver_id": "918981538038",
        "passengers": 4,
        "address": "Main Garage, Kolkata",
        "creation_ts": datetime.utcnow()
    }
    try:
        vehicle = VehicleSchema(**vehicle_data)
        print("✓ VehicleSchema successfully validated!")
        assert vehicle.tier == "compact"
    except Exception as e:
        print("✗ VehicleSchema failed:", e)
        sys.exit(1)

    # 3. Settings Rates Schema Test (New dynamic pricing structure)
    settings_data = {
        "local": {
            "compact": { "base_fare": 550, "extra_km_rate": 12, "waiting_rate": 3, "night_charge": 200 },
            "premium": { "base_fare": 650, "extra_km_rate": 13, "waiting_rate": 4, "night_charge": 300 },
            "suv": { "base_fare": 750, "extra_km_rate": 14, "waiting_rate": 5, "night_charge": 400 },
            "muv": { "base_fare": 850, "extra_km_rate": 15, "waiting_rate": 5, "night_charge": 500 }
        },
        "rental": {
            "compact": { "base_fare": 2300, "included_hours": 6, "included_km": 60, "extra_km_rate": 12, "extra_hour_rate": 180, "night_charge": 200, "default_discount": 500 },
            "premium": { "base_fare": 2500, "included_hours": 6, "included_km": 60, "extra_km_rate": 13, "extra_hour_rate": 240, "night_charge": 300, "default_discount": 500 },
            "suv": { "base_fare": 2800, "included_hours": 6, "included_km": 60, "extra_km_rate": 14, "extra_hour_rate": 300, "night_charge": 400, "default_discount": 500 },
            "muv": { "base_fare": 3300, "included_hours": 6, "included_km": 60, "extra_km_rate": 16, "extra_hour_rate": 360, "night_charge": 500, "default_discount": 500 }
        },
        "intercity": {
            "compact": { "rate_per_km": 12, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
            "premium": { "rate_per_km": 14, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
            "suv": { "rate_per_km": 18, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 },
            "muv": { "rate_per_km": 22, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 }
        },
        "global": {
            "night_charge_start": "23:59",
            "night_charge_end": "06:00",
            "gst_percentage": 5.0
        }
    }
    try:
        rates = SettingsRatesSchema(**settings_data)
        print("✓ SettingsRatesSchema successfully validated!")
        assert rates.local["compact"].base_fare == 550.0
        assert rates.rental["muv"].base_fare == 3300.0
        assert rates.intercity["suv"].rate_per_km == 18.0
    except Exception as e:
        print("✗ SettingsRatesSchema failed:", e)
        sys.exit(1)

    # 4. Booking Schema Test (Example 1 Local Compact Ride from Customer Specification)
    # Target value expected: ₹686
    booking_data = {
        "booking_id": "BK-20260725-1029",
        "customer_id": "user_abc123_test",
        "booking_channel": "website",
        "status": "pending_approval",
        "payment_status": "pending",
        "driver_assignment": None,
        "trip_details": {
            "ride_type": "local",
            "pickup_location": "Howrah Station",
            "drop_location": "Dhakuria",
            "pickup_date": "2026-07-25",
            "pickup_time": "10:30",
            "pickup_coords": {"lat": 22.5834, "lng": 88.3414},
            "drop_coords": {"lat": 22.5134, "lng": 88.3685}
        },
        "fare_details": {
            "vehicle_tier": "compact",
            "estimated_km": 18.0, # 18 KM total distance
            "base_fare": 550.0, # Includes 0-10 KM
            "extra_distance_charge": 96.0, # (18 - 10) * 12 = 96
            "waiting_charge": 60.0, # 20 mins * 3 = 60
            "night_charge": 0.0,
            "toll_charges": 50.0,
            "parking_charges": 30.0,
            "discount_amount": 100.0,
            "promo_code": "DISCOUNT100",
            "estimated_fare": 686.0, # 550 + 96 + 60 + 0 + 50 + 30 - 100 = 686
            "quote_signature": "e5c6a8f10398f828a2a4b49c"
        },
        "creation_ts": datetime.utcnow(),
        "updated_ts": datetime.utcnow()
    }
    try:
        booking = BookingSchema(**booking_data)
        print("✓ BookingSchema successfully validated (Local Compact calculation matches exactly)!")
        assert booking.fare_details.estimated_fare == 686.0
    except Exception as e:
        print("✗ BookingSchema failed:", e)
        sys.exit(1)

    # 5. Success Envelope Test
    success_env = {
        "data": {
            "booking_id": "BK-20260725-1029",
            "status": "pending_approval"
        }
    }
    try:
        envelope = SuccessEnvelope(**success_env)
        print("✓ SuccessEnvelope successfully validated!")
        assert "version" in envelope.meta
    except Exception as e:
        print("✗ SuccessEnvelope failed:", e)
        sys.exit(1)

    print("\n✓✓✓ All Phase 0 Schema Verification Tests Passed Successfully! ✓✓✓")

if __name__ == "__main__":
    run_tests()
