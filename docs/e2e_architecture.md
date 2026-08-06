# 🚖 SethCabs: End-to-End (E2E) Architecture Document

This document provides a comprehensive end-to-end technical overview of the **SethCabs Web Application** architecture. It describes the hybrid REST-and-realtime structure, outlines user interaction sequence flows for different modules, documents database schemas, and models document relationships.

---

## 1. 🌐 High-Level System Architecture

SethCabs is built on a **Hybrid REST-and-Realtime Architecture**. 
* **Reads (Real-Time Streams)**: Web clients (both Riders and Administrators) connect directly to Cloud Firestore using the client-side Firebase SDK's `onSnapshot` listeners to receive instantaneous UI updates.
* **Writes (Secure Mutations)**: 100% of data writes (quotes, bookings, ride approvals, status updates, registry edits, feedback, and catalog settings) are routed exclusively through the FastAPI backend server. Direct client write mutations are completely blocked.
* **Security & Auth**: Secure role-based access control (RBAC) is governed by Firebase Authentication custom claims (`{"admin": true}`) checked in backend headers. Fare details are protected against tampering using HMAC-SHA256 signatures generated and verified on the server.

```mermaid
graph TB
    %% Styling
    classDef actor fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#fff;
    classDef system fill:#0F172A,stroke:#38BDF8,stroke-width:2px,color:#fff;
    classDef cloud fill:#172554,stroke:#3B82F6,stroke-width:2px,color:#fff;
    classDef external fill:#1C1917,stroke:#A8A29E,stroke-width:1.5px,color:#A8A29E;

    Rider([Rider / Customer]):::actor
    Admin([Fleet Administrator]):::actor

    Browser["Web UI Layer (HTML, CSS, JS)
    Renders Premium Glassmorphic Cards"]:::system
    
    FastAPI["FastAPI Backend Server
    (Secure REST API Mutations & Quotes)"]:::system

    Firebase["Firebase Authentication
    Secure Sessions & Users Catalog"]:::cloud
    
    Firestore[("Cloud Firestore DB
    Real-Time Data Streaming")]:::cloud
    
    OSRM["OSRM & Nominatim APIs
    Routing Geometry & Geocoding"]:::external

    %% Interconnections
    Rider -->|"Books cab, views history"| Browser
    Admin -->|"Manages roster & approves bookings"| Browser
    
    Browser <-->|"Authenticates session & obtains JWT"| Firebase
    Browser -->|"Direct Real-time snapshot read streams"| Firestore
    Browser -->|"POST writes & estimation requests"| FastAPI
    FastAPI <-->|"Firestore Admin SDK writes & claims"| Firestore
    FastAPI <-->|"Validates auth tokens"| Firebase
    FastAPI -->|"Requests geocodes & route coordinates"| OSRM
```

---

## 2. 🔄 Module Interaction Flows (Stick / Sequence Diagrams)

These sequence diagrams depict step-by-step system interactions across different modules.

### A. Rider Authentication & Session Initialization
This flow manages secure access checks during client load, separating standard riders from dashboard administrators.

```mermaid
sequenceDiagram
    autonumber
    actor Rider as Rider / User
    participant Browser as Web Browser (app.js)
    participant FBAuth as Firebase Auth
    participant FastAPI as FastAPI (/me/profile)
    participant Firestore as Firestore (/users)
    actor Admin as Administrator

    Rider->>Browser: Loads landing page (index.html)
    Browser->>FBAuth: Check current authentication state (onAuthStateChanged)
    
    alt User is Logged In
        FBAuth-->>Browser: Returns user object (UID, Email)
        Browser->>Browser: Requests JWT token claim refresh (getIdToken(true))
        Browser->>FastAPI: GET /api/v1/me/profile (with Bearer Token)
        FastAPI->>Firestore: Fetches user document from /users
        Firestore-->>FastAPI: Returns user document
        FastAPI-->>Browser: Returns profile JSON (role)
        
        alt User Role is "admin"
            Browser->>Browser: Hides Booking buttons & reveals "Admin Panel" CTA
            Admin->>Browser: Clicks "Admin Panel"
            Browser->>Browser: Redirects to modules/admin/admin.html
        else User Role is "rider"
            Browser->>Browser: Reveals "Book Cab" & "Activity" CTA buttons
        end
    else User is Guest (Logged Out)
        Browser->>Browser: Directs user to authenticate if they click Book Cab
    end
```

---

### B. Customer Booking & Custom Location Map Flow
This flow represents the 3-step customer checkout loop. It coordinates Leaflet mapping, Nominatim searching, OSRM route calculations, overbooking checks, promo verification, and database logging.

```mermaid
sequenceDiagram
    autonumber
    actor Rider as Rider / User
    participant Page as Booking UI (booking.html)
    participant Controller as Controller (bookingUI.js)
    participant Maps as Leaflet & Nominatim APIs
    participant FastAPI as FastAPI Backend (/quotes/estimate)
    participant Firestore as Cloud Firestore

    Rider->>Page: Enters Route Details (Step 1)
    
    alt Custom Location selected
        Controller->>Page: Displays Leaflet map picker
        Rider->>Page: Searches address or drags Pickup/Drop markers
        Page->>Maps: Request Nominatim Reverse-Geocode
        Maps-->>Page: Return formatted address string
    end
    
    Rider->>Page: Submits Step 1 (pickup datetime, locations)
    Controller->>Controller: Enforces 2-hour scheduling lead time verification
    
    Controller->>FastAPI: POST /api/v1/quotes/estimate (pickup/drop locations, times, coordinates)
    
    alt Standard Ride Category
        FastAPI->>Maps: Query OSRM Driving distance & geometry
        Maps-->>FastAPI: Returns route polyline array & total kilometers
    else Rental Category
        FastAPI->>FastAPI: Bypasses Drop parameters & OSRM requests
    end
    
    FastAPI->>Firestore: Fetch active rates and check overbookings
    Firestore-->>FastAPI: Returns rate configurations & current booking counts
    FastAPI->>FastAPI: Checks overbooking ratios (compares active booking counts vs. vehicle roster size)
    
    alt Fleet Tier is Sold Out
        FastAPI-->>Controller: Returns Sold Out tier status
        Controller-->>Page: Displays "Sold Out" state and locks tier card selection
    else Fleet Tier is Available
        FastAPI->>FastAPI: Computes estimated fare and signs parameters with HMAC-SHA256
        FastAPI-->>Controller: Returns calculated fares & cryptographically signed quote
        Controller-->>Page: Displays calculated fares for Compact, Premium, SUV, and MUV cards
    end

    Rider->>Page: Selects class card & advances to Review (Step 3)
    
    opt Enters Promo Discount Code
        Controller->>FastAPI: POST /api/v1/offers/validate (code, base_fare)
        FastAPI->>Firestore: Query coupon details from /offers collection
        Firestore-->>FastAPI: Returns coupon configuration
        FastAPI->>FastAPI: Validates coupon status & returns discount value
        FastAPI-->>Controller: Returns calculated discount
        Controller->>Controller: Updates fare breakdown UI with applied discount
    end

    Rider->>Page: Clicks "Confirm & Book"
    Controller->>FastAPI: POST /api/v1/bookings (trip_details, fare_details, quote_signature, quote_id)
    Note over FastAPI: Verifies quote HMAC signature, expiration time, and checks signature anti-replay nonce
    FastAPI->>Firestore: Writes new record in /bookings collection (booking_channel: "website")
    Firestore-->>FastAPI: Document logged, returns Booking ID (BK-YYYYMMDD-XXXX)
    FastAPI-->>Controller: Returns Booking ID & success status
    Controller-->>Page: Triggers success banner
    Page-->>Rider: Shows success screen & schedules auto-redirect to home
```

---

### C. Admin Ride Approval & Roster Allocation
This sequence details how administrators assign available drivers/vehicles to requested rides, checking for scheduling conflicts in real-time.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Fleet Administrator
    participant Panel as Admin Panel (admin.html)
    participant Logic as Admin Controller (adminUI.js)
    participant FastAPI as FastAPI Backend (/admin/bookings/{id})
    participant Firestore as Cloud Firestore

    Note over Logic: Snapshot listeners are active for bookings, vehicles, and drivers
    Firestore-->>Logic: Stream database updates dynamically
    Logic->>Panel: Populate list tables and update dashboard KPI metrics counters

    Admin->>Panel: Accesses "Requested" booking list & clicks "Accept Ride"
    Logic->>Logic: Compiles list of active drivers and vehicles from snapshot
    Logic->>Panel: Populate Dropdown Roster grouped by Tier
    Note over Panel: Options holding busy drivers/cars are flagged as "[Busy - On Ride]"
    
    Admin->>Panel: Selects dynamic driver-car option & clicks "Confirm Allocation"
    
    Logic->>FastAPI: PATCH /api/v1/admin/bookings/{id} (status: "confirmed", driver_assignment: {...})
    
    FastAPI->>Firestore: Execute Firestore transaction to verify driver/vehicle allocation conflicts
    Firestore-->>FastAPI: Transaction status check (no double bookings)
    
    alt Selected Roster Entry is Confirmed/Active on another ride
        FastAPI-->>Logic: Return HTTP 400 (Conflict error)
        Logic->>Panel: Blocks submit action & triggers warning alert block
    else Selected Roster Entry is Free
        FastAPI->>Firestore: Updates /bookings/{id} details atomically
        Firestore-->>FastAPI: Commit success
        FastAPI-->>Logic: Returns HTTP 200 (Success)
        Logic->>Panel: Closes modal and updates lists in real-time
    end
```

---

### D. Driver & Vehicle Registry Association Flow
This details the bidirectional reference mapping mechanism when updating or registering operators.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Fleet Administrator
    participant Panel as Admin Panel
    participant Logic as Admin Controller (adminUI.js)
    participant FastAPI as FastAPI Backend (/admin/vehicles or /admin/drivers)
    participant Firestore as Cloud Firestore

    Admin->>Panel: Fills Vehicle Form (Plate: WB02A1111) & assigns Driver (Phone: 918981538038)
    Admin->>Panel: Clicks "Save Vehicle"
    Logic->>FastAPI: POST /api/v1/admin/vehicles (doc_id: "WB02A1111", assigned_driver_id: "918981538038")
    
    FastAPI->>Firestore: Fetch previous associations and execute atomic updates
    Firestore-->>FastAPI: Previous links fetched
    
    opt Vehicle was previously linked to another driver
        FastAPI->>Firestore: Updates previous driver document setting assigned_vehicle_id: null
    end
    
    FastAPI->>Firestore: Updates assigned driver document setting assigned_vehicle_id: "WB02A1111"
    
    opt Driver was previously linked to another vehicle
        FastAPI->>Firestore: Updates previous vehicle document setting assigned_driver_id: null
    end
    
    FastAPI->>Firestore: Writes vehicle document (doc_id: "WB02A1111", assigned_driver_id: "918981538038")
    Firestore-->>FastAPI: Database transaction committed
    
    FastAPI-->>Logic: Returns success status
    Logic->>Panel: Clears forms, repopulates dropdown selectors, and updates tables via snapshot
```

---

## 3. 🗄️ Database Schemas (Cloud Firestore Collections)

Firestore collections are structured as NoSQL JSON documents. Relationships between collections are maintained by storing reference IDs as strings.

### 1. Users Collection (`/users/{uid}`)
Contains customer profile details and roles used for authentication boundaries.
*   **Document ID**: Firebase Auth User UID.

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `uid` | `string` | Unique identifier generated by Firebase Auth. |
| `name` | `string` | User's full name. |
| `email` | `string` | User's email address. |
| `phone` | `string` | Contact phone number. |
| `role` | `string` | User permission role (`"rider"` or `"admin"`). |
| `creation_ts` | `Timestamp` | Record creation date and time. |
| `updated_ts` | `Timestamp` | Last modification timestamp. |

---

### 2. Bookings Collection (`/bookings/{booking_id}`)
Stores transactional ride requests, parameters, fare details, and driver/car allocations.
*   **Document ID**: Readable date-based unique string (e.g. `BK-20260604-9844`).

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `booking_id` | `string` | Unique booking identification number. |
| `customer_id` | `string` | Reference ID matching `/users.uid`. |
| `customer_name` | `string` | User name snapshot copy for fast rendering. |
| `customer_phone` | `string` | User phone snapshot copy. |
| `booking_channel` | `string` | Source of booking (`"website"`, `"admin"`). |
| `status` | `string` | State lifecycle: `"pending_approval"`, `"confirmed"`, `"active"`, `"completed"`, `"rejected"`, `"cancelled"`. |
| `payment_status` | `string` | Ledger status: `"pending"`, `"paid"`. |
| `creation_ts` | `Timestamp` | Booking checkout timestamp. |
| `updated_ts` | `Timestamp` | Last modification timestamp. |
| `trip_details` | `Map (Object)` | Holds trip parameters (detailed below). |
| `fare_details` | `Map (Object)` | Holds fare estimations and discounts (detailed below). |
| `driver_assignment` | `Map` or `null` | Allocated driver and vehicle details (detailed below). |
| `feedback` | `Map` or `null` | Rider star rating and comments (detailed below). |
| `rejection_reason` | `string` or `null` | Logged explanation when status is `"rejected"`. |

#### `trip_details` Map Structure:
*   `ride_type`: `string` (`"local"`, `"outstation"`, `"rental"`).
*   `pickup_location`: `string` (Address title).
*   `drop_location`: `string` or `null` (Destination address title).
*   `pickup_date`: `string` (`YYYY-MM-DD`).
*   `pickup_time`: `string` (`HH:MM` in 24-hr format).
*   `outstation_days`: `number` or `null` (Duration for outstation category).
*   `rental_hours`: `number` or `null` (Duration for hourly rentals).
*   `pickup_coords`: `Array [lat, lng]` (Coordinates).
*   `drop_coords`: `Array [lat, lng]` or `null` (Coordinates).
*   `route_polyline`: `string` or `null` (JSON stringified array of coordinates).

#### `fare_details` Map Structure:
*   `vehicle_tier`: `string` (`"compact"`, `"premium"`, `"suv"`, `"muv"`).
*   `estimated_km`: `number` (Driving distance).
*   `base_fare`: `number` (Initial fare configuration mapping).
*   `extra_distance_charge`: `number` (Charges for extra kilometers in local/rental).
*   `waiting_charge`: `number` (Charges for waiting hours).
*   `night_charge`: `number` (Additional night driving charges).
*   `toll_charges`: `number` (Toll gates fees).
*   `parking_charges`: `number` (Parking lot fees).
*   `driver_allowance`: `number` (Operator daily allowance).
*   `discount_amount`: `number` (Discount amount applied).
*   `promo_code`: `string` or `null` (Applied coupon code).
*   `estimated_fare`: `number` (Grand total amount).
*   `rates_version_id`: `string` or `null` (Historical rates reference).
*   `quote_signature`: `string` (Cryptographic verification signature).

#### `driver_assignment` Map Structure (or `null`):
*   `driver_id`: `string` (Allocated driver phone).
*   `driver_name`: `string` (Allocated driver name).
*   `vehicle_id`: `string` (Allocated vehicle plate number).
*   `vehicle_model`: `string` (Allocated vehicle model name).
*   `assigned_at`: `string` (Timestamp of allocation).

#### `feedback` Map Structure (or `null`):
*   `rating`: `number` (Integer range: 1 to 5).
*   `comments`: `string` (Feedback review comments).
*   `submitted_ts`: `Timestamp` (Time when feedback was submitted).

---

### 3. Vehicles Collection (`/vehicles/{vehicle_id}`)
Maintains the operator fleet inventory.
*   **Document ID**: Standardized uppercase alphanumeric plate number (e.g. `WB02A1111` for "WB-02-A-1111").

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `model` | `string` | Vehicle model name (e.g., `"Maruti Swift Dzire"`, `"Toyota Innova"`). |
| `plate_number` | `string` | Display license plate string with formatted dashes. |
| `tier` | `string` | Pricing category classification (`"compact"`, `"premium"`, `"suv"`, `"muv"`). |
| `status` | `string` | Maintenance state (`"active"`, `"maintenance"`, `"inactive"`). |
| `assigned_driver_id` | `string` or `null` | Reference ID matching `/drivers.id` (stripped phone). |
| `passengers` | `number` | Seat capacity. |
| `address` | `string` | Primary depot location. |
| `creation_ts` | `Timestamp` | Roster log timestamp. |

---

### 4. Drivers Collection (`/drivers/{driver_id}`)
Holds the operator drivers registry.
*   **Document ID**: Standardized stripped digits-only phone number (e.g. `918981538038`).

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `name` | `string` | Driver operator's full name. |
| `phone` | `string` | Format contact number string (e.g., `"+918981538038"`). |
| `license_number` | `string` | Driver's commercial licensing ID. |
| `status` | `string` | Availability state (`"active"`, `"inactive"`, `"on_trip"`). |
| `assigned_vehicle_id` | `string` or `null` | Reference ID matching `/vehicles.id` (stripped plate). |
| `address` | `string` | Driver local depot assignment. |
| `creation_ts` | `Timestamp` | Registration log timestamp. |

---

### 5. Offers Collection (`/offers/{code}`)
Coupon codes list compiled for customer deductions.
*   **Document ID**: Upper-case promo code title string (e.g., `WELCOME100`).

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `code` | `string` | Coupon display code. |
| `discount_type` | `string` | Deduction strategy (`"flat"` value or `"percentage"` ratio). |
| `discount_value` | `number` | Numeric deduction rate (e.g. `100` for flat or `15` for 15%). |
| `min_fare_threshold`| `number` | Minimum booking grand total base required to qualify. |
| `status` | `string` | State parameters (`"active"` or `"inactive"`). |
| `visible_to_customer`| `boolean` | Flag for visibility in customer promotions list. |

---

### 6. Settings Collection (`/settings/rates`)
Global configurations used for dynamic system values.
*   **Document ID**: `rates` (Holds nested configurations).

| Field Key | Data Type | Structure Map Description |
| :--- | :--- | :--- |
| `rates` | `Map (Object)` | Holds nested pricing matrices for local, rental, intercity, and global configurations (detailed below). |
| `active_version_id`| `string` | Foreign Key referencing `/rates_history.id`. |
| `updated_ts` | `Timestamp` | Setting update timestamp. |

#### `rates` Map Structure:
*   `local`: `Map` (Mappings of local ride parameters per vehicle tier).
*   `rental`: `Map` (Mappings of hourly/distance packages per vehicle tier).
*   `intercity`: `Map` (Mappings of outstation kilometers and halt parameters per vehicle tier).
*   `global`: `Map` (Timing intervals e.g. night charge windows).

---

### 7. Rates History Collection (`/rates_history/{version_id}`)
Audit log of all historical rate configurations. Enables historical booking calculations to be audited back to the active rates configuration used during checkout.
*   **Document ID**: `R-` followed by creation timestamp (e.g. `R-1717540200000`).

| Field Key | Data Type | Description |
| :--- | :--- | :--- |
| `rates` | `Map (Object)` | Pricing matrices for vehicle tiers (same structure as above). |
| `creation_ts` | `Timestamp` | Version registration timestamp. |

---

## 4. 📊 Entity Relationship Diagram (ERD)

This diagram visualizes relationships between the Firestore document collections. Relationships are maintained logically using string references representing keys.

```mermaid
erDiagram
    users {
        string uid PK "Document ID"
        string name
        string email
        string phone
        string role
        timestamp creation_ts
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

    users ||--o{ bookings : "submits"
    drivers |o--o| vehicles : "assigned bidirectionally (assigned_vehicle_id / assigned_driver_id)"
    bookings }o--o| drivers : "allocated on approval (driver_assignment.driver_id)"
    bookings }o--o| vehicles : "allocated on approval (driver_assignment.vehicle_id)"
    bookings }o--o| offers : "applies coupon (fare_details.promo_code)"
    bookings }o--o| rates_history : "calculated under configuration (fare_details.rates_version_id)"
    settings_rates }o--|| rates_history : "tracks active version (active_version_id)"
```
