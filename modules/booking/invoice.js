// modules/booking/invoice.js

import { auth, db } from "../shared/firebase.js";
import { doc, getDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// DOM Selector Handles
const invoiceLoader = document.getElementById("invoice-loader");
const invoiceContainer = document.getElementById("invoice-container");
const invoiceAlert = document.getElementById("invoice-alert");

const btnPrintInvoice = document.getElementById("btn-print-invoice");
const btnShareWhatsapp = document.getElementById("btn-share-whatsapp");

const invStatusPill = document.getElementById("invoice-status-pill");
const invSerialNumber = document.getElementById("inv-serial-number");
const invIssueDate = document.getElementById("inv-issue-date");
const invBookingId = document.getElementById("inv-booking-id");

const invCustomerName = document.getElementById("inv-customer-name");
const invCustomerPhone = document.getElementById("inv-customer-phone");
const invCustomerEmail = document.getElementById("inv-customer-email");
const invCustomerCity = document.getElementById("inv-customer-city");

const invVehicleTier = document.getElementById("inv-vehicle-tier");
const invVehicleNumber = document.getElementById("inv-vehicle-number");
const invDriverName = document.getElementById("inv-driver-name");
const invDriverPhone = document.getElementById("inv-driver-phone");

const invPickupAddress = document.getElementById("inv-pickup-address");
const invPickupDatetime = document.getElementById("inv-pickup-datetime");
const invStopsContainer = document.getElementById("inv-stops-container");
const invDropAddress = document.getElementById("inv-drop-address");
const invRideCategory = document.getElementById("inv-ride-category");
const invRouteDistance = document.getElementById("inv-route-distance");
const invTripType = document.getElementById("inv-trip-type");

const invLineItemsBody = document.getElementById("inv-line-items-body");
const invTotalAmount = document.getElementById("inv-total-amount");
const invAmountInWords = document.getElementById("inv-amount-in-words");
const invPaymentStatus = document.getElementById("inv-payment-status");

let loadedBooking = null;

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
    initInvoice();
});

async function initInvoice() {
    // 1. Read Booking ID from URL parameter (?id=BK-... or ?booking_id=BK-...)
    const urlParams = new URLSearchParams(window.location.search);
    const bookingId = urlParams.get("id") || urlParams.get("booking_id");

    if (!bookingId) {
        showError("Invalid Request: No booking ID specified in the URL. Please return to your bookings.");
        return;
    }

    // 2. Wire Button Events
    if (btnPrintInvoice) {
        btnPrintInvoice.addEventListener("click", () => {
            window.print();
        });
    }

    if (btnShareWhatsapp) {
        btnShareWhatsapp.addEventListener("click", () => {
            if (!loadedBooking) return;
            shareInvoiceOnWhatsApp(loadedBooking);
        });
    }

    // 3. Fetch Booking Data
    await fetchInvoiceData(bookingId);
}

async function fetchInvoiceData(bookingId) {
    showLoader(true);
    hideError();

    try {
        let bookingData = null;

        // Try direct Firestore read first (fast & reliable if logged in with matching rules)
        if (db) {
            try {
                const docRef = doc(db, "bookings", bookingId);
                const docSnap = await getDoc(docRef);
                if (docSnap.exists()) {
                    bookingData = { id: docSnap.id, ...docSnap.data() };
                }
            } catch (fsErr) {
                console.warn("Direct Firestore read failed, falling back to API:", fsErr);
            }
        }

        // Fallback: Backend API call
        if (!bookingData) {
            const apiBase = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
                ? "http://localhost:8000/api/v1"
                : "/api/v1";

            const headers = { "Content-Type": "application/json" };
            if (auth && auth.currentUser) {
                try {
                    const token = await auth.currentUser.getIdToken();
                    headers["Authorization"] = `Bearer ${token}`;
                } catch (tokErr) {
                    console.warn("Could not retrieve auth token:", tokErr);
                }
            }

            const response = await fetch(`${apiBase}/bookings/${encodeURIComponent(bookingId)}/invoice`, {
                method: "GET",
                headers
            });

            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.detail || `Server returned HTTP ${response.status}`);
            }

            const result = await response.json();
            bookingData = result.invoice || result.data;
        }

        if (!bookingData) {
            throw new Error(`Booking ${bookingId} was not found in our database records.`);
        }

        loadedBooking = bookingData;
        renderInvoice(bookingData);
        showLoader(false);
    } catch (err) {
        console.error("Failed to load invoice:", err);
        showError(`Unable to load invoice: ${err.message}`);
        showLoader(false);
    }
}

function renderInvoice(booking) {
    const trip = booking.trip_details || {};
    const fare = booking.fare_details || {};
    const cust = booking.customer_details || {};
    const driver = booking.driver_assignment || null;
    const bookingId = booking.booking_id || booking.id || "BK-UNKNOWN";

    // 1. Meta & Status Pill
    const cleanId = bookingId.replace(/[^A-Za-z0-9]/g, "");
    invSerialNumber.textContent = `INV-${cleanId.slice(-8).toUpperCase()}`;
    invBookingId.textContent = bookingId;

    let issueDateFormatted = formatDate(new Date());
    if (booking.creation_ts) {
        if (booking.creation_ts.seconds) {
            issueDateFormatted = formatDate(new Date(booking.creation_ts.seconds * 1000));
        } else if (typeof booking.creation_ts === "string") {
            issueDateFormatted = formatDate(new Date(booking.creation_ts));
        }
    }
    invIssueDate.textContent = issueDateFormatted;

    // Status Pill
    const status = (booking.status || "confirmed").toLowerCase();
    if (status === "completed") {
        invStatusPill.className = "inline-block px-3 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider mb-2 bg-slate-800 border border-slate-700 text-slate-300";
        invStatusPill.textContent = "Ride Completed";
    } else if (status === "active" || status === "ongoing") {
        invStatusPill.className = "inline-block px-3 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider mb-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400";
        invStatusPill.textContent = "Ride In-Progress";
    } else if (status === "confirmed") {
        invStatusPill.className = "inline-block px-3 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider mb-2 bg-blue-500/10 border border-blue-500/30 text-blue-400";
        invStatusPill.textContent = "Ride Confirmed";
    } else {
        invStatusPill.className = "inline-block px-3 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider mb-2 bg-amber-500/10 border border-amber-500/30 text-amber-400";
        invStatusPill.textContent = "Booking Requested";
    }

    // 2. Customer Details
    invCustomerName.textContent = cust.name || "Valued Guest";
    invCustomerPhone.textContent = cust.phone ? formatPhone(cust.phone) : "N/A";
    invCustomerEmail.textContent = cust.email || "N/A";
    invCustomerCity.textContent = "Kolkata & Howrah Urban Region";

    // 3. Vehicle & Chauffeur Details
    const tier = (fare.vehicle_tier || "premium").toUpperCase();
    invVehicleTier.textContent = tier;

    if (driver && driver.vehicle_number) {
        invVehicleNumber.textContent = driver.vehicle_number;
        invDriverName.textContent = driver.driver_name || "Assigned Chauffeur";
        invDriverPhone.textContent = driver.driver_phone ? `Phone: ${formatPhone(driver.driver_phone)}` : "";
    } else {
        invVehicleNumber.textContent = "Allocated at Dispatch";
        invDriverName.textContent = "Chauffeur details will be messaged 15 mins before pickup";
        invDriverPhone.textContent = "";
    }

    // 4. Trip Itinerary
    invPickupAddress.textContent = trip.pickup_location || "Airport Terminal Area";
    invPickupDatetime.textContent = trip.pickup_date && trip.pickup_time
        ? `${trip.pickup_date} at ${trip.pickup_time}`
        : "Standard Dispatch";

    // Multi-Stops Rendering
    invStopsContainer.innerHTML = "";
    if (trip.drop_stops && Array.isArray(trip.drop_stops) && trip.drop_stops.length > 0) {
        trip.drop_stops.forEach((stop, idx) => {
            const stopAddress = typeof stop === "string" ? stop : (stop.address || stop.name || `Stop ${idx + 1}`);
            const stopEl = document.createElement("div");
            stopEl.className = "flex items-start gap-3 pl-2 py-1";
            stopEl.innerHTML = `
                <div class="w-4 h-4 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold text-[9px] shrink-0 mt-0.5">
                    ${idx + 1}
                </div>
                <div>
                    <span class="text-[9px] text-slate-500 print-text-muted uppercase font-bold block">Intermediate Stop ${idx + 1}</span>
                    <strong class="text-slate-300 print-text-dark font-medium">${stopAddress}</strong>
                </div>
            `;
            invStopsContainer.appendChild(stopEl);
        });
    }

    invDropAddress.textContent = trip.drop_location || "Destination";
    invRideCategory.textContent = (trip.ride_type || "Local").toUpperCase();
    invRouteDistance.textContent = `${fare.estimated_km || trip.distance_km || "--"} km`;
    invTripType.textContent = trip.trip_type === "round_trip" ? "Round-Trip" : "One-Way";

    // 5. Itemized Line Items Table
    renderLineItems(booking);

    // 6. Payment Status
    const isPaid = (booking.payment_status || "").toLowerCase() === "paid" || status === "completed";
    if (isPaid) {
        invPaymentStatus.textContent = "PAID (Direct Driver Settlement)";
        invPaymentStatus.className = "ml-1 text-emerald-400 font-semibold uppercase";
    } else {
        invPaymentStatus.textContent = "PENDING (Collect via Cash or UPI at Trip End)";
        invPaymentStatus.className = "ml-1 text-amber-400 font-semibold uppercase";
    }

    invoiceContainer.classList.remove("hidden");
}

function renderLineItems(booking) {
    const fare = booking.fare_details || {};
    const trip = booking.trip_details || {};
    const breakdown = fare.breakdown || {};

    invLineItemsBody.innerHTML = "";

    const rows = [];

    // Line 1: Base Fare / Package Rate
    const baseAmount = typeof breakdown.base_fare === "number" ? breakdown.base_fare : (fare.base_fare || fare.estimated_fare || 0);
    let baseDesc = "Base Package Fare";
    let baseRate = `${fare.vehicle_tier ? fare.vehicle_tier.toUpperCase() : "STANDARD"}`;

    if (trip.ride_type === "rental") {
        baseDesc = `Hourly Rental Package (${trip.rental_hours || 4} Hours)`;
    } else if (trip.ride_type === "outstation" || trip.ride_type === "intercity") {
        baseDesc = `Intercity / Outstation Package (${fare.estimated_km || "--"} km)`;
    } else {
        baseDesc = `Local Point-to-Point Transit`;
    }

    rows.push({
        desc: baseDesc,
        rate: baseRate,
        amount: Math.round(baseAmount)
    });

    // Line 2: Extra Kilometers (if any)
    if (breakdown.extra_km_charge && breakdown.extra_km_charge > 0) {
        rows.push({
            desc: "Extra Distance Overage",
            rate: "Calculated Rate/km",
            amount: Math.round(breakdown.extra_km_charge)
        });
    }

    // Line 3: Extra Hours (if rental)
    if (breakdown.extra_hour_charge && breakdown.extra_hour_charge > 0) {
        rows.push({
            desc: "Extra Time / Hours Overage",
            rate: "Standard Extra Hour Tariff",
            amount: Math.round(breakdown.extra_hour_charge)
        });
    }

    // Line 4: Night Surcharge
    if (breakdown.night_charge && breakdown.night_charge > 0) {
        rows.push({
            desc: "Night Transit Surcharge (23:59 - 06:00 Hrs)",
            rate: "Night Tariff",
            amount: Math.round(breakdown.night_charge)
        });
    }

    // Line 5: Driver Allowance / Night Halt
    if (breakdown.driver_allowance && breakdown.driver_allowance > 0) {
        rows.push({
            desc: "Driver Outstation Allowance",
            rate: "Per Calendar Day",
            amount: Math.round(breakdown.driver_allowance)
        });
    }
    if (breakdown.night_halt && breakdown.night_halt > 0) {
        rows.push({
            desc: "Driver Night Halt Charge",
            rate: "Per Night",
            amount: Math.round(breakdown.night_halt)
        });
    }

    // Line 6: Discount / Promo Deduction (if applicable)
    const discountAmount = fare.discount_amount || breakdown.discount || 0;
    if (discountAmount > 0) {
        rows.push({
            desc: `Promotional / Special Rebate (${fare.promo_code || "OFFER"})`,
            rate: "Deduction",
            amount: -Math.round(discountAmount),
            isDiscount: true
        });
    }

    // Render Table Rows
    rows.forEach(item => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-900/40 print-bg-light transition-colors";
        
        const isDisc = item.isDiscount;
        const amountDisplay = isDisc ? `- ₹${Math.abs(item.amount)}` : `₹${item.amount}`;
        const amountColor = isDisc ? "text-emerald-400 font-semibold" : "text-slate-200 print-text-dark font-medium";

        tr.innerHTML = `
            <td class="py-3 px-4 font-medium text-slate-200 print-text-dark">
                ${item.desc}
            </td>
            <td class="py-3 px-4 text-center text-slate-400 print-text-muted text-[11px]">
                ${item.rate}
            </td>
            <td class="py-3 px-4 text-right ${amountColor}">
                ${amountDisplay}
            </td>
        `;
        invLineItemsBody.appendChild(tr);
    });

    // Net Total
    const netTotal = Math.round(fare.estimated_fare || (baseAmount - discountAmount));
    invTotalAmount.textContent = `₹${netTotal.toLocaleString("en-IN")}/-`;
    invAmountInWords.textContent = `Amount in words: ${numberToIndianWords(netTotal)}`;
}

function shareInvoiceOnWhatsApp(booking) {
    const cust = booking.customer_details || {};
    const trip = booking.trip_details || {};
    const fare = booking.fare_details || {};
    const bookingId = booking.booking_id || booking.id;
    const currentUrl = window.location.href;

    const message = `🚖 *SETHCABS TAX & RIDE INVOICE*
━━━━━━━━━━━━━━━━━━━━
*Booking ID:* ${bookingId}
*Passenger:* ${cust.name || "Guest"}
*Pickup:* ${trip.pickup_location}
*Drop:* ${trip.drop_location}
*Date/Time:* ${trip.pickup_date} at ${trip.pickup_time}
*Vehicle:* ${(fare.vehicle_tier || "").toUpperCase()}
*Total Fare:* ₹${fare.estimated_fare}/- (Taxes Included)
━━━━━━━━━━━━━━━━━━━━
📄 *View / Download Official Invoice:*
${currentUrl}

Thank you for travelling with SethCabs!`;

    const waUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(waUrl, "_blank");
}

function formatDate(dateObj) {
    if (!dateObj || isNaN(dateObj.getTime())) return "--";
    const day = String(dateObj.getDate()).padStart(2, "0");
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[dateObj.getMonth()];
    const year = dateObj.getFullYear();

    let hours = dateObj.getHours();
    const minutes = String(dateObj.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;

    return `${day} ${month} ${year}, ${hours}:${minutes} ${ampm}`;
}

function formatPhone(phoneStr) {
    if (!phoneStr) return "";
    let clean = String(phoneStr).replace(/\D/g, "");
    if (clean.length === 10) {
        return `+91 ${clean.slice(0, 5)} ${clean.slice(5)}`;
    }
    if (clean.length === 12 && clean.startsWith("91")) {
        return `+91 ${clean.slice(2, 7)} ${clean.slice(7)}`;
    }
    return phoneStr;
}

function numberToIndianWords(num) {
    if (!num || isNaN(num) || num <= 0) return "Zero Rupees Only";

    const a = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"
    ];
    const b = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

    function inWords(n) {
        if (n < 20) return a[n];
        if (n < 100) return b[Math.floor(n / 10)] + (n % 10 !== 0 ? " " + a[n % 10] : "");
        if (n < 1000) return a[Math.floor(n / 100)] + " Hundred" + (n % 100 !== 0 ? " and " + inWords(n % 100) : "");
        if (n < 100000) return inWords(Math.floor(n / 1000)) + " Thousand" + (n % 1000 !== 0 ? " " + inWords(n % 1000) : "");
        if (n < 10000000) return inWords(Math.floor(n / 100000)) + " Lakh" + (n % 100000 !== 0 ? " " + inWords(n % 100000) : "");
        return inWords(Math.floor(n / 10000000)) + " Crore" + (n % 10000000 !== 0 ? " " + inWords(n % 10000000) : "");
    }

    return `Rupees ${inWords(Math.floor(num))} Only`;
}

function showLoader(show) {
    if (invoiceLoader) {
        invoiceLoader.style.display = show ? "flex" : "none";
    }
}

function showError(msg) {
    if (invoiceAlert) {
        invoiceAlert.textContent = msg;
        invoiceAlert.className = "max-w-4xl mx-auto mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold block text-center";
    }
}

function hideError() {
    if (invoiceAlert) {
        invoiceAlert.className = "hidden";
    }
}
