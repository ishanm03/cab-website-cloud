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
*Verification*: Open `http://localhost:5500` in your browser to view the landing page.

### 2. Stop Servers
Press `Ctrl+C` inside each terminal window to shut down the respective servers.

---

## 🛠️ Part 1: Backend Manual Testing (Postman / Insomnia)

All backend requests require an active Firebase ID Token as a bearer authorization header unless noted otherwise.

### Setup Headers
* **Key**: `Authorization`
* **Value**: `Bearer <FIREBASE_ID_TOKEN>` (obtained from the browser console via `await firebase.auth().currentUser.getIdToken()`).
* **Content-Type**: `application/json`

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

## 💻 Part 2: Frontend UI manual verification

### Test Case 2.1: Booking Step 1 Validation
1. Open the booking panel (`http://localhost:5500/modules/booking/booking.html` or CTA click).
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

1. Open your browser's developer console (F12 or Cmd+Option+J) on `http://localhost:5500`.
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
