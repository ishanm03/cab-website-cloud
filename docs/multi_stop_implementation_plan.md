# Implementation Plan: Multi-Drop Locations Support (All Ride Categories)

This plan outlines the technical design, data modeling options, and implementation steps to support multiple drop locations (up to 5 stops total) across all ride categories (Local, Rental, Intercity, Outstation).

---

## Status: PARKED
> [!NOTE]
> This feature is currently parked as requested. We will resume implementation after completing the urgent enhancement.

---

## Modeling Options

### Option A: Dynamic Inline List (Recommended)
* **UI Design**: The Destination input field on the booking wizard is placed inside a dynamic list container. Clicking a `+ Add Stop` button appends a new destination row (dropdown + custom address input). Each added row has a trash icon to delete it. Maximum stops capped at 5.
* **Map Rendering**: Plots markers for the Pickup location and all added drop locations. It fetches OSRM routes sequentially (Leg 1: `Pickup -> Drop 1`, Leg 2: `Drop 1 -> Drop 2`, etc.) and draws a continuous polyline.
* **Pricing & Database**:
  * We calculate the cumulative distance (sum of all leg distances: `A + B + C + D + E`).
  * In Firestore, we add a new field `drop_locations: string[]` containing the sequence of stops (e.g. `["Salt Lake", "Kolkata Airport", "Howrah Station"]`).
  * For backward compatibility with existing reporting, the standard `drop_location` string field is populated with the final destination (e.g. `Howrah Station`).
  * Bypasses flat-rate matrices (since flat rates are point-to-point only) and falls back to distance-based tariff calculations (`total_km * rate_per_km`).

### Option B: Unified Waypoint List (Simpler UI, Less granular)
* **UI Design**: Keep the single destination dropdown as the primary, but display a text field underneath: `"Enter additional stopovers (comma-separated, max 4)"`.
* **Map Rendering**: Renders a straight-line fallback or only plots the primary pickup and final drop. It does not fetch multi-stop routes dynamically.
* **Pricing**: Calculates distance purely between pickup and final drop, ignoring intermediate waypoints for pricing calculations, OR requires manual admin routing override.
* *Critique*: Doesn't satisfy the requirement of calculating `A + B + C + D + E` automatically.

---

## Open Questions & Considerations for When Resumed
1. **Rental Stops**: For Rental services, since the trip is charged hourly rather than by point-to-point destination, do we still calculate the cumulative distance of the stops for pricing, or is it purely for driver instructions (with base/extra rates applied as normal)?
2. **Intermediate Custom Locations**: If intermediate stops are custom locations, should the geocoder automatically search and plot them sequentially? (Yes, following the same Nominatim debounced geocoding logic implemented for Step 1).

---

## Proposed Changes

### Component 1: Rider Booking UI & Flow

#### [booking.html](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/booking.html)
* Replace the static drop location container with a dynamic stopover list container:
  ```html
  <div id="drop-locations-container" class="space-y-3">
      <!-- Stop rows will be dynamically appended here -->
  </div>
  <button type="button" id="add-stop-btn" class="mt-2 text-amber-500 hover:text-amber-400 font-semibold text-xs inline-flex items-center gap-1">
      ➕ Add Stopover Location (Max 5)
  </button>
  ```

#### [bookingUI.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/bookingUI.js)
* **Dynamic Stop UI**:
  * Track active drop locations in an array.
  * Implement `handleAddStop()` to instantiate a new drop row template (including custom address toggle matching the primary drop select behavior).
  * Enforce maximum limit of 5 drop fields. Disable `+ Add Stop` button when limit is reached.
* **Geocoding & OSRM Sequencing**:
  * Loop through the list of stops sequentially.
  * Resolve coordinates (either predefined or dynamic geocoding for custom stop inputs).
  * Fetch OSRM legs in sequence (Leg 1: `Pickup -> Drop 1`, Leg 2: `Drop 1 -> Drop 2`, etc.) using `fetchOSRMRoute()`.
  * Sum up distance parameters: `totalDistanceKm = leg1 + leg2 + ... + legN`.
  * Render the dynamic path on the Leaflet Map.
* **Payload Commit**:
  * Include `drop_locations` array in `currentRouteData` and commit to booking request payloads under `trip_details.drop_locations`.

---

### Component 2: Admin Dashboard Manual Booking

#### [admin.html](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/admin/admin.html)
* Add a similar dynamic stops container inside the Admin manual booking form to support up to 5 manual stops.

#### [adminUI.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/admin/adminUI.js)
* **Form & Routing**:
  * Wire up the multi-stop inputs in the manual form.
  * Sequentially trace and map the legs. Sum up distances to calculate the estimated fare breakdown.
* **Card Rendering**:
  * Update `buildBookingCardContentHtml` to display the list of stops as a sequential route path (e.g. `Salt Lake ➔ Airport ➔ Howrah Station`).

---

### Component 3: Backend & Integration Tests

#### [bookings.py](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/backend/app/routers/bookings.py)
* **Backend Validation**:
  * Expect an optional `drop_locations` array field in the request model.
  * If present, validate that it has at most 5 elements.
  * For outstation/intercity doubling calculations, calculate base rate on the cumulative distance parameters.

#### [NEW] [test_phase7_multidrop.py](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/backend/scripts/test_phase7_multidrop.py)
* Test suite to verify multi-drop fare calculations, backend schema support, and validation limits.

---

## Verification Plan

### Automated Tests
* Run `test_phase7_multidrop.py` to assert correct distance accumulations and limit validations.
* Run existing test suites (`test_phase1.py` through `test_phase6.py`) to ensure no regressions.

### Manual Verification
* Add 3 stop locations on the Rider Page. Verify the map renders the sequential polyline.
* Proceed to checkout and confirm that the fare calculation represents the sum distance.
* Check the Admin Panel booking card and verify that all 3 stop names are rendered sequentially.
