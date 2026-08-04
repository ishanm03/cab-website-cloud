# backend/scripts/test_phase5.py
import sys
import os
from unittest.mock import patch, MagicMock

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=== Running Phase 5 Booking Feeds & List Integration Tests ===")

    # 1. Rider auth credentials
    rider_payload = {
        "uid": "test_rider_p5",
        "email": "rider@p5.com",
        "admin": False
    }
    rider_headers = {"Authorization": "Bearer mock_rider_token_p5"}

    # 2. Admin auth credentials
    admin_payload = {
        "uid": "test_admin_p5",
        "email": "admin@p5.com",
        "admin": True
    }
    admin_headers = {"Authorization": "Bearer mock_admin_token_p5"}

    # Mock some booking records in the DB
    mock_b1 = MagicMock()
    mock_b1.to_dict.return_value = {
        "booking_id": "BK-0001",
        "customer_id": "test_rider_p5",
        "trip_details": { "pickup_location": "A", "drop_location": "B" },
        "creation_ts": "2026-08-04T12:00:00"
    }

    mock_b2 = MagicMock()
    mock_b2.to_dict.return_value = {
        "booking_id": "BK-0002",
        "customer_id": "other_rider_p5",
        "trip_details": { "pickup_location": "C", "drop_location": "D" },
        "creation_ts": "2026-08-04T12:30:00"
    }

    # Test Case 1: GET /bookings as Rider (should filter only their own bookings)
    print("Test 1: GET /api/v1/bookings (Rider accessing own feed)...")
    with patch("firebase_admin.auth.verify_id_token", return_value=rider_payload):
        with patch("app.routers.bookings.db") as mock_db:
            # Query matching user's customer_id should return b1 only
            mock_db.collection.return_value.where.return_value.stream.return_value = [mock_b1]
            
            response = client.get("/api/v1/bookings", headers=rider_headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert len(data) == 1
            assert data[0]["booking_id"] == "BK-0001"
            assert data[0]["customer_id"] == "test_rider_p5"
            print("✓ Rider personal booking history list fetched successfully!")

    # Test Case 2: GET /admin/bookings as regular Rider (should be blocked)
    print("Test 2: GET /api/v1/admin/bookings (Rider attempting admin access)...")
    with patch("firebase_admin.auth.verify_id_token", return_value=rider_payload):
        response = client.get("/api/v1/admin/bookings", headers=rider_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Regular riders blocked from accessing the admin booking feed!")

    # Test Case 3: GET /admin/bookings as Admin (should return all bookings)
    print("Test 3: GET /api/v1/admin/bookings (Admin accessing global feed)...")
    with patch("firebase_admin.auth.verify_id_token", return_value=admin_payload):
        with patch("app.routers.bookings.db") as mock_db:
            # Global stream should return both b1 and b2
            mock_db.collection.return_value.stream.return_value = [mock_b1, mock_b2]
            
            response = client.get("/api/v1/admin/bookings", headers=admin_headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert len(data) == 2
            # Check descending sort based on creation_ts (BK-0002 was at 12:30, BK-0001 at 12:00)
            assert data[0]["booking_id"] == "BK-0002"
            assert data[1]["booking_id"] == "BK-0001"
            print("✓ Admin global booking feed successfully fetched with correct descending sort!")

    print("\n✓✓✓ All Phase 5 Booking Feeds & List Integration Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
