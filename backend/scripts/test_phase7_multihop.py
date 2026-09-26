import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError
from app.schemas.pydantic_models import QuoteEstimateRequest
from app.routers.bookings import calculate_fare_breakdown

def test_quote_request_drop_locations_valid():
    req = QuoteEstimateRequest(
        category="local",
        pickup="Airport",
        drop="Howrah Station",
        date_string="2026-09-10",
        time_string="10:00",
        km=25.0,
        vehicle_tier="compact",
        drop_locations=["Salt Lake", "Esplanade", "Howrah Station"]
    )
    assert len(req.drop_locations) == 3

def test_quote_request_drop_locations_limit_exceeded():
    exceeded = False
    try:
        QuoteEstimateRequest(
            category="local",
            pickup="Airport",
            drop="Howrah Station",
            date_string="2026-09-10",
            time_string="10:00",
            km=25.0,
            vehicle_tier="compact",
            drop_locations=["Loc 1", "Loc 2", "Loc 3", "Loc 4", "Loc 5", "Loc 6"]
        )
    except ValidationError:
        exceeded = True
    assert exceeded, "Should have raised ValidationError for >5 drop locations"

def test_multi_hop_fare_calculation_distance_tariff():
    active_rates = {
        "rates": {
            "local": {
                "compact": {
                    "base_fare": 300,
                    "extra_km_rate": 15,
                    "waiting_rate": 2,
                    "night_charge": 100
                }
            },
            "global": {
                "local_included_km": 10.0,
                "night_charge_start": "23:59",
                "night_charge_end": "06:00"
            }
        }
    }
    
    # 35 km cumulative trip (10 km included, 25 extra km @ ₹15 = ₹375 -> Total ₹675)
    breakdown = calculate_fare_breakdown(
        ride_type="local",
        distance=35.0,
        days=None,
        tier="compact",
        hours=None,
        time_string="14:00",
        active_rates=active_rates,
        flat_metrics=None # Bypassed flat rate
    )
    assert breakdown["base_fare"] == 300
    assert breakdown["extra_km_charge"] == 375
    assert breakdown["total"] == 675

if __name__ == "__main__":
    test_quote_request_drop_locations_valid()
    print("[PASS] Valid drop_locations schema passed")
    test_quote_request_drop_locations_limit_exceeded()
    print("[PASS] Max 5 drop_locations validation passed")
    test_multi_hop_fare_calculation_distance_tariff()
    print("ALL PHASE 7 MULTI-HOP TESTS PASSED!")
