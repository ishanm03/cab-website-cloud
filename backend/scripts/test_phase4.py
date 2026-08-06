# backend/scripts/test_phase4.py
import sys
import os
from unittest.mock import patch, MagicMock

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_RATES = {
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
    }
}

def run_tests():
    print("=== Running Phase 4 Rental & Outstation Fare Calculation Tests ===")

    # Mock user auth context
    mock_user_payload = {
        "uid": "test_rider_p4",
        "email": "rider@p4.com",
        "admin": False
    }
    headers = {"Authorization": "Bearer mock_jwt_token_p4"}

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_user_payload):
        with patch("app.routers.bookings.db") as mock_db:
            # Configure db mock to return exists=True and mock rates
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = MOCK_RATES
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []

            # Test 1: Local Premium Ride (Day Time, No Extra KM)
            # Expected: Base premium rate = 650.0
            print("Test 1: Local premium day-time quote...")
            req_local_day = {
                "category": "local",
                "pickup": "Howrah Station",
                "drop": "Sealdah Station",
                "date_string": "2026-08-04",
                "time_string": "14:00",
                "km": 5.0,
                "vehicle_tier": "premium"
            }
            
            response = client.post("/api/v1/quotes/estimate", json=req_local_day, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["base_fare"] == 650.0
            assert data["estimated_fare"] == 650.0
            print("✓ Local premium day-time quote calculated successfully!")

            # Test 2: Local Compact Ride (Night Time, 2 AM, No Extra KM)
            # Expected: Base compact rate (550.0) + Night charge (200.0) = 750.0
            print("Test 2: Local compact night-time quote...")
            req_local_night = {
                "category": "local",
                "pickup": "Howrah Station",
                "drop": "Sealdah Station",
                "date_string": "2026-08-04",
                "time_string": "02:00",
                "km": 5.0,
                "vehicle_tier": "compact"
            }
            
            response = client.post("/api/v1/quotes/estimate", json=req_local_night, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert data["base_fare"] == 750.0
            assert data["estimated_fare"] == 750.0
            print("✓ Local compact night-time quote (+200 night charge) calculated successfully!")

            # Test 3: Rental Package (Compact, 70 KM actual distance, 6 Hours duration, Day Time)
            # Expected: 
            # Base package = 2300.0 (includes 60 KM)
            # Extra distance = 10 KM * 12.0 = 120.0
            # Default package discount = -500.0
            # Total = 2300.0 + 120.0 - 500.0 = 1920.0
            print("Test 3: Rental compact package quote...")
            req_rental = {
                "category": "rental",
                "pickup": "Custom Location",
                "drop": "Custom Location",
                "date_string": "2026-08-04",
                "time_string": "12:00",
                "hours": 6,
                "km": 70.0,
                "vehicle_tier": "compact"
            }
            
            response = client.post("/api/v1/quotes/estimate", json=req_rental, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert data["base_fare"] == 1920.0
            print("✓ Rental compact package (70 KM) quote calculated successfully!")

            # Test 4: Outstation Ride (Compact, One-way 150 KM, 2 Days duration)
            # Expected:
            # Round trip distance = 150 * 2 = 300 KM
            # Minimum daily distance limit = 250 KM/day * 2 days = 500 KM
            # Billable KM = max(300, 500) = 500 KM
            # Base KM fare = 500 * 12.0 (compact rate/km) = 6000.0
            # Driver daily allowance = 2 * 600.0 (compact allowance/day) = 1200.0
            # Night halts = 1 night * 500.0 (compact night halt/night) = 500.0
            # Total = 6000.0 + 1200.0 + 500.0 = 7700.0
            print("Test 4: Outstation compact round-trip quote...")
            req_outstation = {
                "category": "outstation",
                "pickup": "Kolkata",
                "drop": "Digha",
                "date_string": "2026-08-04",
                "time_string": "06:30",
                "days": 2,
                "km": 150.0,
                "vehicle_tier": "compact"
            }
            
            response = client.post("/api/v1/quotes/estimate", json=req_outstation, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert data["base_fare"] == 7700.0
            assert data["estimated_fare"] == 7700.0
            print("✓ Outstation compact multi-day quote calculated successfully!")

    print("\n✓✓✓ All Phase 4 Rental & Outstation Fare Calculation Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
