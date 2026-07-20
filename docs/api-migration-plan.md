# FastAPI API Migration Plan for IshanCabs (Version 0.4)

## Summary
This migration plan details the conversion of IshanCabs from a client-direct Firebase architecture to a secure, modular FastAPI backend. Version 0.4 incorporates an **interleaved end-to-end delivery strategy**, anti-replay signed quote validation, presigned upload URLs, stateless real-time admin reads, and fine-grained Firestore security rules.

---

### Core Architectural Decisions for Version 0.4

1. **Stateless Hybrid Real-Time Architecture**:
   * **Reads**: Clients (both Riders and Admins) continue using the client-side Firebase SDK to establish `onSnapshot` real-time listeners for data display. This preserves instant synchronization without custom WebSocket/SSE backend state complexity.
   * **Writes**: 100% of data mutations (booking requests, approvals, status transitions, fleet/driver edits, catalog updates) are routed exclusively through the FastAPI backend.
   * **Security**: Client write access is locked down in Firestore Security Rules to **strictly write-disabled** (`allow write: if false;`).

2. **Interleaved Feature Delivery (End-to-End Migration)**:
   * Rather than completing all backend APIs before starting frontend work, each phase pair builds the backend routes **and immediately refactors the corresponding frontend components**. This ensures continuous integration and early verification of contract compatibility.

3. **OSRM Backend Ownership**:
   * Distance calculation, matrix routing, and route polyline generation tasks are moved entirely to the backend (`core/routing.py`). The client passes only origin/destination coordinate pairs, preventing malicious distance or fare tampering.

4. **Anti-Replay Signed Quote Engine**:
   * The backend generates fare quotes and cryptographically signs them using HMAC-SHA256 with a server secret (`quote_signature`).
   * **Payload Scope**: The signature covers `base_fare`, `distance_km`, `vehicle_tier`, `pickup_coords`, `drop_coords`, `user_id`, `applied_discount`, `final_fare`, and a `15-minute expiration timestamp`.
   * **Anti-Replay**: The backend checks for duplicate signature hashes on booking creation to prevent a single quote from being used multiple times.

5. **Direct Media Uploads via Presigned URLs**:
   * Instead of streaming binary files through FastAPI (consuming Uvicorn RAM and worker threads), the backend generates Firebase Storage presigned upload URLs or tokens. The frontend uploads files directly to Firebase Storage and passes the returned media URL to backend endpoints.

6. **Atomic Firestore Transactions**:
   * Critical mutations (driver/vehicle allocations, ride status transitions) use Python Firestore Transactions to eliminate race conditions.

7. **Firebase Custom Claims for RBAC & Forced Token Refresh**:
   * Custom claims (`{"admin": true}`) govern access to admin backend routes. Frontend authentication handlers enforce `user.getIdToken(true)` upon role changes or admin session initialization to prevent stale cached JWT tokens.

---

## Phase 0: Discovery and Contract Freeze
**Goal**: Lock down current frontend-to-data schemas and standardized API envelopes to prevent regression.

### 🏃 Sprint 0.1: Contract & Schema Freezing
* **Backend & System Tasks**:
  1. Document all direct Firestore collections: `users`, `bookings`, `vehicles`, `drivers`, `offers`, `settings/rates`, `locations`, `flat_fares`.
  2. Map out payload structures, identifying required vs optional attributes (capacity, coordinates, address strings).
  3. Freeze standard JSON response envelopes for backend APIs:
     * Success: `{ "data": ..., "meta": ... }`
     * Error: `{ "error": { "code": "string", "message": "string", "details": ... } }`
* **Test & Validation Scenarios**:
  * Create Pydantic JSON schema validation mocks representing user profiles, booking invoices, and driver assignments to serve as unit test fixtures.

---

## Phase 1: Backend Scaffolding, Security & Auth
**Goal**: Establish the FastAPI server foundation and verify Firebase Custom Claims authentication context.

### 🏃 Sprint 1.1: FastAPI Setup & Health Checks
* **Backend Tasks**:
  1. Create Python virtual environment and layout under `backend/`.
  2. Implement `backend/app/main.py` with Uvicorn runtime config.
  3. Configure environment variable loader (`core/config.py`) handling CORS origins, HMAC quote secrets, and service account credentials.
* **Test & Validation Scenarios**:
  * `GET /api/v1/health` returns HTTP 200 with standard health check status metadata.

### 🏃 Sprint 1.2: Firebase SDK & Auth Authentication Context
* **Backend Tasks**:
  1. Initialize Firebase Admin SDK globally in `backend/app/core/firebase.py`.
  2. Code the auth dependency `core/auth.py` to decode Firebase ID tokens, handle validation errors, and yield user contexts (`AuthenticatedUser`).
* **Test & Validation Scenarios**:
  * `GET /api/v1/me/test-auth`:
    * HTTP 401 when no token is provided.
    * HTTP 401 on expired/malformed token.
    * HTTP 200 with `uid` payload on valid token.

### 🏃 Sprint 1.3: Custom Claims RBAC Seeder & Token Refresh Handler
* **Backend & Frontend Tasks**:
  1. Build admin dependency checker: `require_admin` verifying `token_claims.get("admin") == True`.
  2. Create CLI script `backend/scripts/make_admin.py` to set custom claims on specified staff accounts.
  3. Update frontend `authService.js` to trigger `getIdToken(true)` upon login or role check to force token claim update.
* **Test & Validation Scenarios**:
  * Execute `make_admin.py`. Access admin-guarded route with fresh token, verifying HTTP 200 instead of HTTP 403.

---

## Phase 2: Profiles & Catalogs (End-to-End)
**Goal**: Migrate profile CRUD and catalog lookup endpoints, and integrate with the frontend immediately.

### 🏃 Sprint 2.1: User Profile Manager
* **Backend Tasks**:
  1. Implement routers `/api/v1/me/profile` (GET, PUT).
  2. Create repository handlers reading/writing to Firestore `users` collection. Block edits to read-only parameters (`role`, `uid`, `email`).
* **Frontend Integration Tasks**:
  1. Refactor frontend `authService.js` / profile components to fetch profile via `GET /api/v1/me/profile` and update profile via `PUT /api/v1/me/profile`.
* **Test & Validation Scenarios**:
  * Verify user profile updates succeed through API and update UI without requiring direct Firestore writes.

### 2.2: Settings & Metadata Catalog Reads
* **Backend Tasks**:
  1. Move public catalog queries behind API endpoints: `GET /api/v1/settings/rates`, `GET /api/v1/locations`, `GET /api/v1/flat-fares`.
* **Frontend Integration Tasks**:
  1. Refactor catalog loaders in frontend to fetch rates and locations from backend endpoints with local caching.
* **Test & Validation Scenarios**:
  * Compare API JSON responses with frontend configuration files for 100% field compliance.

### 🏃 Sprint 2.3: Promo Offer Validations
* **Backend Tasks**:
  1. Implement `POST /api/v1/offers/validate`.
  2. Backend fetches offer from Firestore, validates expiry, active status, and computes percentage/flat discount.
* **Frontend Integration Tasks**:
  1. Update fare breakdown UI to call `/api/v1/offers/validate` when user applies a promo code.
* **Test & Validation Scenarios**:
  * Test invalid code (404), expired code (400), and valid code (returns computed discount total).

---

## Phase 3: Secure Routing, Signed Quote & Booking Creation (End-to-End)
**Goal**: Move route calculation, quote cryptographic signing, and booking creation to backend, then refactor checkout UI.

### 🏃 Sprint 3.1: Server-Side Routing Utilities
* **Backend Tasks**:
  1. Implement `backend/app/core/routing.py` with OSRM matrix query fetcher and Haversine straight-line distance fallback.
* **Test & Validation Scenarios**:
  * Unit test `routing.py` with coordinate pairs; verify distance calculation accuracy and mock OSRM fallback behavior.

### 🏃 Sprint 3.2: Anti-Replay Signed Quote Engine
* **Backend Tasks**:
  1. Implement `POST /api/v1/bookings/quote`.
  2. Calculate trip distance via `routing.py` and compute pricing across available vehicle tiers.
  3. Generate HMAC-SHA256 signature string covering: `base_fare`, `distance_km`, `vehicle_tier`, `pickup_coords`, `drop_coords`, `user_id`, `applied_discount`, `final_fare`, and `expires_at` (15 min).
* **Test & Validation Scenarios**:
  * Confirm signature changes if any fare or coordinate payload parameter is tampered with.

### 🏃 Sprint 3.3: Booking Document Writes & Checkout Refactor
* **Backend Tasks**:
  1. Implement `POST /api/v1/bookings`.
  2. Verify quote signature validity, expiration timestamp, and anti-replay nonce (ensuring quote signature has not already been used).
  3. Write booking document to Firestore (`booking_channel: "website"`).
* **Frontend Integration Tasks**:
  1. Refactor `bookingUI.js` checkout flow: request quote from `/bookings/quote`, display signed quote, and pass signed parameters to `POST /bookings`.
* **Test & Validation Scenarios**:
  * E2E checkout test: valid quote creates booking. Tampered quote or replayed signature returns HTTP 400.

---

## Phase 4: Rider Activity History & Feedback (End-to-End)
**Goal**: Securely query rider history and process completed ride star ratings.

### 🏃 Sprint 4.1: Activity History Log
* **Backend Tasks**:
  1. Implement `GET /api/v1/me/bookings` with customer UID filtering and pagination.
* **Frontend Integration Tasks**:
  1. Refactor `activityUI.js` to load trip history via API instead of direct Firestore collection queries.
* **Test & Validation Scenarios**:
  * Verify riders can only view their own past bookings sorted chronologically.

### 🏃 Sprint 4.2: Booking Feedback Submissions
* **Backend Tasks**:
  1. Implement `POST /api/v1/me/bookings/{booking_id}/feedback`.
  2. Verify booking ownership, status == `'completed'`, and prevent duplicate review submissions.
* **Frontend Integration Tasks**:
  1. Refactor feedback rating modal in `activityUI.js` to submit via API.
* **Test & Validation Scenarios**:
  * Verify submitting ratings on active/cancelled rides returns HTTP 400; user cannot review another rider's trip (403).

---

## Phase 5: Admin Dispatch Operations (End-to-End)
**Goal**: Execute atomic driver allocations, geocoded approvals, and ride state transitions.

### 🏃 Sprint 5.1: Real-Time Admin Dashboard Feed Setup
* **Frontend Tasks**:
  1. Retain Firebase SDK `onSnapshot` listener on `/bookings` in `adminUI.js` for real-time dashboard updates (governed by admin read rules in Phase 8).
* **Test & Validation Scenarios**:
  * Confirm dashboard table updates automatically when backend commits booking status changes.

### 🏃 Sprint 5.2: Atomic Allocation, Approval & Fare Recalculation
* **Backend Tasks**:
  1. Implement `POST /api/v1/admin/bookings/{booking_id}/approve`.
  2. Use Firestore Transactions to:
     * Check booking eligibility.
     * Verify driver & vehicle availability.
     * Recalculate OSRM route & fare if custom `pickup_coords`/`drop_coords` are overridden by admin.
     * Assign driver/vehicle and set status to `"confirmed"`.
* **Frontend Integration Tasks**:
  1. Refactor `adminUI.js` approval modal to call approval endpoint.
* **Test & Validation Scenarios**:
  * Test driver double-allocation race condition in parallel requests (transaction prevents double booking). Verify fare recalculation when coordinates change.

### 🏃 Sprint 5.3: Ride Lifecycle Transitions
* **Backend Tasks**:
  1. Implement `/reject`, `/start`, and `/complete` transition routes under `/api/v1/admin/bookings/{booking_id}/`.
  2. Enforce state machine rules (e.g. `/start` requires pickup time reached; `/complete` requires active state).
* **Frontend Integration Tasks**:
  1. Refactor action buttons in `adminUI.js` to invoke transition endpoints.
* **Test & Validation Scenarios**:
  * Verify valid state transitions and ensure illegal transitions (e.g. completing a pending ride) return HTTP 400.

---

## Phase 6: Fleet & Driver Registry Management (End-to-End)
**Goal**: Secure vehicle/driver registry management and optimize media uploads.

### 🏃 Sprint 6.1: Fleet Registry Management
* **Backend & Frontend Tasks**:
  1. Implement CRUD under `/api/v1/admin/fleet`.
  2. Perform bidirectional link updates (linking driver to vehicle automatically updates driver document reference).
  3. Refactor fleet management tab in `adminUI.js`.
* **Test & Validation Scenarios**:
  * Test vehicle creation and driver assignment sync in Firestore.

### 🏃 Sprint 6.2: Driver Registry Management
* **Backend & Frontend Tasks**:
  1. Implement CRUD under `/api/v1/admin/drivers`.
  2. Refactor driver registry tab in `adminUI.js`.
* **Test & Validation Scenarios**:
  * Verify driver updates mirror to associated vehicle records.

### 🏃 Sprint 6.3: Presigned Media Upload Service
* **Backend Tasks**:
  1. Implement `POST /api/v1/admin/upload-url` which generates Firebase Storage presigned upload URLs/tokens.
* **Frontend Integration Tasks**:
  1. Update image upload controls in `adminUI.js` to upload directly to Firebase Storage using presigned URL, then attach the resulting asset URL to vehicle/driver payload.
* **Test & Validation Scenarios**:
  * Test file uploads: verify files upload directly to storage bucket and asset URLs save properly without server memory overhead.

---

## Phase 7: Catalog & Settings Admin Control (End-to-End)
**Goal**: Provide secure admin routes for rates, coupons, locations, and flat fare management.

### 🏃 Sprint 7.1: Catalog Admin APIs & UI Integration
* **Backend & Frontend Tasks**:
  1. Implement Admin REST CRUD routes:
     * Pricing Rates: `PUT /api/v1/admin/settings/rates`
     * Offers/Coupons: `/api/v1/admin/offers`
     * Locations: `/api/v1/admin/locations`
     * Flat Fares: `/api/v1/admin/flat-fares`
  2. Refactor settings and rate management panels in `adminUI.js`.
* **Test & Validation Scenarios**:
  * Update pricing parameters and verify immediate effect on next `/bookings/quote` response.

---

## Phase 8: Hardening, Security Rules & Auditing
**Goal**: Completely lock down Firestore client rules against direct writes and sanitize codebase.

### 🏃 Sprint 8.1: Firestore Rules Lockdown
* **Migration Tasks**:
  1. Deploy production Firestore Security Rules:
     ```javascript
     rules_version = '2';
     service cloud.firestore {
       match /databases/{database}/documents {
         
         // Public Catalogs: Anyone can read pricing and location metadata
         match /settings/rates { allow read: if true; allow write: if false; }
         match /locations/{locId} { allow read: if true; allow write: if false; }
         match /flat_fares/{fareId} { allow read: if true; allow write: if false; }
         match /offers/{offerId} { allow read: if true; allow write: if false; }

         // User Profiles: Users read own profile; Admins can read all profiles
         match /users/{userId} {
           allow read: if request.auth != null && (request.auth.uid == userId || request.auth.token.admin == true);
           allow write: if false; // BACKEND ONLY
         }

         // Bookings: Customers read own rides; Admins read all rides
         match /bookings/{bookingId} {
           allow read: if request.auth != null && (resource.data.customer_id == request.auth.uid || request.auth.token.admin == true);
           allow write: if false; // BACKEND ONLY
         }

         // Fleet & Drivers: Admins only
         match /vehicles/{vehicleId} {
           allow read: if request.auth != null && request.auth.token.admin == true;
           allow write: if false; // BACKEND ONLY
         }
         match /drivers/{driverId} {
           allow read: if request.auth != null && request.auth.token.admin == true;
           allow write: if false; // BACKEND ONLY
         }

         // Default Lockdown: All direct client writes BLOCKED
         match /{document=**} {
           allow read: if request.auth != null;
           allow write: if false; // ALL MUTATIONS VIA FASTAPI
         }
       }
     }
     ```
* **Test & Validation Scenarios**:
  * Attempt write mutations directly from browser developer console (`db.collection('bookings').add(...)`). Verify all direct write attempts fail with `Permission Denied`.
  * Confirm unauthenticated users can still load rates/locations catalog for initial quote calculations.

### 🏃 Sprint 8.2: Code Cleanup & E2E Verification
* **Migration Tasks**:
  1. Audit application for unused client-side database helper functions.
  2. Verify all API requests correctly append Authorization headers.
* **Test & Validation Scenarios**:
  * Perform full end-to-end sanity walkthrough (Rider quote -> Booking -> Admin Approval -> Driver Assignment -> Trip Start -> Trip Completion -> Rating).
