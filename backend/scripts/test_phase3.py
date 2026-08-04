# backend/scripts/test_phase3.py
import sys
import os
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def run_tests():
    print("=== Running Phase 3 Secure Booking & Quotes Integration Tests ===")

    # Mock user authorization
    mock_user_payload = {
        "uid": "test_rider_p3",
        "email": "rider@p3.com",
        "admin": False
    }
    headers = {"Authorization": "Bearer mock_jwt_token_p3"}

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_user_payload):
        
        # Test 1: GET /bookings/availability
        print("Test 1: GET /api/v1/bookings/availability...")
        # Mock vehicles list and conflicting bookings list
        mock_vehicle_stream = []
        # Total active fleet: 1 compact, 1 premium
        for tier in ["compact", "premium"]:
            mock_v = MagicMock()
            mock_v.to_dict.return_value = {"tier": tier, "status": "active"}
            mock_vehicle_stream.append(mock_v)
            
        mock_booking_stream = []
        # Conflicting booking: 1 compact booked
        mock_b = MagicMock()
        mock_b.to_dict.return_value = {
            "fare_details": {"vehicle_tier": "compact"},
            "trip_details": {"pickup_date": "2026-08-04"}
        }
        mock_booking_stream.append(mock_b)

        with patch("app.routers.bookings.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = mock_vehicle_stream
            mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = mock_booking_stream
            
            response = client.get("/api/v1/bookings/availability?date=2026-08-04")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            # Compact should be sold out (1 booked of 1 active), premium available (0 booked of 1 active)
            assert data["availability"]["compact"] is False
            assert data["availability"]["premium"] is True
            print("✓ Overbooking availability logic validated!")

        # Test 2: POST /quotes/estimate
        print("Test 2: POST /api/v1/quotes/estimate...")
        # Test local ride estimate
        req_payload = {
            "category": "local",
            "pickup": "Howrah Station",
            "drop": "Airport",
            "date_string": "2026-08-04",
            "time_string": "14:00",
            "km": 20.0,
            "vehicle_tier": "premium"
        }
        
        # Mock rates settings document
        mock_rates_doc = MagicMock()
        mock_rates_doc.exists = True
        mock_rates_doc.to_dict.return_value = {
            "rates": {
                "premium": { "rate_per_km": 12.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 150.0, "base_cost": 300.0 }
            }
        }
        
        with patch("app.routers.bookings.db") as mock_db:
            # document("rates").get()
            mock_db.collection.return_value.document.return_value.get.return_value = mock_rates_doc
            # where("pickup_name").where("drop_name").stream() -> empty (no flat fare)
            mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
            
            response = client.post("/api/v1/quotes/estimate", json=req_payload, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            quote_data = response.json()
            assert quote_data["base_fare"] == 540.0  # (20 * 12) + 300 base cost
            assert quote_data["estimated_fare"] == 540.0
            assert "signature" in quote_data
            print("✓ Secure quotes fare math and HMAC signature generation validated!")

        # Test 3: POST /bookings (Valid Commit)
        print("Test 3: POST /api/v1/bookings (Valid)...")
        # Build mock booking registration body using the signed quote details
        booking_payload = {
            "trip_details": {
                "ride_type": "local",
                "pickup_location": "Howrah Station",
                "drop_location": "Airport",
                "pickup_date": "2026-08-04",
                "pickup_time": "14:00"
            },
            "fare_details": {
                "vehicle_tier": "premium",
                "estimated_km": 20.0,
                "base_fare": quote_data["base_fare"],
                "discount_amount": quote_data["discount_amount"],
                "estimated_fare": quote_data["estimated_fare"]
            },
            "quote_signature": quote_data["signature"],
            "quote_id": quote_data["quote_id"],
            "expires_at": quote_data["expires_at"]
        }
        
        with patch("app.routers.bookings.db") as mock_db:
            response = client.post("/api/v1/bookings", json=booking_payload, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            res_book = response.json()
            assert res_book["status"] == "success"
            assert res_book["booking_id"].startswith("BK-")
            print("✓ Secure booking creation validated!")

        # Test 4: POST /bookings (Tampered Pricing Check)
        print("Test 4: POST /api/v1/bookings (Tampered Fare)...")
        # Tamper with the estimated fare to try to pay less!
        booking_payload_tampered = booking_payload.copy()
        booking_payload_tampered["fare_details"] = booking_payload["fare_details"].copy()
        booking_payload_tampered["fare_details"]["estimated_fare"] = 1.0  # Reduced fare!
        
        with patch("app.routers.bookings.db") as mock_db:
            response = client.post("/api/v1/bookings", json=booking_payload_tampered, headers=headers)
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "signature is invalid" in response.json()["detail"]
            print("✓ Tampered fare price modifications successfully blocked!")

        # Test 5: POST /bookings (Expired Quote Check)
        print("Test 5: POST /api/v1/bookings (Expired Quote)...")
        # Build booking payload with an expired timestamp
        expired_time = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        
        # Compute signature with the expired time to bypass sig validation first
        expired_message = f"{quote_data['quote_id']}|test_rider_p3|premium|{int(quote_data['base_fare'])}|{int(quote_data['estimated_fare'])}|{expired_time}"
        expired_sig = hmac.new(
            settings.HMAC_QUOTE_SECRET.encode("utf-8"),
            expired_message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        booking_payload_expired = booking_payload.copy()
        booking_payload_expired["expires_at"] = expired_time
        booking_payload_expired["quote_signature"] = expired_sig

        with patch("app.routers.bookings.db") as mock_db:
            response = client.post("/api/v1/bookings", json=booking_payload_expired, headers=headers)
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "quote has expired" in response.json()["detail"]
            print("✓ Expired quotes successfully blocked!")

    print("\n✓✓✓ All Phase 3 Secure Booking & Quotes Integration Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
