# 🚖 SethCabs Local Manual Testing Guide

This guide details how to control local servers and systematically verify every capability in the **SethCabs** application. All tests are structured for manual execution.

---

## ⚙️ Running Local Servers

### 1. Start Servers
To launch both frontend and backend development environments:

#### Backend Server (FastAPI)
Open a terminal window and run:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Verification*: Open `http://127.0.0.1:8000/api/v1/health` in your browser. It should return `{"status": "ok"}`.

#### Frontend Server (Python HTTP)
Open a second terminal window and run:
```bash
python3 -m http.server 5500
```
*Verification*: Open `http://127.0.0.1:5500` in your browser to view the landing page.

### 2. Stop Servers
Press `Ctrl+C` inside each terminal window to shut down the respective servers.

---

## 🛠️ Part 1: Backend Manual Testing (Postman / Insomnia)

All backend requests require an active Firebase ID Token as a bearer authorization header unless noted otherwise.

### Setup & Credentials Configuration

#### 1. Retrieve the Firebase ID Token
Open the website in your browser (`http://127.0.0.1:5500`), log in, open the browser's developer console (F12), and run:
```javascript
// Dynamically import the auth instance and copy the token to your clipboard
const { auth } = await import("./modules/shared/firebase.js");
await auth.currentUser.getIdToken();
```

#### 2. Configure Insomnia Environment
1. Launch **Insomnia**.
2. Create a new **Design Document** or **Request Collection** named `SethCabs Local Testing`.
3. Click the **Environment** dropdown menu in the upper-left corner (typically named `Base Environment` or `Manage Environments` (Cmd+E)).
4. Paste the following JSON configuration:
   ```json
   {
     "base_url": "http://127.0.0.1:8000/api/v1",
     "firebase_token": "PASTE_YOUR_COPIED_TOKEN_HERE"
   }
   ```
5. Click **Done**.

#### 3. Setup Request Authorization & Headers
For each test case request in Insomnia:
1. Set the URL using the environment variable: `{{ _.base_url }}/me/profile`
2. Select the **Auth** tab located directly below the request URL input bar.
3. Select **Bearer Token** from the dropdown menu.
4. Input the environment variable in the **Token** field: `{{ _.firebase_token }}` (Insomnia will autocomplete this when you type `{{`).
5. Under the **Header** tab, confirm that `Content-Type` is set to `application/json`.

---

### Test Case 1.1: Fetch Profile
* **Endpoint**: `GET http://127.0.0.1:8000/api/v1/me/profile`
* **Expected Success (HTTP 200)**:
  ```json
  {
    "uid": "test_uid_123",
    "name": "Ishan Mukherjee",
    "city": "Kolkata",
    "phone": "9830098300",
    "email": "rider@test.com",
    "auth_provider": "password",
    "status": "active"
  }
  ```

---

### Test Case 1.2: Request Fare Quote Estimate
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/quotes/estimate`
* **Request Body**:
  ```json
  {
    "category": "local",
    "pickup": "Howrah Station",
    "drop": "Airport",
    "date_string": "2026-08-10",
    "time_string": "14:30",
    "km": 18.5,
    "vehicle_tier": "premium",
    "promo_code": "WELCOME100"
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "quote_id": "QT-1722940200-ABCD",
    "base_fare": 650.0,
    "discount_amount": 100.0,
    "estimated_fare": 550.0,
    "promo_code": "WELCOME100",
    "signature": "da66e04d4715fec325b3a3...",
    "expires_at": "2026-08-06T11:15:00Z"
  }
  ```

---

### Test Case 1.3: Create Booking (Signed Checkout)
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/bookings`
* **Request Body**:
  ```json
  {
    "trip_details": {
      "ride_type": "local",
      "pickup_location": "Howrah Station",
      "drop_location": "Airport",
      "pickup_date": "2026-08-10",
      "pickup_time": "14:30",
      "pickup_coords": [22.5833, 88.3414],
      "drop_coords": [22.6547, 88.4467]
    },
    "fare_details": {
      "vehicle_tier": "premium",
      "estimated_km": 18.5,
      "base_fare": 650.0,
      "discount_amount": 100.0,
      "promo_code": "WELCOME100",
      "estimated_fare": 550.0
    },
    "quote_id": "QT-1722940200-ABCD",
    "quote_signature": "da66e04d4715fec325b3a3...",
    "expires_at": "2026-08-06T11:15:00Z"
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "booking_id": "BK-20260810-XXXX"
  }
  ```
* **Expected Replay Attack Block (HTTP 400)**: Submit the same payload twice. The second submission must yield:
  ```json
  {
    "detail": "Failed to submit booking: Quote signature has already been checked out."
  }
  ```

---

### Test Case 1.4: Update Settings pricing rates (Admin only)
* **Endpoint**: `PUT http://127.0.0.1:8000/api/v1/admin/settings/rates`
* **Request Body**:
  ```json
  {
    "rates": {
      "local": {
        "compact": { "base_fare": 600, "extra_km_rate": 12, "waiting_rate": 3, "night_charge": 250 },
        "premium": { "base_fare": 700, "extra_km_rate": 13, "waiting_rate": 4, "night_charge": 350 },
        "suv": { "base_fare": 800, "extra_km_rate": 14, "waiting_rate": 5, "night_charge": 450 },
        "muv": { "base_fare": 900, "extra_km_rate": 16, "waiting_rate": 5, "night_charge": 550 }
      }
    }
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "active_version_id": "R-1722943800000"
  }
  ```
* **Expected Block regular rider (HTTP 403)**: Log in as a rider without admin custom claims. Make the request. Must yield:
  ```json
  {
    "detail": "Admin permissions required."
  }
  ```

---

### Test Case 1.5: Submit Completed Ride Feedback
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/bookings/BK-20260810-XXXX/feedback`
* **Request Body**:
  ```json
  {
    "rating": 5,
    "comments": "Safe driving and clean sedan car."
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success"
  }
  ```
* **Expected Block Duplicate Review (HTTP 400)**: Resubmit feedback on the same booking. Must yield:
  ```json
  {
    "detail": "Feedback has already been submitted for this ride."
  }
  ```

---

### Test Case 1.6: Database Cleanup Operations (Admin only)
* **Endpoint**: `DELETE http://127.0.0.1:8000/api/v1/admin/db/cleanup`

#### Scenario A: Delete Specific Document IDs
* **Request Body**:
  ```json
  {
    "collection_name": "bookings",
    "document_ids": ["BK-20260810-XXXX", "BK-20260810-YYYY"]
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "collection_name": "bookings",
    "deleted_count": 2
  }
  ```

#### Scenario B: Clear Entire Collection (with Safety Flag)
* **Request Body**:
  ```json
  {
    "collection_name": "bookings",
    "confirm_delete_all": true
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "collection_name": "bookings",
    "deleted_count": 48
  }
  ```

#### Scenario C: Clear Entire Collection (Accidental without Safety Flag)
* **Request Body**:
  ```json
  {
    "collection_name": "bookings",
    "confirm_delete_all": false
  }
  ```
* **Expected Failure (HTTP 400)**:
  ```json
  {
    "detail": "Confirm delete all flag must be set to true to clear the entire collection."
  }
  ```

---

### Test Case 1.7: Vehicles & Drivers Roster CRUD (Admin only)

#### 1. Add new Vehicle
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/vehicles`
* **Request Body**:
  ```json
  {
    "plate_number": "WB-02-B-8888",
    "model": "Hyundai Verna",
    "tier": "premium",
    "status": "active",
    "passengers": 4,
    "address": "Kolkata Hub Garage"
  }
  ```
* **Expected Success (HTTP 200)**: returns `{"id": "WB02B8888", "status": "success"}`

#### 2. Add new Driver
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/drivers`
* **Request Body**:
  ```json
  {
    "name": "Subhash Chandra",
    "phone": "9876543210",
    "license_number": "DL-WB02-2026888",
    "status": "active",
    "assigned_vehicle_id": "WB02B8888",
    "address": "Driver Quarters, Salt Lake"
  }
  ```
* **Expected Success (HTTP 200)**: returns `{"id": "9876543210", "status": "success"}`

#### 3. Verify Bidirectional Link
* **Endpoint**: `GET http://127.0.0.1:8000/api/v1/admin/vehicles`
* **Expected Success (HTTP 200)**: The returned list includes `WB02B8888` with `assigned_driver_id` correctly linked as `9876543210`.

---

### Test Case 1.8: Predefined Locations & Flat Fares CRUD (Admin only)

#### 1. Add flat fare overrides
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/flat_fares`
* **Request Body**:
  ```json
  {
    "pickup_name": "Sealdah Station",
    "drop_name": "New Town",
    "fares": {
      "compact": 450,
      "premium": 600,
      "suv": 800,
      "muv": 1100
    }
  }
  ```
* **Expected Success (HTTP 200)**: returns `{"id": "sealdah_station_new_town", "status": "success"}`

---

### Test Case 1.9: Offers & Coupons Manager (Admin only)

#### 1. Add Promo Code
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/offers`
* **Request Body**:
  ```json
  {
    "code": "FESTIVE500",
    "discount_type": "flat",
    "discount_value": 500.0,
    "min_fare_threshold": 2000.0,
    "status": "active"
  }
  ```
* **Expected Success (HTTP 200)**: returns `{"id": "FESTIVE500", "status": "success"}`

---

### Test Case 1.10: Booking State Transitions & Actions (Admin only)

#### 1. Allocate Driver and Approve Booking
* **Endpoint**: `PATCH http://127.0.0.1:8000/api/v1/admin/bookings/BK-20260810-XXXX`
* **Request Body**:
  ```json
  {
    "status": "confirmed",
    "driver_assignment": {
      "driver_id": "9876543210",
      "driver_name": "Subhash Chandra",
      "driver_phone": "9876543210",
      "vehicle_id": "WB02B8888",
      "vehicle_model": "Hyundai Verna",
      "vehicle_number": "WB-02-B-8888"
    }
  }
  ```
* **Expected Success (HTTP 200)**: returns updated booking metadata.

#### 2. Start Trip
* **Endpoint**: `PATCH http://127.0.0.1:8000/api/v1/admin/bookings/BK-20260810-XXXX`
* **Request Body**:
  ```json
  {
    "status": "active"
  }
  ```
* **Expected Success (HTTP 200)**: booking status updates to `active`.

#### 3. Complete Trip & Set Payment Paid
* **Endpoint**: `PATCH http://127.0.0.1:8000/api/v1/admin/bookings/BK-20260810-XXXX`
* **Request Body**:
  ```json
#### 3. Complete Trip & Set Payment Paid
* **Endpoint**: `PATCH http://127.0.0.1:8000/api/v1/admin/bookings/BK-20260810-XXXX`
* **Request Body**:
  ```json
  {
    "status": "completed",
    "payment_status": "paid"
  }
  ```
* **Expected Success (HTTP 200)**: booking status updates to `completed`.

---

### Test Case 1.11: Super Admin User Role Promotion & Demotion (Super Admin only)

#### 1. Promote Rider to Admin
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/users/promote`
* **Auth**: Must be logged in as a Super Admin whose email is listed in `SUPER_ADMIN_EMAILS` (e.g., `admin@ishancabs.com`).
* **Request Body**:
  ```json
  {
    "email": "newadmin@ishancabs.com",
    "role": "admin"
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "uid": "USER_FIREBASE_UID_123",
    "email": "newadmin@ishancabs.com",
    "role": "admin",
    "admin_claim": true
  }
  ```

#### 2. Demote Admin back to Rider
* **Endpoint**: `POST http://127.0.0.1:8000/api/v1/admin/users/promote`
* **Request Body**:
  ```json
  {
    "email": "newadmin@ishancabs.com",
    "role": "rider"
  }
  ```
* **Expected Success (HTTP 200)**:
  ```json
  {
    "status": "success",
    "uid": "USER_FIREBASE_UID_123",
    "email": "newadmin@ishancabs.com",
    "role": "rider",
    "admin_claim": false
  }
  ```

#### 3. Access Denied for Regular Admin
* **Auth**: Log in as a regular admin (not listed in `SUPER_ADMIN_EMAILS`). Submit promotion request.
* **Expected Block (HTTP 403)**:
  ```json
  {
    "detail": "Forbidden: Super Admin permissions required to manage user roles."
  }
  ```

---

## 💻 Part 2: Frontend UI manual verification

### Test Case 2.1: Booking Step 1 Validation
1. Open the booking panel (`http://127.0.0.1:5500/modules/booking/booking.html` or CTA click).
2. Enter a pickup date and time in the past or within 1 hour from now.
3. Click "Next".
4. **Assert**: An alert badge pops up stating `"Minimum scheduling lead time of 2 hours is required."` and blocks step transition.

### Test Case 2.2: Dynamic Fares Card Rendering
1. Fill step 1 with valid values (date in future, pickup: Howrah Station, drop: Airport).
2. Select "Local Ride" and click "Next".
3. **Assert**: The interface transitions to Step 2 showing the class cards (Compact, Premium, SUV, MUV).
4. **Assert**: The card prices are computed automatically (Compact is cheaper than Premium). OSRM distance km matches values shown in the review breakdown.

### Test Case 2.3: Rider Activity List History
1. Log in to the application.
2. Click the "Rider Activity / History" CTA.
3. **Assert**: Renders all past bookings sorted chronologically descending. Renders map routes with red pickup and drop markers.
4. Locate a completed booking. Renders a feedback comment rating modal.

### Test Case 2.4: Admin Dashboard Pending Roster Allocations UI
1. Open the Admin Console (`http://127.0.0.1:5500/modules/admin/admin.html`).
2. Log in using an Admin account credentials.
3. **Assert**: The dashboard renders a grid table of active/pending bookings.
4. Locate a booking in the "Pending Approval" queue. Click **Manage Allocations**.
5. **Assert**: An assignment overlay menu pops up showing the active driver roster and vehicle catalog dropdown options.
6. Select a driver (e.g. Ramesh) and vehicle (e.g. WB02B2222) and click **Approve & Dispatch**.
7. **Assert**: The overlay closes, the booking row status updates to "Confirmed", and the manual page table updates in real-time.

### Test Case 2.5: Admin Dashboard Fleet & Roster Control UI
1. Navigate to the **Fleet Registry** or **Drivers Directory** tabs inside the Admin Console.
2. Click **Register Vehicle**.
3. Input Plate Number `WB-02-B-9999`, Model `Suzuki Ertiga`, select Tier `suv`, select Status `active`, and click **Save**.
4. **Assert**: The new vehicle appears instantly in the fleet registry table list.
5. Click **Add Driver**.
6. Input Name `Pranab Roy`, Phone `9830012345`, select Assigned Vehicle `WB02B9999`, select Status `active`, and click **Save**.
7. **Assert**: The driver is saved and successfully linked. Open the vehicle details card and assert that Pranab Roy is bidirectionally shown as the active driver.

### Test Case 2.6: Admin Dashboard Settings & Fares Manager UI
1. Navigate to the **Pricing settings** tab in the Admin Console.
2. The UI renders input cards for Local, Rental, and Intercity rates.
3. Modify the base fare of Local Compact from `550` to `600`.
4. Click **Publish Fares Configuration**.
5. **Assert**: A success banner displays `"Tariff configurations published and versioned successfully!"`.
6. Open the booking panel as a rider (`http://127.0.0.1:5500/modules/booking/booking.html`) and check a Local Compact estimate. Assert that the fare calculations now reflect the updated base fare of `600`.

---

## 🔄 Part 3: End-to-End Integration Verification Flow

Perform this sequential cycle to verify the complete system functionality:

1. **Rider Checkout**:
   * Rider books a Compact trip from "Airport" to "Salt Lake" scheduled tomorrow at 10:00 AM.
   * Renders checkout review invoice. Renders applied promo code `WELCOME100` discount deduction.
   * Rider clicks Confirm. Renders WhatsApp redirection chat window showing pre-compiled messages.

2. **Admin Allocations**:
   * Log in to the Admin Dashboard (`modules/admin/admin.html`).
   * Select the "Pending Bookings" roster queue. The newly booked Compact ride is visible.
   * Click "Manage Allocations" on the booking row.
   * Select an available driver (e.g. Ramesh) and vehicle (compact Suzuki Dzire).
   * Click "Approve & Dispatch".
   * **Assert**: Booking status updates immediately to `Confirmed` in the table.

3. **Trip Execution**:
   * Admin updates status to "Start Trip".
   * **Assert**: Booking status changes to `Active` immediately.
   * Admin updates status to "Complete Trip".
   * **Assert**: Booking status changes to `Completed`. Renders payment state update to `Paid`.

4. **Feedback Submission**:
   * Log back into the Rider profile, open "Activity History".
   * Locate the completed ride. Renders feedback submission review input box.
   * Input star rating 5 and review comment, click Submit.
   * **Assert**: Renders "Review Submitted!" alert box.

---

## ⚡ Part 4: Non-Functional testing

### Test Case 4.1: Firestore Write Lockdown Verification
Confirm that direct writes from the browser to Firestore database paths are strictly blocked (verifying write rules hardening).

1. Open your browser's developer console (F12 or Cmd+Option+J) on `http://127.0.0.1:5500`.
2. Execute the following database write request:
   ```javascript
   import { db } from "./modules/shared/firebase.js";
   import { collection, addDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
   addDoc(collection(db, "bookings"), { test_value: 1 }).then(console.log).catch(console.error);
   ```
3. **Assert**: Prints `FirebaseError: Missing or insufficient permissions` inside the console logs, validating that all direct mutations are blocked.

### Test Case 4.2: Input Validation Boundaries
* **Negative Values**: Submit estimation requests containing negative kilometers (e.g. `km: -20`). Confirm that backend validators block the request with `HTTP 422 Unprocessable Entity`.
* **Expired Quotes**: Wait 31 minutes after requesting an estimation. Submit booking using the signature. Confirm that backend returns `HTTP 400 Bad Request` with `"Quote signature has expired"`.
* **Tampered Fare values**: Intercept quote request response. Modify `estimated_fare` to `1.0` in the checkout payload and submit `POST /bookings`. Confirm that signature validation fails with `HTTP 400 Bad Request`.

### Test Case 4.3: Missing Database Settings Rates Document Behavior
Confirm that the application handles a missing or deleted settings rates document gracefully without calculating obsolete pricing.

1. Access your backend database (or run a local test server without seeding the `settings/rates` document).
2. Call `POST /quotes/estimate` or open the booking panel in the frontend browser and proceed to Step 2.
3. **Assert (Backend)**: Requests return `HTTP 503 Service Unavailable` with body `{"detail": "Tariff rates configuration is missing from the database."}`.
4. **Assert (Frontend)**: Browser displays an alert banner `"Error fetching rates: HTTP error 503"` and blocks progression from Step 1, preventing the rider from placing a booking.

