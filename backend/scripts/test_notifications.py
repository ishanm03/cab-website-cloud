# backend/scripts/test_notifications.py
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.email_service import (
    send_booking_received_email,
    send_booking_confirmed_email,
    send_booking_rejected_email,
    send_ride_started_email,
    send_ride_completed_email
)
from app.services.telegram_service import (
    send_telegram_booking_alert,
    format_clean_phone
)

def run_tests():
    sample_booking = {
        "booking_id": "BK-20261111-9999",
        "customer_details": {
            "name": "Ishan Mukherjee",
            "phone": "+91 9876543210",
            "email": "test-rider@example.com"
        },
        "trip_details": {
            "pickup_location": "Howrah Railway Station, Kolkata",
            "drop_location": "Netaji Subhash Chandra Bose International Airport, CCU",
            "pickup_date": "2026-11-15",
            "pickup_time": "08:30"
        },
        "fare_details": {
            "vehicle_tier": "Premium Sedan",
            "estimated_fare": 950
        },
        "driver_assignment": {
            "driver_name": "Rajesh Kumar",
            "driver_phone": "+91 9123456789",
            "vehicle_number": "WB-02-AK-1234"
        }
    }

    print("\n--- TEST 1: Phone Formatting ---")
    assert format_clean_phone("+91 9876543210") == "919876543210"
    assert format_clean_phone("9876543210") == "919876543210"
    print("Phone formatting PASSED")

    print("\n--- TEST 2: Email Booking Received ---")
    res1 = send_booking_received_email(sample_booking)
    assert res1 is True
    print("Booking received email PASSED")

    print("\n--- TEST 3: Email Ride Confirmed ---")
    res2 = send_booking_confirmed_email(sample_booking)
    assert res2 is True
    print("Ride confirmed email PASSED")

    print("\n--- TEST 4: Email Ride Rejected ---")
    res3 = send_booking_rejected_email(sample_booking, "All vehicles booked for this slot.")
    assert res3 is True
    print("Ride rejected email PASSED")

    print("\n--- TEST 5: Email Ride Started ---")
    res4 = send_ride_started_email(sample_booking)
    assert res4 is True
    print("Ride started email PASSED")

    print("\n--- TEST 6: Email Ride Completed ---")
    res5 = send_ride_completed_email(sample_booking)
    assert res5 is True
    print("Ride completed email PASSED")

    print("\n--- TEST 7: Telegram Booking Alert with 1-Click WhatsApp Holding URL ---")
    res6 = send_telegram_booking_alert(sample_booking)
    assert res6 is True
    print("Telegram booking alert PASSED")

    print("\nALL NOTIFICATION TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    run_tests()
