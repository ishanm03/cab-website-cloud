# Firestore Schemas & API Contract Discovery (Version 1.0)

This document locks down the data schemas and payload structures for the 8 primary Firestore collections in the **SethCabs** database, standardizes the backend API response envelopes, and integrates the updated fare calculation logic.

---

## 1. Standard API Response Envelopes

To decouple the client-side frontend from direct database formatting, all backend APIs return a standardized JSON structure.

### Success Envelope (Standard Mutations & Actions)
```json
{
  "status": "success",
  "booking_id": "BK-20260725-4928"
}
```

### Profile Fetch Envelope (`GET /api/v1/me/profile`)
```json
{
  "uid": "test_rider_uid",
  "name": "Ishan Mukherjee",
  "city": "Kolkata",
  "phone": "9830098300",
  "email": "rider@test.com",
  "auth_provider": "password",
  "status": "active",
  "creation_ts": "2026-08-01T12:00:00",
  "updated_ts": "2026-08-01T12:00:00"
}
```

### Error Envelope
```json
{
  "detail": "Failed to submit booking: Quote signature verification failed or signature expired."
}
```

---

## 2. Firestore Collection Schemas

### 2.1 Collection: `users`
Represents the rider and administrative user profiles.

* **Document ID**: `uid` (Firebase Auth UID, string)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :---: | :---: | :--- |
  | `uid` | String | Yes | Unique user ID from Firebase Auth. |
  | `name` | String | Yes | Full name of the user. |
  | `city` | String | Yes | Registered city (default: "Kolkata"). |
  | `phone` | String | Yes | Handphone number (10 digits). |
  | `email` | String | No | Valid email address. |
  | `auth_provider` | String | Yes | Provider string (e.g. "password", "google"). |
  | `status` | String | Yes | Profile status ("active", "suspended"). |
  | `creation_ts` | Timestamp / String | Yes | Profile creation date/time. |
  | `updated_ts` | Timestamp / String | Yes | Last modified date/time. |

---

### 2.2 Collection: `bookings`
Represents cab booking requests, invoices, and assignments.

* **Document ID**: `booking_id` (Formatted string: `BK-YYYYMMDD-XXXX`, e.g. `BK-20260725-4928`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `booking_id` | String | Yes | Date-based formatted booking ID. |
  | `customer_id` | String | Yes | Associated rider's `uid`. |
  | `customer_name` | String | Yes | User name snapshot copy for fast rendering. |
  | `customer_phone` | String | Yes | User phone snapshot copy. |
  | `booking_channel` | String | Yes | Source of booking (e.g., "website", "admin"). |
  | `status` | String | Yes | Lifecycle status ("pending_approval", "confirmed", "active", "completed", "cancelled", "rejected"). |
  | `payment_status` | String | Yes | Transaction state ("pending", "paid", "refunded"). |
  | `driver_assignment` | Object / Null | No | Driver details when allocated (see sub-schema below). |
  | `trip_details` | Object | Yes | Geo, schedule, and duration options (see sub-schema below). |
  | `fare_details` | Object | Yes | Cost breakdown and rates version identifier (see sub-schema below). |
  | `feedback` | Object / Null | No | Review comments and ratings submitted by customer (see sub-schema below). |
  | `rejection_reason` | String / Null | No | Logged explanation when status is `"rejected"`. |
  | `creation_ts` | Timestamp / String | Yes | Booking registration timestamp. |
  | `updated_ts` | Timestamp / String | Yes | Last status change timestamp. |

#### Sub-Schema: `driver_assignment`
```json
{
  "driver_id": "918981538038",
  "driver_name": "Rajesh Kumar",
  "driver_phone": "+918981538038",
  "vehicle_id": "WB02A1234",
  "vehicle_model": "Suzuki WagonR",
  "assigned_at": "2026-07-25T05:00:00Z"
}
```

#### Sub-Schema: `trip_details`
```json
{
  "ride_type": "local",
  "pickup_location": "Howrah Station",
  "drop_location": "Kolkata Airport",
  "pickup_date": "2026-07-25",
  "pickup_time": "14:30",
  "outstation_days": null,
  "rental_hours": null,
  "pickup_coords": [22.5833, 88.3414],
  "drop_coords": [22.6547, 88.4467],
  "route_polyline": "..."
}
```

#### Sub-Schema: `fare_details`
```json
{
  "vehicle_tier": "compact",
  "estimated_km": 18.5,
  "base_fare": 550.0,
  "extra_distance_charge": 96.0,
  "waiting_charge": 60.0,
  "night_charge": 0.0,
  "toll_charges": 50.0,
  "parking_charges": 30.0,
  "driver_allowance": 0.0,
  "discount_amount": 100.0,
  "promo_code": "WELCOME100",
  "estimated_fare": 686.0,
  "rates_version_id": "v0.4-rates-prod",
  "quote_signature": "hmac_signature_hex_string"
}
```

#### Sub-Schema: `feedback`
```json
{
  "rating": 5,
  "comments": "Excellent service and punctual driver!",
  "submitted_ts": "2026-08-01T14:50:00Z"
}
```

---

### 2.3 Collection: `vehicles`
Represents the available fleet assets.

* **Document ID**: `vehicle_id` (Normalized plate number, e.g. `WB02A1234`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `model` | String | Yes | Vehicle make and name (e.g. "Suzuki WagonR"). |
  | `plate_number` | String | Yes | Cleaned vehicle registration plate string. |
  | `tier` | String | Yes | Class category ("compact", "premium", "suv", "muv"). |
  | `status` | String | Yes | Operational state ("active", "inactive", "maintenance"). |
  | `assigned_driver_id` | String / Null | No | Phone number or ID of the linked driver. |
  | `passengers` | Number | Yes | Seat capacity (Compact/Premium: 4, SUV: 6, MUV: 12). |
  | `address` | String | Yes | Primary depot location. |
  | `creation_ts` | Timestamp / String | Yes | Date/time registered. |

---

### 2.4 Collection: `drivers`
Represents the driver registry database.

* **Document ID**: `driver_id` (Normalized phone number string, e.g. `918981538038`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `name` | String | Yes | Driver's full name. |
  | `phone` | String | Yes | Normalized phone contact number. |
  | `license_number` | String | Yes | RTO Driving License Number string. |
  | `status` | String | Yes | Working state ("active", "inactive", "on_trip"). |
  | `assigned_vehicle_id` | String / Null | No | Plate number of the assigned vehicle asset. |
  | `address` | String | Yes | Driver local city depot assignment. |
  | `creation_ts` | Timestamp / String | Yes | Registration timestamp. |

---

### 2.5 Collection: `offers`
Represents promotional coupons and discounts.

* **Document ID**: `code` (Uppercase string, e.g., `WELCOME100`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `code` | String | Yes | Uppercase alphanumeric coupon name. |
  | `discount_type` | String | Yes | Calculation mode ("flat", "percentage"). |
  | `discount_value` | Number | Yes | Price reduction amount or percentage value. |
  | `min_fare_threshold` | Number | Yes | Minimum base price required to apply. |
  | `status` | String | Yes | Activation status ("active", "inactive"). |
  | `visible_to_customer` | Boolean | Yes | Flag for promotional visibility in client apps. |

---

### 2.6 Collection: `settings/rates`
Dynamic tariff specifications for the three core ride models (Local, Rental, Intercity).

* **Document ID**: `rates` (stored in setting document path `/settings/rates`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `rates` | Object | Yes | Nested pricing configuration per vehicle tier (compact, premium, suv, muv) matching specifications below. |
  | `active_version_id` | String | Yes | Identifier reference linking to a document in `/rates_history`. |
  | `updated_ts` | Timestamp / String | Yes | Setting update timestamp. |

#### Sub-Schema Matrix (Rates):
* **Compact**: `{ "base_cost": 250, "rate_per_km": 10.00, "rate_per_hour": 120.00, "driver_allowance_per_day": 300.00 }`
* **Premium**: `{ "base_cost": 300, "rate_per_km": 12.00, "rate_per_hour": 150.00, "driver_allowance_per_day": 300.00 }`
* **SUV**: `{ "base_cost": 500, "rate_per_km": 15.00, "rate_per_hour": 200.00, "driver_allowance_per_day": 400.00 }`
* **MUV**: `{ "base_cost": 700, "rate_per_km": 18.00, "rate_per_hour": 250.00, "driver_allowance_per_day": 500.00 }`

---

### 2.7 Collection: `locations`
Represents geocoded landmark pins used for auto-routing.

* **Document ID**: `loc_id` (Snake-cased name, e.g. `howrah_station`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `id` | String | Yes | Lowercase snake_cased identifier. |
  | `name` | String | Yes | Human-readable name (e.g. "Howrah Station"). |
  | `type` | String | Yes | Pin eligibility ("pickup", "drop", "both"). |
  | `lat` | Number | Yes | Latitude coordinates decimal. |
  | `lng` | Number | Yes | Longitude coordinates decimal. |
  | `creation_ts` | Timestamp / String | Yes | Seeding or creation timestamp. |

---

### 2.8 Collection: `flat_fares`
Predefined pricing overrides for high-traffic routes.

* **Document ID**: `pickupId_dropId` (e.g. `howrah_station_airport`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `id` | String | Yes | Composite identifier format: `pickup_drop`. |
  | `pickup_name` | String | Yes | Name of the origin landmark. |
  | `drop_name` | String | Yes | Name of the destination landmark. |
  | `fares` | Object | Yes | Price mappings per vehicle class (see structure below). |
  | `creation_ts` | Timestamp / String | Yes | Document creation timestamp. |

#### Sub-Schema: `fares`
```json
{
  "compact": 850,
  "premium": 999,
  "suv": 1499,
  "muv": 1875
}
```
