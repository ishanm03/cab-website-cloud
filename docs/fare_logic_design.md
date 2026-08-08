# SETHCABS Kolkata Ride Fare Calculation Logic & Design

This document serves as the single source of truth for all pricing models within the SETHCABS Kolkata platform (Local, Rental, and Intercity). The calculations and administrative controls defined below must produce identical results across the Customer App, Website, Admin Dashboard, and backend API endpoints.

---

## 1. Local Ride Pricing Model

### Vehicle Categories & Parameters
| Category | Base Fare (0-d_inc KM) | Extra Distance Rate | Waiting Charge | Night Charge |
| :--- | :---: | :---: | :---: | :---: |
| **Compact Ride** | ₹550 | ₹12 / KM | ₹3 / Minute | ₹200 |
| **Premium Ride** | ₹650 | ₹13 / KM | ₹4 / Minute | ₹300 |
| **SUV Ride** | ₹750 | ₹14 / KM | ₹5 / Minute | ₹400 |
| **Group MUV (12 Seater)** | ₹850 | ₹15 / KM | ₹5 / Minute | ₹500 |

### Rules & Sequence
1. **Base Fare**: Start with the selected category's base rate (includes up to $d_{\text{inc}}$ KM, configurable under Global Rules settings, defaulting to 10 KM).
2. **Extra Distance**:
   $$\text{Extra Distance Charge} = \max(0, \text{Total Distance} - d_{\text{inc}}) \times \text{Extra KM Rate}$$
3. **Waiting Charge**:
   $$\text{Waiting Charge} = \text{Waiting Minutes} \times \text{Waiting Rate}$$
4. **Night Charge**: Apply the flat category-specific Night Charge if the ride starts between **11:59 PM and 6:00 AM**. Otherwise, ₹0.
5. **Toll & Parking**: Add actual Toll and Parking charges directly.
6. **Discount**: Subtract the promo or custom discount (capped so the subtotal cannot go below ₹0).
7. **Final Formula**:
   $$\text{Final Fare} = \max(0, \text{Base Fare} + \text{Extra Distance Charge} + \text{Waiting Charge} + \text{Night Charge} + \text{Toll} + \text{Parking} - \text{Discount})$$

---

## 2. Rental Package Pricing Model

### Minimum Rental Package Setup
* **Included Duration**: 6 Hours
* **Included Distance**: 60 KM
* **Base Package Rule**: The base fare covers up to 6 hours or 60 KM, whichever limit is crossed first.

### Ride Categories & Parameters
| Category | Base Fare | Extra KM Rate | Extra Hour Rate | Night Charge | Default Discount |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Compact Ride** | ₹2,300 | ₹12 / KM | ₹180 / Hour | ₹200 | ₹500 |
| **Premium Ride** | ₹2,500 | ₹13 / KM | ₹240 / Hour | ₹300 | ₹500 |
| **SUV Ride** | ₹2,800 | ₹14 / KM | ₹300 / Hour | ₹400 | ₹500 |
| **Group MUV (12 Seater)** | ₹3,300 | ₹16 / KM | ₹360 / Hour | ₹500 | ₹500 |

### Rules & Sequence
1. **Base Fare**: Start with the category base package rate.
2. **Extra KM**:
   $$\text{Extra KM Charge} = \max(0, \text{Total KM} - 60) \times \text{Extra KM Rate}$$
3. **Extra Hours**:
   $$\text{Extra Hour Charge} = \max(0, \text{Total Hours} - 6) \times \text{Extra Hour Rate}$$
4. **Night Charge**: Apply if pickup is between **11:59 PM and 6:00 AM**.
5. **Discount**: Deducted from the subtotal (Default is ₹500, but can be overridden by admin).
6. **Additional Configurable Charges**: Add Toll, Parking, Driver Night Allowance, State Entry Tax, GST, and Miscellaneous Charges after applying the discount.
7. **Final Formula**:
   $$\text{Final Fare} = \max(0, \text{Base Fare} + \text{Extra KM Charge} + \text{Extra Hour Charge} + \text{Night Charge} - \text{Discount}) + \text{Toll} + \text{Parking} + \text{Driver Allowance} + \text{Other}$$

---

## 3. Intercity Pricing Model

### Ride Categories & Parameters
| Category | Supported Vehicles | Rate Per KM | Driver Allowance / Day | Night Halt / Night |
| :--- | :--- | :---: | :---: | :---: |
| **Compact Ride** | WagonR, Tiago, Celerio | ₹12 | ₹600 | ₹500 |
| **Premium Ride** | Dzire, Amaze, Aura | ₹14 | ₹600 | ₹500 |
| **SUV Ride** | Scorpio, Bolero, Xylo | ₹18 | ₹800 | ₹500 |
| **Group MUV Ride** | Innova Crysta, Ertiga, Carens | ₹22 | ₹800 | ₹500 |

### Rules & Sequence
1. **Minimum Daily Distance**: Minimum billing is **250 KM per travel day**.
   $$\text{Min Billable KM} = 250 \times \text{Travel Days}$$
2. **Billable KM**:
   $$\text{Billable KM} = \max(\text{One-way Distance} \times 2, \text{Min Billable KM})$$
3. **Base Fare**:
   $$\text{Base Fare} = \text{Billable KM} \times \text{Rate Per KM}$$
4. **Driver Allowance**:
   $$\text{Driver Allowance} = \text{Driver Rate/Day} \times \text{Travel Days}$$
5. **Final Formula**:
   $$\text{Final Fare} = \text{Base Fare} + \text{Driver Allowance} + \text{Toll} + \text{Parking} + \text{State Tax} + \text{Night Halt}$$

---

## 4. Admin Configuration & Extensibility Requirements

To ensure future ride categories, pricing rates, and fees can be updated without code changes, the database and admin dashboard must implement the following schemas:

### Firestore Document Schema: `settings/rates`
```json
{
  "local": {
    "compact": { "base_fare": 550, "extra_km_rate": 12, "waiting_rate": 3, "night_charge": 200 },
    "premium": { "base_fare": 650, "extra_km_rate": 13, "waiting_rate": 4, "night_charge": 300 },
    "suv": { "base_fare": 750, "extra_km_rate": 14, "waiting_rate": 5, "night_charge": 400 },
    "muv": { "base_fare": 850, "extra_km_rate": 15, "waiting_rate": 5, "night_charge": 500 }
  },
  "rental": {
    "compact": { "base_fare": 2300, "included_hours": 6, "included_km": 60, "extra_km_rate": 12, "extra_hour_rate": 180, "night_charge": 200, "default_discount": 500 },
    "premium": { "base_fare": 2500, "included_hours": 6, "included_km": 60, "extra_km_rate": 13, "extra_hour_rate": 240, "night_charge": 300, "default_discount": 500 },
    "suv": { "base_fare": 2800, "included_hours": 6, "included_km": 60, "extra_km_rate": 14, "extra_hour_rate": 300, "night_charge": 400, "default_discount": 500 },
    "muv": { "base_fare": 3300, "included_hours": 6, "included_km": 60, "extra_km_rate": 16, "extra_hour_rate": 360, "night_charge": 500, "default_discount": 500 }
  },
  "intercity": {
    "compact": { "rate_per_km": 12, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
    "premium": { "rate_per_km": 14, "driver_allowance": 600, "min_km_per_day": 250, "night_halt": 500 },
    "suv": { "rate_per_km": 18, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 },
    "muv": { "rate_per_km": 22, "driver_allowance": 800, "min_km_per_day": 250, "night_halt": 500 }
  },
  "global": {
    "night_charge_start": "23:59",
    "night_charge_end": "06:00",
    "local_included_km": 10
  }
}
```

### Dashboard Requirements
* **Extensible Editing**: Admins must be able to add new vehicle categories or modify all numeric values (rates, base package hours/KMs, times for night charges).
* **Breakdown Display**: Every calculated price must display its granular sub-components (Base Fare, Extra distance/time, night charges, taxes, allowances, and discount details) to riders and admins.
* **Backend Validation**: The backend must enforce validation rules (no negative numbers, inputs within safe thresholds) using Pydantic schemas.
