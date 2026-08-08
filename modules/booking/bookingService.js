// modules/booking/bookingService.js

import { auth, db } from "../shared/firebase.js";
import { 
    collection, 
    addDoc, 
    setDoc, 
    getDoc,
    doc, 
    query, 
    where, 
    getDocs, 
    serverTimestamp 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
    ? "http://localhost:8000/api/v1" 
    : "/api/v1";

const bookingService = {
    /**
     * Calculates the estimated grand total fare for a given trip configuration
     * @param {string} rideType - "local" | "intercity" | "outstation" | "rental"
     * @param {number} distance - Distance in kilometers (from routesMatrix)
     * @param {number} days - Outstation duration (in days)
     * @param {string} tier - "compact" | "premium" | "suv" | "muv"
     * @param {object} flatMetrics - Flat metrics from routeMatrix if available
     * @param {number} hours - Rental duration (in hours)
     * @param {object} activeRates - Dynamic rates setting from Firestore
     * @returns {number} Estimated total fare in INR
     */
    calculateFare(rideType, distance, days, tier, flatMetrics, hours = 0, activeRates = null, timeString = null) {
        if (!activeRates) {
            return 0; // Return 0 if rates have not loaded from Firestore yet
        }
        const actualDays = Math.max(1, parseInt(days) || 1);
        const actualDistance = parseFloat(distance) || 0;
        const actualHours = Math.max(1, parseInt(hours) || 1);
        
        const rates = activeRates.rates || activeRates;
        const categoryMap = rideType === "outstation" ? "intercity" : rideType;
        const categoryConfig = rates[categoryMap];
        if (!categoryConfig || !categoryConfig[tier]) {
            return 0;
        }
        const config = categoryConfig[tier];
        
        const globalCfg = rates.global || {};
        const nightStart = globalCfg.night_charge_start || "23:59";
        const nightEnd = globalCfg.night_charge_end || "06:00";
        
        const isNightTime = (tStr) => {
            if (!tStr) return false;
            try {
                const parseTime = (s) => {
                    const parts = s.split(":");
                    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
                };
                const t = parseTime(tStr);
                const start = parseTime(nightStart);
                const end = parseTime(nightEnd);
                if (start > end) { // Over midnight
                    return t >= start || t <= end;
                } else {
                    return t >= start && t <= end;
                }
            } catch (e) {
                return false;
            }
        };

        const nightApplies = isNightTime(timeString);

        // 1. Hourly rental calculations
        if (rideType === "rental") {
            const baseFare = parseFloat(config.base_fare) || 0;
            const inclKm = parseFloat(config.included_km) || 0;
            const inclHours = parseFloat(config.included_hours) || 0;
            
            const extraKmCharge = Math.max(0, actualDistance - inclKm) * (parseFloat(config.extra_km_rate) || 0);
            const extraHourCharge = Math.max(0, actualHours - inclHours) * (parseFloat(config.extra_hour_rate) || 0);
            const nightCharge = nightApplies ? (parseFloat(config.night_charge) || 0) : 0;
            const discount = parseFloat(config.default_discount) || 0;
            
            const subtotal = baseFare + extraKmCharge + extraHourCharge + nightCharge - discount;
            return Math.max(0, Math.round(subtotal));
        }

        // 2. If Local / Intercity and flat-rates are mapped in our routesMatrix, use them!
        if ((rideType === "local" || rideType === "intercity") && flatMetrics) {
            if (tier === "compact") return flatMetrics.base_fare_compact || Math.round((flatMetrics.base_fare_premium || flatMetrics.base_fare_sedan || 999) * 0.85);
            if (tier === "premium") return flatMetrics.base_fare_premium || flatMetrics.base_fare_sedan;
            if (tier === "suv") return flatMetrics.base_fare_suv;
            if (tier === "muv") return flatMetrics.base_fare_muv || Math.round((flatMetrics.base_fare_suv || 1000) * 1.25);
        }

        // 3. Fallback or Outstation computations
        if (rideType === "outstation") {
            const roundTripDistance = actualDistance * 2;
            const minimumBilledDistance = actualDays * (parseFloat(config.min_km_per_day) || 250);
            const finalBilledDistance = Math.max(roundTripDistance, minimumBilledDistance);
            
            const distanceCost = finalBilledDistance * (parseFloat(config.rate_per_km) || 0);
            const allowanceCost = actualDays * (parseFloat(config.driver_allowance) || 0);
            const nightHaltCost = Math.max(0, actualDays - 1) * (parseFloat(config.night_halt) || 0);
            
            return Math.round(distanceCost + allowanceCost + nightHaltCost);
        } else {
            // Local custom estimation
            const baseFare = parseFloat(config.base_fare) || 0;
            const extraKmCharge = Math.max(0, actualDistance - 10) * (parseFloat(config.extra_km_rate) || 0);
            const nightCharge = nightApplies ? (parseFloat(config.night_charge) || 0) : 0;
            return Math.round(baseFare + extraKmCharge + nightCharge);
        }
    },

    /**
     * Checks if a vehicle tier has availability for the selected pickup date
     * Prevents overbooking by comparing active bookings vs total fleet sizes
     * @param {string} tier - "compact" | "premium" | "suv" | "muv"
     * @param {string} dateString - "YYYY-MM-DD"
     * @returns {Promise<boolean>} Available status
     */
    /**
     * Cache for date availability checks
     */
    availabilityCache: { date: null, data: null },

    async checkAvailability(tier, dateString) {
        if (this.availabilityCache.date === dateString && this.availabilityCache.data) {
            return this.availabilityCache.data[tier] !== false;
        }
        try {
            const response = await fetch(`${API_BASE}/bookings/availability?date=${dateString}`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const result = await response.json();
            this.availabilityCache = { date: dateString, data: result.availability };
            return this.availabilityCache.data[tier] !== false;
        } catch (error) {
            console.error("bookingService: Error querying availability, defaulting to true:", error);
            return true;
        }
    },

    /**
     * Requests a cryptographically signed quote from the backend
     */
    async estimateQuote(payload) {
        try {
            const token = auth && auth.currentUser ? await auth.currentUser.getIdToken() : null;
            const headers = { "Content-Type": "application/json" };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }
            
            const response = await fetch(`${API_BASE}/quotes/estimate`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Error generating quote.");
            }
            return await response.json();
        } catch (error) {
            console.error("bookingService: estimateQuote failed:", error);
            throw error;
        }
    },

    /**
      * Commits a customer's booking request directly to the Cloud Firestore database via API
      * @param {object} bookingPayload - Comprehensive booking data matching trip schemas
      * @returns {Promise<string>} Generated Booking ID
      */
    async createBooking(bookingPayload) {
        try {
            const token = auth && auth.currentUser ? await auth.currentUser.getIdToken() : null;
            const headers = { "Content-Type": "application/json" };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const response = await fetch(`${API_BASE}/bookings`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify(bookingPayload)
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Error committing booking.");
            }

            const result = await response.json();
            console.log("bookingService: Booking committed successfully via API:", result.booking_id);
            return result.booking_id;
        } catch (error) {
            console.error("bookingService: createBooking failed:", error);
            throw error;
        }
    },

    /**
     * Compiles an automated booking confirmation text and returns the WhatsApp API trigger URI
     * @param {object} booking - Committed booking payload
     * @returns {string} WhatsApp API Redirect Link
     */
    compileWhatsAppLink(booking) {
        const supportPhone = "918981538038"; // Dispatch center phone
        
        const text = `🚖 *SethCabs: New Ride Booking*

*Booking ID:* ${booking.booking_id}
*Customer:* ${booking.customer_details.name} (${booking.customer_details.phone})
*Category:* ${booking.trip_details.ride_type.toUpperCase()}
*Pickup:* ${booking.trip_details.pickup_location}
*Drop:* ${booking.trip_details.drop_location}
*Pickup Date/Time:* ${booking.trip_details.pickup_date} at ${booking.trip_details.pickup_time}
${booking.trip_details.outstation_days ? `*Duration:* ${booking.trip_details.outstation_days} Days\n` : ""}*Car Class:* ${booking.fare_details.vehicle_tier.toUpperCase()}
*Estimated Total:* ₹${booking.fare_details.estimated_fare}/-

Please confirm driver and vehicle allocation details. Thank you!`;

        return `https://wa.me/${supportPhone}?text=${encodeURIComponent(text)}`;
    },

    /**
     * Fetches dynamic rates from Firestore settings/rates
     * @returns {Promise<object>} Map of rates per vehicle tier
     */
    async fetchRates() {
        try {
            const response = await fetch(`${API_BASE}/settings/rates`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            return { rates: data.rates, version_id: data.active_version_id || null };
        } catch (error) {
            console.error("SethCabs: Error fetching rates via API:", error);
            throw error;
        }
    },

    /**
     * Updates dynamic rates in Firestore settings/rates
     * @param {object} newRates - Map of rates per vehicle tier
     * @returns {Promise<void>}
     */
    async updateRates(newRates) {
        try {
            const response = await fetch(`${API_BASE}/settings/rates`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rates: newRates })
            });
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
        } catch (error) {
            console.error("SethCabs: Error updating rates via API:", error);
            throw error;
        }
    },

    /**
     * Fetches active promo codes that are marked to be visible to customers
     * @returns {Promise<Array>} List of visible promo offers
     */
    async fetchVisiblePromos() {
        try {
            const response = await fetch(`${API_BASE}/offers/visible`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("SethCabs: Error fetching visible promos via API:", error);
            return [];
        }
    },

    /**
     * Verifies a promo code against active offers in Firestore
     * @param {string} code - The promo code to check
     * @param {number} baseFare - Current booking base fare
     * @returns {Promise<object>} Validation result: { valid: boolean, discount: number, message: string }
     */
    async verifyPromoCode(code, baseFare) {
        try {
            const cleanCode = code.trim().toUpperCase();
            if (!cleanCode) {
                return { valid: false, discount: 0, message: "Please enter a promo code." };
            }
            
            const response = await fetch(`${API_BASE}/offers/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: cleanCode,
                    base_fare: baseFare
                })
            });
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                return { valid: false, discount: 0, message: errData.detail || "Error validating coupon." };
            }
            
            return await response.json();
        } catch (error) {
            console.error("SethCabs: Error verifying promo code via API:", error);
            return { valid: false, discount: 0, message: "Error verifying promo code. Please try again." };
        }
    },

    async submitFeedback(bookingId, rating, comments) {
        try {
            const token = db && typeof auth !== "undefined" && auth.currentUser ? await auth.currentUser.getIdToken() : null;
            const headers = { "Content-Type": "application/json" };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }
            const response = await fetch(`${API_BASE}/bookings/${bookingId}/feedback`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify({ rating, comments })
            });
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to submit feedback.");
            }
            return await response.json();
        } catch (error) {
            console.error("SethCabs: Error submitting feedback:", error);
            throw error;
        }
    }
};

export { bookingService };

