# backend/scripts/test_auth.py
import sys
import os
from unittest.mock import patch

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth
from app.main import app

client = TestClient(app)

def run_tests():
    print("=== Running Backend Foundation & Auth Integration Tests ===")

    # Test 1: Health check route
    print("Test 1: GET /api/v1/health...")
    response = client.get("/api/v1/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["data"]["status"] == "healthy"
    assert "timestamp" in data["meta"]
    print("✓ Health check route passed!")

    # Test 2: Protected route - Missing Credentials
    print("Test 2: GET /api/v1/me/test-auth (No Token)...")
    response = client.get("/api/v1/me/test-auth")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print("✓ Protected route blocked missing token successfully!")

    # Test 3: Protected route - Invalid Token
    print("Test 3: GET /api/v1/me/test-auth (Invalid Token)...")
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.side_effect = firebase_auth.InvalidIdTokenError("Invalid token error details")
        
        headers = {"Authorization": "Bearer invalid_mock_token_123"}
        response = client.get("/api/v1/me/test-auth", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "Invalid authentication token" in response.json()["detail"]
    print("✓ Protected route blocked invalid token successfully!")

    # Test 4: Protected route - Expired Token
    print("Test 4: GET /api/v1/me/test-auth (Expired Token)...")
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.side_effect = firebase_auth.ExpiredIdTokenError("Expired token error details", "cause")
        
        headers = {"Authorization": "Bearer expired_mock_token_123"}
        response = client.get("/api/v1/me/test-auth", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "Authentication token has expired" in response.json()["detail"]
    print("✓ Protected route blocked expired token successfully!")

    # Test 5: Protected route - Valid Non-Admin Rider Token
    print("Test 5: GET /api/v1/me/test-auth (Valid Rider Token)...")
    mock_payload = {
        "uid": "rider_user_123",
        "email": "rider@example.com",
        "admin": False
    }
    with patch("firebase_admin.auth.verify_id_token", return_value=mock_payload):
        headers = {"Authorization": "Bearer valid_rider_token_123"}
        response = client.get("/api/v1/me/test-auth", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        res_data = response.json()["data"]
        assert res_data["uid"] == "rider_user_123"
        assert res_data["admin"] is False
    print("✓ Protected route verified rider token successfully!")

    # Test 6: Admin Route - Restricted for Non-Admin
    print("Test 6: GET /api/v1/admin/test-rbac (Rider accessing Admin)...")
    with patch("firebase_admin.auth.verify_id_token", return_value=mock_payload):
        headers = {"Authorization": "Bearer valid_rider_token_123"}
        response = client.get("/api/v1/admin/test-rbac", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Admin permissions are required" in response.json()["detail"]
    print("✓ Admin RBAC blocked non-admin user successfully!")

    # Test 7: Admin Route - Allowed for Admin
    print("Test 7: GET /api/v1/admin/test-rbac (Admin accessing Admin)...")
    mock_admin_payload = {
        "uid": "admin_user_456",
        "email": "admin@example.com",
        "admin": True
    }
    with patch("firebase_admin.auth.verify_id_token", return_value=mock_admin_payload):
        headers = {"Authorization": "Bearer valid_admin_token_123"}
        response = client.get("/api/v1/admin/test-rbac", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        res_data = response.json()["data"]
        assert res_data["uid"] == "admin_user_456"
        assert res_data["admin"] is True
        assert "Welcome, Admin!" in res_data["message"]
    print("✓ Admin RBAC authorized admin user successfully!")

    print("\n✓✓✓ All Backend Foundation & Auth Integration Tests Passed! ✓✓✓")

if __name__ == "__main__":
    run_tests()
