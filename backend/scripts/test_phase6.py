# backend/scripts/test_phase6.py
import sys
import os
from unittest.mock import patch, MagicMock

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=== Running Phase 6 Admin Operations Integration Tests ===")

    # Mock admin credentials
    admin_payload = {
        "uid": "test_admin_p6",
        "email": "admin@p6.com",
        "admin": True
    }
    admin_headers = {"Authorization": "Bearer mock_admin_token_p6"}

    with patch("firebase_admin.auth.verify_id_token", return_value=admin_payload):
        with patch("app.routers.admin.db") as mock_db:
            
            # Test 1: Update settings/rates
            print("Test 1: PUT /api/v1/admin/settings/rates...")
            rates_payload = {
                "rates": {
                    "compact": { "base_fare": 600.0, "extra_km_rate": 12.0 },
                    "premium": { "base_fare": 700.0, "extra_km_rate": 13.0 }
                }
            }
            response = client.put("/api/v1/admin/settings/rates", json=rates_payload, headers=admin_headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.json()["status"] == "success"
            print("✓ Settings/rates saved successfully!")

            # Test 2: Vehicles CRUD
            print("Test 2: Vehicles CRUD (POST, PUT, DELETE)...")
            # Create
            veh_payload = {"id": "WB02A1111", "model": "Suzuki Dzire", "tier": "premium"}
            response = client.post("/api/v1/admin/vehicles", json=veh_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["id"] == "WB02A1111"
            # Update
            veh_update = {"model": "Swift Dzire"}
            response = client.put("/api/v1/admin/vehicles/WB02A1111", json=veh_update, headers=admin_headers)
            assert response.status_code == 200
            # Delete
            response = client.delete("/api/v1/admin/vehicles/WB02A1111", headers=admin_headers)
            assert response.status_code == 200
            print("✓ Vehicles CRUD endpoints validated successfully!")

            # Test 3: Drivers CRUD
            print("Test 3: Drivers CRUD (POST, PUT, DELETE)...")
            drv_payload = {"id": "9876543210", "name": "Rajesh Kumar", "phone": "9876543210"}
            response = client.post("/api/v1/admin/drivers", json=drv_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["id"] == "9876543210"
            # Update
            drv_update = {"status": "inactive"}
            response = client.put("/api/v1/admin/drivers/9876543210", json=drv_update, headers=admin_headers)
            assert response.status_code == 200
            # Delete
            response = client.delete("/api/v1/admin/drivers/9876543210", headers=admin_headers)
            assert response.status_code == 200
            print("✓ Drivers CRUD endpoints validated successfully!")

            # Test 4: Locations CRUD
            print("Test 4: Locations CRUD (POST, PUT, DELETE)...")
            loc_payload = {"id": "salt_lake", "name": "Salt Lake Sector V", "type": "both", "lat": 22.57, "lng": 88.43}
            response = client.post("/api/v1/admin/locations", json=loc_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["id"] == "salt_lake"
            # Update
            loc_update = {"name": "Salt Lake Sector V Tech Park"}
            response = client.put("/api/v1/admin/locations/salt_lake", json=loc_update, headers=admin_headers)
            assert response.status_code == 200
            # Delete
            response = client.delete("/api/v1/admin/locations/salt_lake", headers=admin_headers)
            assert response.status_code == 200
            print("✓ Locations CRUD endpoints validated successfully!")

            # Test 5: Flat Fares CRUD
            print("Test 5: Flat Fares CRUD (POST, PUT, DELETE)...")
            ff_payload = {"id": "airport_howrah", "pickup_name": "Airport", "drop_name": "Howrah", "fares": {"compact": 350, "premium": 450}}
            response = client.post("/api/v1/admin/flat-fares", json=ff_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["id"] == "airport_howrah"
            # Update
            ff_update = {"fares": {"compact": 370, "premium": 470}}
            response = client.put("/api/v1/admin/flat-fares/airport_howrah", json=ff_update, headers=admin_headers)
            assert response.status_code == 200
            # Delete
            response = client.delete("/api/v1/admin/flat-fares/airport_howrah", headers=admin_headers)
            assert response.status_code == 200
            print("✓ Flat Fares CRUD endpoints validated successfully!")

            # Test 6: Offers CRUD
            print("Test 6: Offers CRUD (POST, PUT, DELETE)...")
            off_payload = {"code": "WELCOME100", "discount_value": 100, "discount_type": "flat"}
            response = client.post("/api/v1/admin/offers", json=off_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["code"] == "WELCOME100"
            # Update
            off_update = {"discount_value": 150}
            response = client.put("/api/v1/admin/offers/WELCOME100", json=off_update, headers=admin_headers)
            assert response.status_code == 200
            # Delete
            response = client.delete("/api/v1/admin/offers/WELCOME100", headers=admin_headers)
            assert response.status_code == 200
            print("✓ Offers CRUD endpoints validated successfully!")

            # Test 7: PATCH /bookings/{id}
            print("Test 7: PATCH /api/v1/admin/bookings/BK-TEST...")
            mock_db.collection.return_value.document.return_value.get.return_value.exists = True
            patch_payload = {"status": "confirmed", "driver_assignment": {"driver_name": "Bimal"}}
            response = client.patch("/api/v1/admin/bookings/BK-TEST", json=patch_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            print("✓ Booking PATCH updates validated successfully!")

            # Test 8: POST /bookings/manual
            print("Test 8: POST /api/v1/admin/bookings/manual...")
            manual_payload = {"booking_id": "BK-MANUAL", "status": "confirmed", "customer_id": "cust_123"}
            response = client.post("/api/v1/admin/bookings/manual", json=manual_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["booking_id"] == "BK-MANUAL"
            print("✓ Manual booking creation validated successfully!")

            # Test 9: POST /seed-fleet
            print("Test 9: POST /api/v1/admin/seed-fleet...")
            seed_payload = {
                "compact": [
                    { "vehicle_number": "WB02B2222", "driver_name": "Ramesh", "driver_phone": "9830098300" }
                ]
            }
            response = client.post("/api/v1/admin/seed-fleet", json=seed_payload, headers=admin_headers)
            assert response.status_code == 200
            assert response.json()["count"] == 1
            print("✓ Dynamic fleet seeding validated successfully!")

    print("\n✓✓✓ All Phase 6 Admin Operations Integration Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
