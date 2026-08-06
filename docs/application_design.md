# 🚖 SethCabs: High-Level Application Design & Architecture Document

This document outlines the high-level system architecture, database design, component interactions, and detailed algorithmic operations of the **SethCabs Web Application**. It serves as a comprehensive technical manuscript for developers, stakeholders, and system auditors.

---

## 1. 🌐 High-Level Architecture Overview

SethCabs is built on a **Hybrid REST-and-Realtime Architecture**. Instead of direct browser-to-database mutations which are insecure, the application decouples read operations from write mutations:
* **Reads**: Frontend screens establish real-time listeners (`onSnapshot`) via the client-side Firebase SDK to stream status and catalogs.
* **Writes**: 100% of data writes, state transitions, and administration changes are routed securely through a central FastAPI backend server.
* **Database & Auth**: Core credentials and RBAC rules are managed via Firebase Authentication and stored in Cloud Firestore.

---

## 2. 📊 C4 Architecture Diagrams

The C4 model helps visualize system boundaries, containers, and code components in progressive levels of detail.

### C4 Level 1: System Context Diagram
This diagram shows the system boundaries and actor interactions.

```mermaid
graph TB
    %% Styling
    classDef actor fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#fff;
    classDef system fill:#0F172A,stroke:#38BDF8,stroke-width:2px,color:#fff;
    classDef external fill:#1C1917,stroke:#A8A29E,stroke-width:1.5px,stroke-dasharray: 5 5,color:#A8A29E;

    Rider([Rider / Customer]):::actor
    Admin([Administrator]):::actor

    SethCabsApp["SethCabs Web App
    (Static Glassmorphic UI)"]:::system
    
    FastAPI["FastAPI Backend Server
    (Secure Business Operations API)"]:::system

    Firebase["Firebase Services
    (Auth & Firestore Database)"]:::system
    
    EmailGateway["Email Gateway
    (EmailJS / SMTP)"]:::external
    
    WAGateway["WhatsApp Gateway
    (CallMeBot)"]:::external

    %% Relations
    Rider -->|"Books cabs, reviews history"| SethCabsApp
    Admin -->|"Manages roster & approves bookings"| SethCabsApp
    
    SethCabsApp -->|"Direct reads / dynamic updates"| Firebase
    SethCabsApp -->|"REST API mutations & estimation requests"| FastAPI
    FastAPI <-->|"Firestore Admin API writes & claim audits"| Firebase
    
    SethCabsApp -->|"Triggers transactional alerts"| EmailGateway
    SethCabsApp -->|"Triggers real-time alerts"| WAGateway
```

---

### C4 Level 2: Container Diagram
This diagram drills down into the core containers that run inside the browser and the backend server.

```mermaid
graph TB
    %% Styling
    classDef container fill:#0F172A,stroke:#38BDF8,stroke-width:2px,color:#fff;
    classDef cloud fill:#172554,stroke:#3B82F6,stroke-width:2px,color:#fff;
    classDef external fill:#1C1917,stroke:#A8A29E,stroke-width:1.5px,color:#A8A29E;

    subgraph BrowserContainer ["Web Browser (Client Device)"]
        UI["UI Layer (HTML / CSS)"]:::container
        AuthMod["Auth UI & SDK Handler"]:::container
        BookingMod["Booking UI Wizard"]:::container
        AdminMod["Admin UI Panels"]:::container
    end

    subgraph BackendContainer ["FastAPI Backend (Uvicorn)"]
        RouterAuth["Auth & JWT Dependency Engine"]:::container
        RouterBooking["Booking & Quote Calculator"]:::container
        RouterAdmin["Admin & Catalog CRUD Manager"]:::container
    end

    Firestore[("Cloud Firestore
    NoSQL Database")]:::cloud
    
    FBAuth["Firebase Authentication
    Secure Sessions"]:::cloud

    %% Connectors
    UI --> AuthMod
    UI --> BookingMod
    UI --> AdminMod
    
    AuthMod -->|"Authenticates"| FBAuth
    BookingMod -->|"POST /quotes/estimate & POST /bookings"| RouterBooking
    AdminMod -->|"PATCH /admin/bookings & CRUD requests"| RouterAdmin
    
    RouterAuth <-->|"Decodes & validates tokens"| FBAuth
    RouterBooking <-->|"Transactions & writes"| Firestore
    RouterAdmin <-->|"Roster association writes"| Firestore
```

---

### C4 Level 3: Component Diagram for Backend Booking Container
This diagram illustrates the code structure inside the **FastAPI Backend Booking Component**.

```mermaid
graph TD
    %% Styling
    classDef route fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#fff;
    classDef core fill:#0F172A,stroke:#38BDF8,stroke-width:2px,color:#fff;
    classDef db fill:#172554,stroke:#3B82F6,stroke-width:1.5px,color:#fff;

    EndpointBooking["bookings.py
    (POST /bookings, POST /quotes/estimate)"]:::route
    
    EndpointAdmin["admin.py
    (PATCH /admin/bookings, POST /sync-schemas)"]:::route
    
    AuthDep["auth.py
    (get_current_user, require_admin)"]:::core
    
    FirebaseCore["firebase.py
    (Admin SDK Initialization)"]:::core
    
    FirestoreDB[("Firestore DB Interface")]:::db

    %% Dependencies
    EndpointBooking -->|"Validates rider identity"| AuthDep
    EndpointAdmin -->|"Enforces admin RBAC claims"| AuthDep
    AuthDep -->|"Reads claims"| FirebaseCore
    EndpointBooking -->|"Fare computations & updates"| FirestoreDB
    EndpointAdmin -->|"Atomic transitions"| FirestoreDB
    FirebaseCore -->|"Connects"| FirestoreDB
```

---

## 3. 🔄 System Process Flowcharts

### Customer Booking & Fare Guarantee Lifecycle

```mermaid
flowchart TD
    Start([Rider accesses booking screen]) --> Step1[Step 1: Input pickup, drop, date & time]
    Step1 --> VerifyLead{Is pickup datetime > 2 hours from now?}
    
    VerifyLead -- "No" --> RejectTime[Show lead time warning & block progress]
    RejectTime --> Step1
    
    VerifyLead -- "Yes" --> RequestQuote[POST /api/v1/quotes/estimate]
    RequestQuote --> BackendCalc[Backend: query distance, active rates settings & check availability]
    
    BackendCalc --> CheckInv{Are vehicle tiers sold out?}
    CheckInv -- "Yes" --> ShowSoldOut[Flag tier card as Sold Out in UI]
    CheckInv -- "No" --> SignQuote[Backend: Generate HMAC-SHA256 Quote Signature]
    
    SignQuote --> ReturnQuote[Return estimates and signature hex string]
    ReturnQuote --> DisplayFares[Step 2: Show fares in card list & allow selection]
    DisplayFares --> SelectCar[Select class card & advance to Review Step 3]
    
    SelectCar --> ReviewScreen[Rider clicks Book Cab]
    ReviewScreen --> CreateBooking[POST /api/v1/bookings]
    
    CreateBooking --> VerifySig{Is signature valid & expires_at > current time?}
    VerifySig -- "No" --> RejectBooking[Return HTTP 400 Bad Request]
    VerifySig -- "Yes" --> CheckReplay{Has quote_id already been booked?}
    
    CheckReplay -- "Yes" --> RejectBooking
    CheckReplay -- "No" --> RecordNonce[Write quote_id to database to prevent replay]
    RecordNonce --> CommitBooking[(Commit booking record to Firestore database)]
    
    CommitBooking --> SuccessScreen[Show Success screen & returns booking ID]
```

---

## 4. 🗄️ Database Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    users ||--o{ bookings : "submits"
    drivers |o--o| vehicles : "assigned bidirectionally (assigned_vehicle_id / assigned_driver_id)"
    bookings }o--o| drivers : "allocated on approval (driver_assignment.driver_id)"
    bookings }o--o| vehicles : "allocated on approval (driver_assignment.vehicle_id)"
    bookings }o--o| offers : "applies coupon (fare_details.promo_code)"
    bookings }o--o| rates_history : "calculated under configuration (fare_details.rates_version_id)"
    settings_rates }o--|| rates_history : "tracks active version (active_version_id)"

    users {
        string uid PK "Document ID"
        string name
        string email
        string phone
        string role
        timestamp creation_ts
        timestamp updated_ts
    }
    
    bookings {
        string booking_id PK "Document ID"
        string customer_id FK "References users.uid"
        string status
        string payment_status
        object trip_details
        object fare_details "Contains promo_code FK and rates_version_id FK"
        object driver_assignment FK "Holds reference fields to drivers & vehicles"
        object feedback
        string rejection_reason
        timestamp creation_ts
        timestamp updated_ts
    }
    
    vehicles {
        string id PK "Document ID (standardized plate)"
        string model
        string plate_number
        string tier
        string status
        string assigned_driver_id FK "References drivers.id"
        timestamp creation_ts
    }
    
    drivers {
        string id PK "Document ID (standardized phone)"
        string name
        string phone
        string license_number
        string status
        string assigned_vehicle_id FK "References vehicles.id"
        timestamp creation_ts
    }
    
    offers {
        string id PK "Document ID (promo code string)"
        string code
        string discount_type
        number discount_value
        number min_fare_threshold
        string status
        timestamp creation_ts
    }
    
    settings_rates {
        string id PK "Document ID ('rates')"
        object local
        object rental
        object intercity
        object global
        string active_version_id FK "References rates_history.id"
        timestamp updated_ts
    }
    
    rates_history {
        string id PK "Document ID (version string)"
        object rates "Map containing parameters"
        timestamp creation_ts
    }
```

---

## 5. 📖 High-Level Component Explanations

Here is a straightforward explanation of each file in the codebase and what it is responsible for.

### 🏠 Landing Page & UI
* **[index.html](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/index.html)**: Homepage layout containing structural anchors, package grids, promo sliders, and CTAs.
* **[app.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/app.js)**: Listens for authentication changes, manages active sessions, and determines navigation links.
* **[styles.css](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/styles.css)**: Core design system specifying glassmorphism filters, backgrounds, custom scrollbars, and buttons.

### 🚖 Rider Modules
* **[modules/booking/booking.html](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/booking.html)**: Multi-step checkout UI wizard (Step 1: Route details, Step 2: Car Tier Selection, Step 3: Checkout Review).
* **[modules/booking/bookingUI.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/bookingUI.js)**: Controller for checkout actions, coordinate validations, Nominatim search inputs, and page indicators.
* **[modules/booking/bookingService.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/bookingService.js)**: Frontend API client managing fare checkouts, promo validations, availability requests, and completed feedback uploads.
* **[modules/booking/activityUI.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/activityUI.js)**: Feeds personal booking lists to riders and renders Leaflet static maps of past routes.

### 🔐 Administrative Modules
* **[modules/admin/admin.html](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/admin/admin.html)**: Backoffice console grid layout. Handles approvals, vehicle catalog registry, coupons, flat fares, and driver rosters.
* **[modules/admin/adminUI.js](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/admin/adminUI.js)**: Controller calling backend admin operations via authenticated API requests.

---

## 6. 🛠️ Detailed Component Explanation

This section acts as a technical manuscript explaining the exact algorithms, code structures, and database interactions running in the active codebase.

### 6.1 Authentication Module (RBAC & Session Checks)
Access guard validations are governed using Firebase Auth ID tokens:
1. When a client authenticates or changes roles, they call `user.getIdToken(true)` to force token claims updating.
2. The client transmits the resulting JWT string in the HTTP request as an `Authorization: Bearer <JWT>` header.
3. The backend (`backend/app/core/auth.py`) decodes the token:
   * Decodes the signature using Google's public keys.
   * Audits expiry parameters.
   * Asserts the existence of custom claims:
     ```python
     # Enforces admin-only verification
     if not decoded_token.get("admin"):
         raise HTTPException(status_code=403, detail="Admin permissions required.")
     ```

---

### 6.2 Fare Calculation Engine (Algorithmic Logic)
Fares are calculated inside [`backend/app/routers/bookings.py`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/backend/app/routers/bookings.py#L73-L154):

#### Category A: Hourly Rental Packages
Fares are governed by set base package limits (e.g., 6 hours / 60 km):
$$\text{Rental Fare} = \text{Base Cost} + \max(0, d - d_{\text{inc}}) \times R_{\text{km}} + \max(0, h - h_{\text{inc}}) \times R_{\text{hr}} + \text{Night Charge} - \text{Discount}$$
* *Parameters*: $d$ = distance in km, $d_{\text{inc}}$ = included km, $h$ = actual hours, $h_{\text{inc}}$ = included hours, $R_{\text{km}}$ = extra km rate, $R_{\text{hr}}$ = extra hour rate.

#### Category B: Intercity Outstation (Round-Trip pricing)
Intercity trips are double-distance billed (round-trip doubling) and require minimum travel mileage thresholds (250 km per day):
$$\text{Outstation Distance} = \max\left(2 \times d, 250 \times \text{Days}\right)$$
$$\text{Outstation Fare} = \text{Outstation Distance} \times R_{\text{km}} + \left(\text{Driver Allowance} \times \text{Days}\right) + \left(\text{Night Halt} \times (\text{Days} - 1)\right)$$

#### Category C: Fallback Local Rides
Standard local rides are calculated dynamically:
$$\text{Local Fare} = \text{Base Cost} + \max(0, d - 10) \times R_{\text{km}} + \text{Night Charge}$$

#### Night Charge Condition
A night-charge multiplier is added if the pickup time string ($t$) falls within the night time window:
$$t \ge \text{night charge start (23:59)} \quad \text{or} \quad t \le \text{night charge end (06:00)}$$

---

### 6.3 Anti-Replay Signed Quotes
To prevent clients from submitting tampered fares (e.g. editing HTML values during checkout), quotes are cryptographically signed on the server:
1. **Hashing (SHA-256)**: The server constructs a serialized message string:
   $$\text{Message} = \text{quote ID} \mid \text{customer ID} \mid \text{vehicle tier} \mid \text{base fare} \mid \text{estimated fare} \mid \text{expires at}$$
2. **Signature Generating**: The server hashes this message using a secret key:
   $$\text{Signature} = \text{HMAC-SHA256}(\text{HMAC-QUOTE-SECRET}, \text{Message})$$
3. **Nonce Check (Anti-Replay)**: When a booking is submitted via `POST /bookings`, the server checks:
   * If current time is less than `expires_at`.
   * If the signature matches the parameters.
   * If `quote_id` has already been logged in the `bookings` collection. If it exists, the checkout is rejected to prevent replaying a signed quote multiple times.

---

### 6.4 Fleet & Driver Association (Atomic Bidirectional Updates)
When an administrator assigns a driver to a vehicle (or vehicle to a driver), the backend executes successive updates atomically to maintain relationship consistency:
* When Vehicle $V_1$ is linked to Driver $D_1$:
  1. Read current driver references. If $V_1$ was previously linked to $D_2$, set $D_2$'s reference (`assigned_vehicle_id`) to `null`.
  2. If $D_1$ was previously linked to $V_2$, set $V_2$'s reference (`assigned_driver_id`) to `null`.
  3. Write $V_1$'s `assigned_driver_id` as $D_1$ and $D_1$'s `assigned_vehicle_id` as $V_1$.

---

### 6.5 Database API Route Operations

#### 1. POST /api/v1/bookings
* *Process*: Accepts booking requests containing trip details and quote signatures.
* *Query steps*:
  1. Retrieve `quote_id` from payload and verify if a document with this ID already exists.
  2. Verify quote signature matches HMAC computation.
  3. Write document to `/bookings/{booking_id}` using `SERVER_TIMESTAMP`.

#### 2. PUT /api/v1/admin/settings/rates
* *Process*: Re-configures system pricing matrix tariffs and records history logs.
* *Query steps*:
  1. Generate version ID: `R-<timestamp>`.
  2. Write active rates copy to `/rates_history/R-<timestamp>`.
  3. Update active rate variables inside `/settings/rates` document, storing the version ID pointer.

#### 3. DELETE /api/v1/admin/vehicles/{id} or drivers/{id}
* *Process*: Deletes the registered vehicle or driver from inventory catalog.
* *Query steps*:
  1. Fetch document metadata.
  2. Clear references from any linked entities (unlink driver/car).
  3. Delete document from collection path `/vehicles/{id}` or `/drivers/{id}`.

#### 4. DELETE /api/v1/admin/db/cleanup
* *Process*: Deletes selected documents by ID or cleans up the entire collection under a safety verification flag.
* *Query steps*:
  1. If `document_ids` is provided, initialize a Firestore batch and schedule deletion of specified document paths. Commit batch changes (max 500 documents per batch).
  2. If `document_ids` is not provided (or empty), check if `confirm_delete_all` is `True`. If `False`, reject request with HTTP 400.
  3. If `confirm_delete_all` is `True`, query the collection stream, queue references to a Firestore delete batch, and commit in 500-operation intervals.


---

## 7. ⚙️ Configuration Management

This section lists all configurations used across the frontend and backend, detailing their purpose, variables, and where they reside in the directory structure.

### 7.1 Client-Side Firebase Configuration
* **Location**: [`modules/shared/firebase.js`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/shared/firebase.js)
* **Configuration Object**:
  ```javascript
  const firebaseConfig = {
      apiKey: "AIzaSyCDaeBao1YQyN-yycmvthxu-eYJatexX-o",
      authDomain: "ishancabproject.firebaseapp.com",
      projectId: "ishancabproject",
      storageBucket: "ishancabproject.firebasestorage.app",
      messagingSenderId: "127785774256",
      appId: "1:127785774256:web:d7629170ddee8e876edf75"
  };
  ```
* **Variables Description**:
  * `apiKey`: Secret key used for authenticating frontend SDK client requests.
  * `authDomain`: Domain for hosting Firebase Auth user sign-in handlers.
  * `projectId`: Firebase console project identifier.
  * `storageBucket`: Storage bucket URI for asset management.
  * `messagingSenderId`: Messaging credentials identifier.
  * `appId`: Unique application registration identifier.

---

### 7.2 Backend Environment Configuration
* **Location**: `.env` (located in backend root directory `backend/.env`)
* **Environment Class Schema**: Loaded into `Settings` configuration model in [`backend/app/core/config.py`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/backend/app/core/config.py)
* **Configuration Variables Template**:
  ```env
  PROJECT_NAME="SethCabs Backend"
  CORS_ORIGINS="http://localhost:5500,http://127.0.0.1:5500"
  HMAC_QUOTE_SECRET="temporary_dev_hmac_quote_secret_key_12345"
  FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/service-account.json"
  ```
* **Variables Description**:
  * `PROJECT_NAME`: Title of the backend server.
  * `CORS_ORIGINS`: Allowed hostnames list permitting browser fetch requests.
  * `HMAC_QUOTE_SECRET`: Secret hashing key for cryptographically signing booking quotes.
  * `FIREBASE_SERVICE_ACCOUNT_PATH`: File path to the JSON key of your Firebase Service Account (optional if running on GCP with Application Default Credentials).

---

### 7.3 External APIs & Services Configuration
The application integrates several third-party maps and communication services configured dynamically:

#### 1. OpenStreetMap Tile Server
* **Location**: Configured directly in `tileLayer` initializers inside:
  * [`modules/booking/bookingUI.js`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/bookingUI.js#L343-L346)
  * [`modules/booking/activityUI.js`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/activityUI.js#L459-L461)
  * [`modules/admin/adminUI.js`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/admin/adminUI.js#L1142)
* **Configuration URL**: `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
* **Purpose**: Fetches static background map graphic tiles.

#### 2. Nominatim Geocoder API
* **Location**: Integrated inside search handlers in `bookingUI.js` and `adminUI.js`.
* **Configuration URL**: `https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1`
* **Purpose**: Translates textual address entries into coordinate pins (latitude & longitude) dynamically.

#### 3. OSRM Routing Engine API
* **Location**: Initialized in coordinate preview functions in `bookingUI.js`.
* **Configuration URL**: `https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson`
* **Purpose**: Calculates driving routes, coordinates path vectors, and tracks total distance parameters.

#### 4. WhatsApp Click-to-Chat Dispatch Service
* **Location**: Configured inside `compileWhatsAppLink()` inside [`modules/booking/bookingService.js`](file:///Users/ishanmukherjee/AI_Learning/Cab-Website-Build/cab-website-cloud/cab-website-cloud/modules/booking/bookingService.js#L189-L206)
* **Configuration Phone Number**: `918981538038` (Support desk/Dispatch controller contact phone)
* **Configuration URL Schema**: `https://wa.me/{phone_number}?text={encoded_message}`
* **Purpose**: Redirects riders on checkout completion to open a WhatsApp message containing full booking details pre-compiled.

---

> [!WARNING]
> **Credential Security**: Never commit the backend `.env` file or Firebase Service Account JSON credentials files into public Git repositories. Ensure these files are added to your project's `.gitignore` file.

