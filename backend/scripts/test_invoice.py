# backend/scripts/test_invoice.py
import sys
import os

# Ensure backend directory is in python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invoice_route_registration():
    """Verify that GET /api/v1/bookings/{booking_id}/invoice exists and enforces auth."""
    # Request without auth should return 401 Unauthorized
    response = client.get("/api/v1/bookings/BK-TEST-1234/invoice")
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
    print("[PASS] Invoice endpoint properly registered and requires authentication.")

if __name__ == "__main__":
    try:
        test_invoice_route_registration()
        print("ALL INVOICE ENDPOINT TESTS PASSED!")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
