# backend/scripts/test_phase2.py
import sys
import os
from unittest.mock import patch, MagicMock

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=== Running Phase 2 Profiles & Catalogs Integration Tests ===")

    # Mock payload for authenticated user
    mock_user_payload = {
        "uid": "test_user_p2",
        "email": "p2@example.com",
        "admin": False
    }

    # Helper headers
    headers = {"Authorization": "Bearer mock_jwt_token_p2"}

    # Patch Auth globally for these tests
    with patch("firebase_admin.auth.verify_id_token", return_value=mock_user_payload):
        
        # Test 1: GET /settings/rates
        print("Test 1: GET /api/v1/settings/rates...")
        # Patch Firestore doc check
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "rates": {
                "compact": { "rate_per_km": 10.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 120.0, "base_cost": 250.0 },
                "premium": { "rate_per_km": 12.0, "driver_allowance_per_day": 300.0, "rate_per_hour": 150.0, "base_cost": 300.0 }
            },
            "active_version_id": "p2-test-v1"
        }
        
        with patch("app.routers.catalogs.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            
            response = client.get("/api/v1/settings/rates")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "rates" in data
            assert data["rates"]["compact"]["rate_per_km"] == 10.0
            print("✓ Settings rates endpoint validated!")

        # Test 2: GET /locations
        print("Test 2: GET /api/v1/locations...")
        mock_loc_docs = []
        for name, idx in [("Howrah Station", "howrah"), ("Airport", "airport")]:
            mock_doc = MagicMock()
            mock_doc.id = idx
            mock_doc.to_dict.return_value = {
                "name": name,
                "type": "both",
                "lat": 22.5,
                "lng": 88.4
            }
            mock_loc_docs.append(mock_doc)

        with patch("app.routers.catalogs.db") as mock_db:
            mock_db.collection.return_value.order_by.return_value.stream.return_value = mock_loc_docs
            
            response = client.get("/api/v1/locations")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Howrah Station"
            print("✓ Locations catalog endpoint validated!")

        # Test 3: POST /offers/validate
        print("Test 3: POST /api/v1/offers/validate...")
        # Mock offer coupon doc
        mock_offer = MagicMock()
        mock_offer.exists = True
        mock_offer.to_dict.return_value = {
            "code": "PROMO20",
            "discount_type": "percentage",
            "discount_value": 20.0,
            "min_fare_threshold": 500.0,
            "status": "active",
            "visible_to_customer": True
        }
        
        with patch("app.routers.catalogs.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = mock_offer
            
            # Case A: Below threshold (base fare = 400, threshold = 500)
            req_below = {"code": "PROMO20", "base_fare": 400.0}
            response = client.post("/api/v1/offers/validate", json=req_below)
            assert response.status_code == 200
            res_below = response.json()
            assert res_below["valid"] is False
            assert "Minimum fare" in res_below["message"]

            # Case B: Valid (base fare = 1000, 20% discount = 200)
            req_valid = {"code": "PROMO20", "base_fare": 1000.0}
            response = client.post("/api/v1/offers/validate", json=req_valid)
            assert response.status_code == 200
            res_valid = response.json()
            assert res_valid["valid"] is True
            assert res_valid["discount"] == 200.0
            print("✓ Offers validation calculations validated!")

        # Test 4: Profile Management (GET & PUT)
        print("Test 4: GET /api/v1/me/profile (Not Found Case)...")
        with patch("app.routers.profiles.db") as mock_db:
            # Case A: Document doesn't exist
            mock_profile_doc = MagicMock()
            mock_profile_doc.exists = False
            mock_db.collection.return_value.document.return_value.get.return_value = mock_profile_doc
            
            response = client.get("/api/v1/me/profile", headers=headers)
            assert response.status_code == 404, f"Expected 404, got {response.status_code}"
            print("✓ GET profile not found handled successfully!")

            # Case B: Update/Save Profile (PUT)
            print("Test 4: PUT /api/v1/me/profile (Save Profile)...")
            mock_profile_doc.exists = True
            mock_profile_doc.to_dict.return_value = {
                "name": "Seth User",
                "city": "Kolkata",
                "phone": "919876543210",
                "email": "p2@example.com",
                "auth_provider": "google",
                "status": "active",
                "creation_ts": "2026-08-04T12:00:00",
                "updated_ts": "2026-08-04T12:00:00"
            }
            # PUT request body
            payload = {
                "name": "Seth User Updated",
                "phone": "+91 (987) 654-3210" # Cleans to 919876543210
            }
            response = client.put("/api/v1/me/profile", json=payload, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            res_put = response.json()
            assert res_put["name"] == "Seth User Updated"
            assert res_put["phone"] == "919876543210"
            print("✓ PUT profile modification and validation successfully validated!")

            # Case C: Fetch Profile (GET)
            print("Test 4: GET /api/v1/me/profile (Found Case)...")
            response = client.get("/api/v1/me/profile", headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            res_get = response.json()
            assert res_get["uid"] == "test_user_p2"
            assert res_get["name"] == "Seth User"
            print("✓ GET profile fetch verified successfully!")

    print("\n✓✓✓ All Phase 2 Profiles & Catalogs Integration Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
