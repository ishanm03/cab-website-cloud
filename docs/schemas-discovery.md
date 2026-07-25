# Firestore Schemas & API Contract Discovery (Version 1.0)

This document locks down the data schemas and payload structures for the 8 primary Firestore collections in the IshanCabs / SETHCABS database, standardizes the backend API response envelopes, and integrates the updated fare calculation logic.

---

## 1. Standard API Response Envelopes

To decouple the client-side frontend from direct database formatting, all backend APIs must return a standardized JSON structure.

### Success Envelope
```json
{
  "data": {
    "key": "value"
  },
  "meta": {
    "timestamp": "2026-07-25T04:20:00Z",
    "version": "1.0"
  }
}
```

### Error Envelope
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The provided inputs failed schema constraints.",
    "details": [
      {
        "loc": ["body", "phone"],
        "msg": "value is not a valid phone number",
        "type": "value_error"
      }
    ]
  }
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
  | `creation_ts` | Timestamp | Yes | Profile creation date/time. |
  | `updated_ts` | Timestamp | Yes | Last modified date/time. |

---

### 2.2 Collection: `bookings`
Represents cab booking requests, invoices, and assignments.

* **Document ID**: `booking_id` (Formatted string: `BK-YYYYMMDD-XXXX`, e.g. `BK-20260725-4928`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `booking_id` | String | Yes | Date-based formatted booking ID. |
  | `customer_id` | String | Yes | Associated rider's `uid`. |
  | `booking_channel` | String | Yes | Source of booking (e.g., "website", "mobile", "whatsapp", "admin"). |
  | `status` | String | Yes | Lifecycle status ("pending_approval", "confirmed", "active", "completed", "cancelled", "rejected"). |
  | `payment_status` | String | Yes | Transaction state ("pending", "paid", "refunded"). |
  | `driver_assignment` | Object / Null | No | Driver details when allocated (see sub-schema below). |
  | `trip_details` | Object | Yes | Geo, schedule, and duration options (see sub-schema below). |
  | `fare_details` | Object | Yes | Cost breakdown and rates version identifier (see sub-schema below). |
  | `creation_ts` | Timestamp | Yes | Booking registration timestamp. |
  | `updated_ts` | Timestamp | Yes | Last status change timestamp. |

#### Sub-Schema: `driver_assignment`
```json
{
  "driver_id": "918981538038",
  "driver_name": "Rajesh Kumar",
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
  "pickup_coords": { "lat": 22.5834, "lng": 88.3414 },
  "drop_coords": { "lat": 22.6547, "lng": 88.4467 },
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
  | `creation_ts` | Timestamp | Yes | Date/time registered. |

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
  | `creation_ts` | Timestamp | Yes | Registration timestamp. |

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
  | `local` | Object | Yes | Maps vehicle tier specific rates for local rides (see structure below). |
  | `rental` | Object | Yes | Maps vehicle tier package targets for rentals (see structure below). |
  | `intercity` | Object | Yes | Maps vehicle tier parameters for long distance trips (see structure below). |
  | `global` | Object | Yes | Global timing and tax parameters (see structure below). |

#### Sub-Schema: `local`
Contains nested rates for each tier:
```json
{
  "compact": { "base_fare": 550, "extra_km_rate": 12, "waiting_rate": 3, "night_charge": 200 },
  "premium": { "base_fare": 650, "extra_km_rate": 13, "waiting_rate": 4, "night_charge": 300 },
  "suv": { "base_fare": 750, "extra_km_rate": 14, "waiting_rate": 5, "night_charge": 400 },
  "muv": { "base_fare": 850, "extra_km_rate": 15, "waiting_rate": 5, "night_charge": 500 }
}
```

#### Sub-Schema: `rental`
Contains nested hourly/distance packages for each tier:
```json
{
  "compact": { "base_fare": 2300, "included_hours": 6, "included_km": 60, "extra_km_rate": 12, "extra_hour_rate": 180, "night_charge": 200, "default_discount": 500 },
  "premium": { "base_fare": 2500, "included_hours": 6, "included_km": 60, "extra_km_rate": 13, "extra_hour_rate": 240, "night_charge": 300, "default_discount": 500 },
  "suv": { "base_fare": 2800, "included_hours": 6, "included_km": 60, "extra_km_rate": 14, "extra_hour_rate": 300, "night_charge": 400, "default_discount": 500 },
  "muv": { "base_fare": 3300, "included_hours": 6, "included_km": 60, "extra_km_rate": 16, "extra_hour_rate": 360, "night_charge": 500, "default_discount": 500 }
}
```

#### Sub-Schema: `intercity`
Contains nested intercity guidelines:
```json
{
  "compact": { "rate_per_km": 12, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
  "premium": { "rate_per_km": 14, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
  "suv": { "rate_per_km": 18, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 },
  "muv": { "rate_per_km": 22, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 }
}
```

#### Sub-Schema: `global`
```json
{
  "night_charge_start": "23:59",
  "night_charge_end": "06:00",
  "gst_percentage": 5.0
}
```

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
  | `creation_ts` | Timestamp | Yes | Seeding or creation timestamp. |

---

### 2.8 Collection: `flat_fares`
Predefined pricing overrides for high-traffic routes.

* **Document ID**: `pickupId_dropId` (e.g. `howrah_station_kolkata_airport`)
* **Fields**:
  | Field | Type | Required | Description |
  | :--- | :--- | :---: | :--- |
  | `id` | String | Yes | Composite identifier format: `pickup_drop`. |
  | `pickup_name` | String | Yes | Name of the origin landmark. |
  | `drop_name` | String | Yes | Name of the destination landmark. |
  | `fares` | Object | Yes | Price mappings per vehicle class (see structure below). |
  | `creation_ts` | Timestamp | Yes | Document creation timestamp. |

#### Sub-Schema: `fares`
```json
{
  "compact": 490,
  "premium": 580,
  "suv": 850,
  "muv": 1100
}
```
