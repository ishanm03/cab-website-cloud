// modules/booking/bookingUI.js

import { auth, db } from "../shared/firebase.js";
import { dbService } from "../shared/dbService.js";
import { utils } from "../shared/utils.js";
import { routesMatrix, getRouteMetrics, terminalCoordinates } from "../shared/routesMatrix.js";
import { classifyDestination } from "../shared/locationClassifier.js";
import { bookingService } from "./bookingService.js?v=20260603";
import { authService } from "../auth/authService.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { 
    collection, 
    getDocs, 
    query, 
    where, 
    orderBy 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
    ? "http://localhost:8000/api/v1" 
    : "/api/v1";

// DOM Selector Handles
const riderWelcome = document.getElementById("rider-welcome");
const btnRiderLogout = document.getElementById("btn-rider-logout");

const bookingProgressBar = document.getElementById("booking-progress-bar");
const stepDot1 = document.getElementById("step-dot-1");
const stepDot2 = document.getElementById("step-dot-2");
const stepDot3 = document.getElementById("step-dot-3");
const stepText1 = document.getElementById("step-text-1");
const stepText2 = document.getElementById("step-text-2");
const stepText3 = document.getElementById("step-text-3");

const bookingAlert = document.getElementById("booking-alert");
const bookingLoader = document.getElementById("booking-loader");
const bookingLoaderText = document.getElementById("booking-loader-text");

// Panels
const panelStep1 = document.getElementById("panel-step-1");
const panelStep2 = document.getElementById("panel-step-2");
const panelStep3 = document.getElementById("panel-step-3");

// Step 1 Form elements
const formStep1 = document.getElementById("form-step-1");
const pickupSelect = document.getElementById("pickup-select");
const dropSelect = document.getElementById("drop-select");
const dropStopsWrapper = document.getElementById("drop-stops-wrapper");
const dropStopsList = document.getElementById("drop-stops-list");
const btnAddStop = document.getElementById("btn-add-stop");
const stopCounterBadge = document.getElementById("stop-counter-badge");
const pickupDate = document.getElementById("pickup-date");
const pickupTime = document.getElementById("pickup-time");
const tripTypeRadios = document.getElementsByName("trip-type");
const categoryRadios = document.getElementsByName("ride-category");
const catLocalContainer = document.getElementById("cat-local-container");
const catIntercityContainer = document.getElementById("cat-intercity-container");
const catOutstationContainer = document.getElementById("cat-outstation-container");
const catRentalContainer = document.getElementById("cat-rental-container");
const rentalHoursContainer = document.getElementById("rental-hours-container");
const rentalHoursSelect = document.getElementById("rental-hours");

// Custom Address inputs
const customPickupContainer = document.getElementById("custom-pickup-container");
const customPickupAddress = document.getElementById("custom-pickup-address");
const customDropContainer = document.getElementById("custom-drop-container");
const customDropAddress = document.getElementById("custom-drop-address");
const customFareNotice = document.getElementById("custom-fare-notice");

// Multi-drop stops state
let dropStops = []; // Array of { id, rowEl, selectEl, customContainerEl, customInputEl, customCoords, customTimer }
let mapStopMarkers = []; // Array of Leaflet markers for intermediate stops

// Step 2 elements
const routeKmBadge = document.getElementById("route-km-badge");
const fleetListContainer = document.getElementById("fleet-list-container");
const carCards = document.querySelectorAll(".car-card");
const btnBackTo1 = document.getElementById("btn-back-to-1");
const btnSubmitStep2 = document.getElementById("btn-submit-step-2");

// Step 3 elements
const summaryPickup = document.getElementById("summary-pickup");
const summaryDrop = document.getElementById("summary-drop");
const summaryDatetime = document.getElementById("summary-datetime");
const summaryCategory = document.getElementById("summary-category");
const summaryDaysRow = document.getElementById("summary-days-row");
const summaryDays = document.getElementById("summary-days");
const summaryTier = document.getElementById("summary-tier");
const summaryBaseFare = document.getElementById("summary-base-fare");
const summaryDiscountRow = document.getElementById("summary-discount-row");
const summaryPromoCodeName = document.getElementById("summary-promo-code-name");
const summaryDiscountAmount = document.getElementById("summary-discount-amount");
const promoCodeInput = document.getElementById("promo-code-input");
const btnApplyPromo = document.getElementById("btn-apply-promo");
const promoStatusMsg = document.getElementById("promo-status-msg");
const availableOffersContainer = document.getElementById("available-offers-container");
const offersChipsList = document.getElementById("offers-chips-list");
const summaryGrandTotal = document.getElementById("summary-grand-total");
const btnBackTo2 = document.getElementById("btn-back-to-2");
const btnConfirmBooking = document.getElementById("btn-confirm-booking");

// Step 3 detailed breakdown elements
const btnToggleFareBreakdown = document.getElementById("btn-toggle-fare-breakdown");
const breakdownChevron = document.getElementById("breakdown-chevron");
const fareBreakdownContent = document.getElementById("fare-breakdown-content");
let isFareBreakdownExpanded = false;
let currentBreakdownData = null;

// Active Session Context State Variables
let currentUser = null;
let currentProfile = null;
let currentRouteData = {
    pickup: "",
    drop: "",
    dateString: "",
    timeString: "",
    category: "",
    days: 1,
    km: 0,
    flatMetrics: null,
    pickupCoords: null,
    dropCoords: null,
    polyline: null
};
let selectedVehicleTier = null;
let selectedVehicleFare = 0; // Represents base fare before discounts
let appliedPromo = null; // { code: string, discount: number }
let activeRatesVersionId = null; // Tracks rates_history document for auditing

// Map & Geocoding State Variables
const bookingMapWrapper = document.getElementById("booking-map-wrapper");

let mapInstance = null;
let pickupMarker = null;
let dropMarker = null;
let mapPickupCoords = null; // [lat, lng]
let mapDropCoords = null;   // [lat, lng]
let mapPickupAddress = "";
let mapDropAddress = "";
let customPickupCoords = null;
let customDropCoords = null;
let customPickupTimer = null;
let customDropTimer = null;

let dbLocations = []; // Loaded dynamically from Firestore

// Initialize setup listeners
document.addEventListener("DOMContentLoaded", () => {
    initBookingUI();
});

function initBookingUI() {
    // 1. Session State Observer
    if (auth) {
        onAuthStateChanged(auth, handleUserSessionChange);
    }
    
    // 2. Logout trigger
    btnRiderLogout.addEventListener("click", handleLogout);

    // 3. Hydrate routes and time dropdowns dynamically from database
    loadDynamicLocations();
    populateTimeDropdown();

    // 4. Change pickups and populate drop options
    pickupSelect.addEventListener("change", handlePickupChange);
    initDropStops();
    if (btnAddStop) {
        btnAddStop.addEventListener("click", handleAddDropStop);
    }

    // 5. Trip Type listener
    tripTypeRadios.forEach(radio => {
        radio.addEventListener("change", handleTripTypeChange);
    });

    // Ride Category change to show/hide days selector
    categoryRadios.forEach(radio => {
        radio.addEventListener("change", handleCategoryChange);
    });

    // 6. Set calendar date restrictions (Lead Time Constraints) and trigger overlay on focus/click
    restrictDateInputs();
    setupDatepickerTrigger();

    // 7. Form Step 1 Submission
    formStep1.addEventListener("submit", handleStep1Submit);

    // 8. Vehicle Car Card Click handler
    setupCarSelection();

    // 9. Back buttons
    btnBackTo1.addEventListener("click", navigateBackTo1);
    btnBackTo2.addEventListener("click", navigateBackTo2);

    // 10. Step 2 click checkout trigger
    btnSubmitStep2.addEventListener("click", navigateToStep3);

    // 11. Final Confirm booking & WhatsApp redirect
    btnConfirmBooking.addEventListener("click", handleFinalConfirm);

    // 12. Apply Promo Code
    btnApplyPromo.addEventListener("click", handleApplyPromo);

    // 13. Dynamic Geocoding setup for Custom Location inputs
    setupCustomAddressGeocoding();

    // 14. Detailed Fare Breakdown accordion toggle
    if (btnToggleFareBreakdown) {
        btnToggleFareBreakdown.addEventListener("click", () => {
            isFareBreakdownExpanded = !isFareBreakdownExpanded;
            if (isFareBreakdownExpanded) {
                fareBreakdownContent.classList.remove("hidden");
                if (breakdownChevron) breakdownChevron.style.transform = "rotate(180deg)";
            } else {
                fareBreakdownContent.classList.add("hidden");
                if (breakdownChevron) breakdownChevron.style.transform = "rotate(0deg)";
            }
        });
    }
}

let isLoggingOut = false;
let idleTimer = null;
const INACTIVITY_LIMIT = 120000; // 2 minutes

function resetIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(async () => {
        console.log("[UAT-7] User idle for 2 minutes on booking page. Auto-logging out.");
        isLoggingOut = true;
        try {
            await authService.logout();
        } catch (err) {
            console.error("Sign out error:", err);
        }
        window.location.href = "../auth/login.html?logout=true";
    }, INACTIVITY_LIMIT);
}

function startInactivityTracker() {
    const events = ['mousemove', 'mousedown', 'keypress', 'touchstart', 'scroll'];
    events.forEach(evt => {
        document.addEventListener(evt, resetIdleTimer, true);
    });
    resetIdleTimer();
}

function stopInactivityTracker() {
    if (idleTimer) {
        clearTimeout(idleTimer);
        idleTimer = null;
    }
    const events = ['mousemove', 'mousedown', 'keypress', 'touchstart', 'scroll'];
    events.forEach(evt => {
        document.removeEventListener(evt, resetIdleTimer, true);
    });
}

// Redirect unauthenticated sessions
async function handleUserSessionChange(user) {
    if (user) {
        currentUser = user;
        startInactivityTracker();
        try {
            let profile = await dbService.getUserProfile(user.uid);
            if (!profile && user) {
                profile = {
                    uid: user.uid,
                    name: user.displayName || (user.email ? user.email.split("@")[0] : "Rider"),
                    city: "Kolkata",
                    phone: user.phoneNumber || "",
                    email: user.email || null
                };
            }
            if (profile) {
                currentProfile = profile;
                riderWelcome.textContent = `Welcome, ${profile.name || "Rider"}`;
                utils.showElement(riderWelcome);
            }
        } catch (error) {
            console.error("Failed to read user profile:", error);
            riderWelcome.textContent = "Welcome, Rider";
            utils.showElement(riderWelcome);
        }
    } else {
        currentUser = null;
        currentProfile = null;
        stopInactivityTracker();
        // User not logged in -> redirect back to login page
        if (!isLoggingOut) {
            window.location.href = "../auth/auth.html?msg=login_required";
        }
    }
}

// Header Log-off handler
async function handleLogout() {
    const confirmSignout = confirm("Are you sure you want to log out?");
    if (confirmSignout) {
        isLoggingOut = true;
        stopInactivityTracker();
        await authService.logout();
        window.location.href = "../auth/auth.html?logout=true";
    }
}

// Loads predefined locations from Firestore
async function loadDynamicLocations() {
    try {
        const response = await fetch(`${API_BASE}/locations`);
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        dbLocations = await response.json();
        console.log(`Loaded ${dbLocations.length} predefined locations from API.`);
        hydratePickupLocations();
    } catch (error) {
        console.error("Failed to load locations, using fallback coordinates:", error);
        dbLocations = Object.entries(terminalCoordinates).map(([name, coords]) => ({
            id: name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, ""),
            name: name,
            lat: coords[0],
            lng: coords[1],
            type: "both"
        }));
        hydratePickupLocations();
    }
}

// Hydrates select with available locations
function hydratePickupLocations() {
    pickupSelect.innerHTML = `<option value="" disabled selected>Select Pickup Node</option>
                              <option value="Custom Location">Custom Location</option>`;
    const pickups = dbLocations.filter(loc => loc.type === "pickup" || loc.type === "both");
    pickups.forEach(loc => {
        const opt = document.createElement("option");
        opt.value = loc.name;
        opt.textContent = loc.name;
        pickupSelect.appendChild(opt);
    });
}

// Initializes the initial drop stop row and wires event listeners
function initDropStops() {
    const initialRow = document.querySelector('.drop-stop-row[data-index="0"]');
    const initialSelect = document.getElementById("drop-select");
    const initialCustomContainer = document.getElementById("custom-drop-container");
    const initialCustomInput = document.getElementById("custom-drop-address");

    dropStops = [{
        id: 0,
        rowEl: initialRow,
        selectEl: initialSelect,
        customContainerEl: initialCustomContainer,
        customInputEl: initialCustomInput,
        customCoords: null,
        customTimer: null
    }];

    if (initialSelect) {
        initialSelect.addEventListener("change", () => handleDropChange(0));
    }

    if (initialCustomInput) {
        initialCustomInput.addEventListener("input", () => handleCustomDropInput(0));
    }

    updateStopLabels();
}

// Populates drop options for a specific select element
function renderDropOptionsForSelect(selectEl) {
    if (!selectEl) return;
    const currentVal = selectEl.value;
    const pickupVal = pickupSelect ? pickupSelect.value : "";

    selectEl.innerHTML = `<option value="" disabled ${!currentVal ? "selected" : ""}>Select Destination</option>`;
    selectEl.disabled = !pickupVal;
    
    if (pickupVal) {
        selectEl.className = "drop-stop-select w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-white px-4 py-3.5 rounded-xl outline-none transition-all duration-300 font-medium text-sm appearance-none";
    } else {
        selectEl.className = "drop-stop-select w-full bg-slate-950/40 border border-slate-800 text-slate-500 px-4 py-3.5 rounded-xl outline-none transition-all duration-300 font-medium text-sm appearance-none";
    }

    // Add Custom Location choice
    const customOpt = document.createElement("option");
    customOpt.value = "Custom Location";
    customOpt.textContent = "Custom Location";
    if (currentVal === "Custom Location") customOpt.selected = true;
    selectEl.appendChild(customOpt);

    let drops = [];
    if (pickupVal === "Custom Location") {
        drops = dbLocations.filter(loc => loc.type === "drop" || loc.type === "both");
    } else {
        drops = dbLocations.filter(loc => (loc.type === "drop" || loc.type === "both") && loc.name !== pickupVal);
    }

    drops.forEach(dest => {
        const opt = document.createElement("option");
        opt.value = dest.name;
        opt.textContent = dest.name;
        if (dest.name === currentVal) opt.selected = true;
        selectEl.appendChild(opt);
    });
}

// Populates options across all active drop stops
function populateAllDropStops() {
    dropStops.forEach(stop => {
        renderDropOptionsForSelect(stop.selectEl);
    });
}

// Adds a new intermediate stopover or final drop (up to 5 total)
function handleAddDropStop() {
    if (dropStops.length >= 5) {
        utils.showAlert(bookingAlert, "Maximum of 5 drop stops are supported per booking.");
        return;
    }

    const newId = Date.now();
    const newIndex = dropStops.length;

    const rowDiv = document.createElement("div");
    rowDiv.className = "drop-stop-row bg-slate-950/40 p-4 rounded-2xl border border-slate-800 space-y-2 relative transition-all";
    rowDiv.dataset.id = newId;

    rowDiv.innerHTML = `
        <div class="flex items-center justify-between">
            <span class="stop-label text-[10px] font-bold text-amber-500 uppercase tracking-wider"></span>
            <button type="button" class="btn-remove-stop text-slate-400 hover:text-rose-400 p-1 text-xs font-bold transition-colors flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                <span>Remove</span>
            </button>
        </div>
        <select class="drop-stop-select w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-white px-4 py-3.5 rounded-xl outline-none transition-all duration-300 font-medium text-sm appearance-none">
        </select>
        <div class="custom-drop-container hidden mt-2">
            <label class="block text-[10px] font-bold uppercase tracking-wider text-amber-500 mb-1">Enter Custom Drop Address</label>
            <input type="text" placeholder="E.g. Gate 3, City Center II, Rajarhat" class="custom-drop-input w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-white px-4 py-2.5 rounded-xl outline-none transition-all duration-300 text-xs font-medium">
        </div>
    `;

    dropStopsList.appendChild(rowDiv);

    const selectEl = rowDiv.querySelector(".drop-stop-select");
    const customContainerEl = rowDiv.querySelector(".custom-drop-container");
    const customInputEl = rowDiv.querySelector(".custom-drop-input");
    const btnRemove = rowDiv.querySelector(".btn-remove-stop");

    renderDropOptionsForSelect(selectEl);

    const stopObj = {
        id: newId,
        rowEl: rowDiv,
        selectEl,
        customContainerEl,
        customInputEl,
        customCoords: null,
        customTimer: null
    };

    selectEl.addEventListener("change", () => handleDropChange(newId));
    customInputEl.addEventListener("input", () => handleCustomDropInput(newId));
    btnRemove.addEventListener("click", () => handleRemoveDropStop(newId));

    dropStops.push(stopObj);

    updateStopLabels();
    toggleCustomAddressFields();
    toggleMapVisibility();
    syncRideCategoryWithDestination();
}

// Removes a drop stop row
function handleRemoveDropStop(id) {
    if (dropStops.length <= 1) return; // Keep at least 1 stop
    
    const index = dropStops.findIndex(s => s.id === id);
    if (index === -1) return;

    const stopObj = dropStops[index];
    if (stopObj.rowEl && stopObj.rowEl.parentElement) {
        stopObj.rowEl.remove();
    }

    dropStops.splice(index, 1);

    updateStopLabels();
    toggleCustomAddressFields();
    toggleMapVisibility();
    syncRideCategoryWithDestination();
}

// Re-indexes and numbers stop labels (Stop 1, Stop 2... Final Destination)
function updateStopLabels() {
    const total = dropStops.length;
    dropStops.forEach((stop, idx) => {
        const labelEl = stop.rowEl.querySelector(".stop-label");
        const btnRemove = stop.rowEl.querySelector(".btn-remove-stop");

        if (labelEl) {
            if (total === 1) {
                labelEl.textContent = "📍 Stop 1 (Destination)";
            } else if (idx === total - 1) {
                labelEl.textContent = `📍 Stop ${idx + 1} (Final Destination)`;
            } else {
                labelEl.textContent = `📍 Stop ${idx + 1} (Via Point)`;
            }
        }

        if (btnRemove) {
            if (total > 1) {
                btnRemove.classList.remove("hidden");
            } else {
                btnRemove.classList.add("hidden");
            }
        }
    });

    if (stopCounterBadge) {
        stopCounterBadge.textContent = `${total} of 5 Stops`;
    }

    if (btnAddStop) {
        if (total >= 5) {
            btnAddStop.classList.add("opacity-50", "pointer-events-none");
        } else {
            btnAddStop.classList.remove("opacity-50", "pointer-events-none");
        }
    }
}

// Resolves current data of all stops
function getDropStopsData() {
    return dropStops.map((stop, idx) => {
        const val = stop.selectEl ? stop.selectEl.value : "";
        const isCustom = val === "Custom Location";
        const customText = (isCustom && stop.customInputEl) ? stop.customInputEl.value.trim() : "";
        let coords = null;
        if (isCustom) {
            coords = stop.customCoords;
        } else if (val) {
            const loc = dbLocations.find(l => l.name === val);
            if (loc) coords = [loc.lat, loc.lng];
        }
        return {
            id: stop.id,
            index: idx,
            value: val,
            isCustom,
            customText,
            name: isCustom ? customText : val,
            coords
        };
    });
}

// Repopulates Dropdown options based on active Pickup choice
function handlePickupChange() {
    utils.hideElement(bookingAlert);
    const pickupVal = pickupSelect.value;
    
    if (pickupVal !== "Custom Location") {
        customPickupCoords = null;
    }

    populateAllDropStops();
    toggleCustomAddressFields();
    toggleMapVisibility();
    syncRideCategoryWithDestination();
}

function handleDropChange(stopId) {
    utils.hideElement(bookingAlert);
    const stopObj = dropStops.find(s => s.id === stopId);
    if (stopObj && stopObj.selectEl.value !== "Custom Location") {
        stopObj.customCoords = null;
    }
    toggleCustomAddressFields();
    toggleMapVisibility();
    syncRideCategoryWithDestination();
}

function handleCustomDropInput(stopId) {
    const stopObj = dropStops.find(s => s.id === stopId);
    if (!stopObj || !stopObj.customInputEl) return;

    clearTimeout(stopObj.customTimer);
    stopObj.customTimer = setTimeout(async () => {
        const address = stopObj.customInputEl.value.trim();
        if (address.length > 3) {
            console.log(`[Geocoding] Searching stop ${stopId} drop address:`, address);
            const coords = await geocodeAddress(address);
            if (coords) {
                stopObj.customCoords = coords;
                console.log(`[Geocoding] Stop ${stopId} resolved to:`, coords);
                initOrUpdateMap();
            }
            syncRideCategoryWithDestination();
        }
    }, 800);
}

// Dynamically classifies the destination across all stops and shows only the matching category
function syncRideCategoryWithDestination() {
    const tripType = document.querySelector('input[name="trip-type"]:checked')?.value || "one_way";
    if (tripType === "round_trip") {
        utils.hideElement(catLocalContainer);
        utils.hideElement(catIntercityContainer);
        utils.hideElement(catOutstationContainer);
        utils.showElement(catRentalContainer);
        document.querySelectorAll('input[name="ride-category"]').forEach(r => {
            r.checked = (r.value === "rental");
        });
        handleCategoryChange({ target: { value: "rental" } });
        return;
    }

    // Trip type is one_way:
    utils.hideElement(catRentalContainer);
    
    const stopsData = getDropStopsData();
    const activeStops = stopsData.filter(s => !!s.value);
    if (activeStops.length === 0) {
        // No drops selected yet - restore all 3 one-way categories
        utils.showElement(catLocalContainer);
        utils.showElement(catIntercityContainer);
        utils.showElement(catOutstationContainer);
        return;
    }

    // Evaluate categories across all selected stops (outstation > intercity > local)
    let highestCategory = "local";
    for (const stop of activeStops) {
        const cat = classifyDestination(stop.value, stop.coords, stop.customText);
        if (cat === "outstation") {
            highestCategory = "outstation";
            break;
        } else if (cat === "intercity" && highestCategory !== "outstation") {
            highestCategory = "intercity";
        }
    }

    console.log("[CategorySync] Multi-stop Determined Category:", highestCategory);

    // Hide all 3 categories first
    utils.hideElement(catLocalContainer);
    utils.hideElement(catIntercityContainer);
    utils.hideElement(catOutstationContainer);

    // Show only the determined category
    if (highestCategory === "outstation") {
        utils.showElement(catOutstationContainer);
    } else if (highestCategory === "intercity") {
        utils.showElement(catIntercityContainer);
    } else {
        utils.showElement(catLocalContainer);
    }

    // Set checked state explicitly on the radio inputs
    document.querySelectorAll('input[name="ride-category"]').forEach(r => {
        r.checked = (r.value === highestCategory);
    });

    handleCategoryChange({ target: { value: highestCategory } });
}

function toggleCustomAddressFields() {
    const isPickupCustom = pickupSelect.value === "Custom Location";
    const category = document.querySelector('input[name="ride-category"]:checked')?.value || "local";

    if (isPickupCustom) {
        utils.showElement(customPickupContainer);
        customPickupAddress.required = true;
    } else {
        utils.hideElement(customPickupContainer);
        customPickupAddress.required = false;
        customPickupAddress.value = "";
    }

    dropStops.forEach(stop => {
        const isCustom = stop.selectEl && stop.selectEl.value === "Custom Location";
        if (isCustom && category !== "rental") {
            utils.showElement(stop.customContainerEl);
            if (stop.customInputEl) stop.customInputEl.required = true;
        } else {
            utils.hideElement(stop.customContainerEl);
            if (stop.customInputEl) {
                stop.customInputEl.required = false;
                if (category === "rental") stop.customInputEl.value = "";
            }
        }
    });
}

function toggleMapVisibility() {
    const pickupVal = pickupSelect.value;
    const category = document.querySelector('input[name="ride-category"]:checked')?.value || "local";
    const stopsData = getDropStopsData();
    const hasAnyDrop = stopsData.some(s => !!s.value);

    const hasPickup = !!pickupVal;
    const hasDrop = (category === "rental" || hasAnyDrop);

    if (hasPickup && hasDrop) {
        utils.showElement(bookingMapWrapper);
        initOrUpdateMap();
    } else {
        utils.hideElement(bookingMapWrapper);
    }
}

function initOrUpdateMap() {
    const kolkataCenter = [22.5726, 88.3639];

    if (!mapInstance) {
        mapInstance = L.map('booking-map', {
            dragging: true,
            touchZoom: true,
            scrollWheelZoom: true,
            doubleClickZoom: true,
            boxZoom: true,
            keyboard: true,
            zoomControl: true
        }).setView(kolkataCenter, 12);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(mapInstance);
    }

    const pickupVal = pickupSelect.value;
    const category = document.querySelector('input[name="ride-category"]:checked')?.value || "local";

    // Resolve Pickup coordinates
    if (pickupVal === "Custom Location") {
        mapPickupCoords = customPickupCoords;
        mapPickupAddress = customPickupAddress.value.trim() || "Custom Location";
    } else {
        const pickupLoc = dbLocations.find(l => l.name === pickupVal);
        mapPickupCoords = pickupLoc ? [pickupLoc.lat, pickupLoc.lng] : null;
        mapPickupAddress = pickupVal || "";
    }

    // Draw/update Pickup Marker
    if (mapPickupCoords) {
        if (pickupMarker) {
            pickupMarker.setLatLng(mapPickupCoords);
        } else {
            pickupMarker = L.marker(mapPickupCoords, {
                title: "Pickup Location"
            }).addTo(mapInstance);
        }
        updateMarkerPopup(pickupMarker, "🚩 Pickup: " + mapPickupAddress);
    } else {
        if (pickupMarker) {
            mapInstance.removeLayer(pickupMarker);
            pickupMarker = null;
        }
    }

    // Clear existing drop stop markers
    mapStopMarkers.forEach(m => mapInstance.removeLayer(m));
    mapStopMarkers = [];

    // Gather waypoints
    const waypoints = [];
    const markerGroup = [];
    if (mapPickupCoords) {
        waypoints.push(mapPickupCoords);
        if (pickupMarker) markerGroup.push(pickupMarker);
    }

    if (category !== "rental") {
        const stopsData = getDropStopsData();
        const totalStops = stopsData.length;

        stopsData.forEach((stop, idx) => {
            if (stop.coords) {
                waypoints.push(stop.coords);
                const isFinal = (idx === totalStops - 1);
                const labelText = isFinal 
                    ? `🏁 Destination: ${stop.name || 'Drop'}` 
                    : `📍 Stop ${idx + 1}: ${stop.name || 'Via'}`;

                const marker = L.marker(stop.coords, {
                    title: labelText
                }).addTo(mapInstance);
                updateMarkerPopup(marker, labelText);
                mapStopMarkers.push(marker);
                markerGroup.push(marker);
            }
        });
    }

    // Draw/update multi-waypoint polyline if at least 2 waypoints
    if (waypoints.length >= 2) {
        fetchOSRMRoute(waypoints).then(routeData => {
            const coords = routeData.geometry.coordinates;
            const polylinePoints = coords.map(coord => [coord[1], coord[0]]);
            
            if (window.bookingPolyline) {
                mapInstance.removeLayer(window.bookingPolyline);
            }
            window.bookingPolyline = L.polyline(polylinePoints, { color: '#f59e0b', weight: 4, opacity: 0.8 }).addTo(mapInstance);
            
            if (markerGroup.length > 0) {
                const group = new L.featureGroup(markerGroup);
                mapInstance.fitBounds(group.getBounds().pad(0.15));
            }
        }).catch(err => {
            console.warn("OSRM multi-waypoint route fetch failed for preview:", err);
            // Draw straight line fallback
            if (window.bookingPolyline) {
                mapInstance.removeLayer(window.bookingPolyline);
            }
            window.bookingPolyline = L.polyline(waypoints, { color: '#f59e0b', weight: 3, opacity: 0.8, dashArray: '5, 5' }).addTo(mapInstance);
            if (markerGroup.length > 0) {
                const group = new L.featureGroup(markerGroup);
                mapInstance.fitBounds(group.getBounds().pad(0.15));
            }
        });
    } else {
        if (window.bookingPolyline) {
            mapInstance.removeLayer(window.bookingPolyline);
            window.bookingPolyline = null;
        }
        if (mapPickupCoords) {
            mapInstance.setView(mapPickupCoords, 14);
        }
    }

    // Adjust view size
    setTimeout(() => {
        if (mapInstance) {
            mapInstance.invalidateSize();
        }
    }, 100);
}

function updateMarkerPopup(marker, text) {
    if (!marker) return;
    marker.bindPopup(text).openPopup();
}

async function geocodeAddress(address) {
    if (!address) return null;
    try {
        const query = encodeURIComponent(address + ", West Bengal, India");
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}&limit=1`, {
            headers: { 'Accept-Language': 'en' }
        });
        if (response.ok) {
            const results = await response.json();
            if (results && results.length > 0) {
                return [parseFloat(results[0].lat), parseFloat(results[0].lon)];
            }
        }
    } catch (e) {
        console.error("Geocoding failed for address:", address, e);
    }
    return null;
}

function setupCustomAddressGeocoding() {
    if (!customPickupAddress) return;

    customPickupAddress.addEventListener("input", () => {
        clearTimeout(customPickupTimer);
        customPickupTimer = setTimeout(async () => {
            const address = customPickupAddress.value.trim();
            if (address.length > 3) {
                console.log("[Geocoding] Searching custom pickup:", address);
                const coords = await geocodeAddress(address);
                if (coords) {
                    customPickupCoords = coords;
                    console.log("[Geocoding] Custom pickup resolved to:", customPickupCoords);
                    initOrUpdateMap();
                }
            }
        }, 800);
    });
}

// Multi-waypoint OSRM router
async function fetchOSRMRoute(waypoints) {
    if (!waypoints || waypoints.length < 2) {
        throw new Error("At least 2 waypoints required for OSRM routing");
    }
    // OSRM expects coordinates in lng,lat format joined by semicolons
    const coordsString = waypoints.map(pt => `${pt[1]},${pt[0]}`).join(';');
    const url = `https://router.project-osrm.org/route/v1/driving/${coordsString}?overview=full&geometries=geojson`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error("Failed to fetch route from OSRM");
    }
    const data = await response.json();
    if (!data.routes || data.routes.length === 0) {
        throw new Error("No route found between selected coordinates");
    }
    return data.routes[0];
}

function getHaversineDistance(coords1, coords2) {
    const R = 6371; // Earth's radius in km
    const dLat = (coords2[0] - coords1[0]) * Math.PI / 180;
    const dLng = (coords2[1] - coords1[1]) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(coords1[0] * Math.PI / 180) * Math.cos(coords2[0] * Math.PI / 180) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Math.ceil(R * c * 1.3); // Apply 30% routing overhead to approximate actual driving distance
}

function getHaversineRouteDistance(waypoints) {
    if (!waypoints || waypoints.length < 2) return 0;
    let total = 0;
    for (let i = 0; i < waypoints.length - 1; i++) {
        total += getHaversineDistance(waypoints[i], waypoints[i+1]);
    }
    return Math.ceil(total);
}

function handleTripTypeChange(e) {
    const tripType = e.target.value;
    console.log("[UAT-TripType] Selected Trip Type:", tripType);
    syncRideCategoryWithDestination();
}

// Shows/Hides rental hours and toggles drop stops visibility
function handleCategoryChange(e) {
    utils.hideElement(bookingAlert);
    const category = e.target.value;
    console.log("[UAT-Category] Category changed to:", category);

    if (category === "rental") {
        utils.showElement(rentalHoursContainer);
        rentalHoursSelect.required = true;
        
        if (dropStopsWrapper) utils.hideElement(dropStopsWrapper);
        dropStops.forEach(stop => {
            if (stop.selectEl) {
                stop.selectEl.required = false;
                stop.selectEl.value = "";
            }
        });
    } else {
        utils.hideElement(rentalHoursContainer);
        rentalHoursSelect.required = false;
        
        if (dropStopsWrapper) utils.showElement(dropStopsWrapper);
        if (dropStops[0] && dropStops[0].selectEl && pickupSelect.value) {
            dropStops[0].selectEl.required = true;
        }
    }

    toggleCustomAddressFields();
    toggleMapVisibility();
}

// Restricts calendar inputs to require minimum 2 hours lead scheduling time
function restrictDateInputs() {
    const today = new Date();
    // Enforce tomorrow if time boundaries are met, or set minimum to today
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    pickupDate.min = `${yyyy}-${mm}-${dd}`;
}

// Populate the pickup time select dropdown with 30-minute intervals
function populateTimeDropdown() {
    if (!pickupTime) return;
    pickupTime.innerHTML = `<option value="" disabled selected>Select Pickup Time</option>`;
    
    for (let hour = 0; hour < 24; hour++) {
        for (let min of [0, 30]) {
            const h24 = String(hour).padStart(2, '0');
            const m = String(min).padStart(2, '0');
            const timeVal = `${h24}:${m}`;
            
            // Format 12-hour display string
            const period = hour >= 12 ? "PM" : "AM";
            const h12 = hour % 12 === 0 ? 12 : hour % 12;
            const displayTime = `${h12}:${m} ${period}`;
            
            const opt = document.createElement("option");
            opt.value = timeVal;
            opt.textContent = displayTime;
            pickupTime.appendChild(opt);
        }
    }
}

// Binds native calendar overlay trigger on input click & focus for extreme reliability
function setupDatepickerTrigger() {
    if (!pickupDate) return;
    
    const triggerPicker = () => {
        try {
            pickupDate.showPicker();
        } catch (e) {
            console.warn("showPicker not supported on this browser:", e);
        }
    };
    
    pickupDate.addEventListener("click", triggerPicker);
    pickupDate.addEventListener("focus", triggerPicker);
}

// Global loader controllers
function showLoader(msg) {
    bookingLoaderText.textContent = msg;
    utils.showElement(bookingLoader);
    utils.hideElement(panelStep1);
    utils.hideElement(panelStep2);
    utils.hideElement(panelStep3);
    utils.hideElement(bookingAlert);
}

function hideLoader(targetPanel) {
    utils.hideElement(bookingLoader);
    utils.showElement(targetPanel);
}

// Form Step 1 Submission: pricing calculations and overbooking verification
async function handleStep1Submit(e) {
    e.preventDefault();
    utils.hideElement(bookingAlert);

    const pickup = pickupSelect.value;
    const dateVal = pickupDate.value;
    const timeVal = pickupTime.value;
    const category = document.querySelector('input[name="ride-category"]:checked').value;
    const days = 1;

    // Validate 2-hour scheduling constraint
    const now = new Date();
    const selectedDatetime = new Date(`${dateVal}T${timeVal}`);
    const timeDifferenceMs = selectedDatetime - now;
    const timeDifferenceHours = timeDifferenceMs / (1000 * 60 * 60);

    if (timeDifferenceHours < 2) {
        utils.showAlert(bookingAlert, "Scheduling Warning: All rides must be booked at least 2 hours in advance.");
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    // Resolve Pickup coordinates and name
    let pickupCoords = null;
    let resolvedPickupName = pickup;
    const isPickupCustom = (pickup === "Custom Location");

    if (isPickupCustom) {
        const customText = customPickupAddress.value.trim();
        if (!customText) {
            utils.showAlert(bookingAlert, "Please type a custom pickup address.");
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }
        resolvedPickupName = customText;
        pickupCoords = customPickupCoords || await geocodeAddress(customText);
        if (pickupCoords) {
            customPickupCoords = pickupCoords;
        }
    } else {
        const pickupLoc = dbLocations.find(l => l.name === pickup);
        if (pickupLoc) {
            pickupCoords = [pickupLoc.lat, pickupLoc.lng];
        }
    }

    // Resolve all drop stops
    const stopsData = getDropStopsData();
    let resolvedDropNames = [];
    let dropWaypoints = [];
    let isAnyDropCustom = false;

    if (category === "rental") {
        resolvedDropNames = ["Rental Service (No Drop)"];
    } else {
        if (stopsData.length === 0 || !stopsData[0].value) {
            utils.showAlert(bookingAlert, "Please select at least one destination/drop location.");
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }

        for (let i = 0; i < stopsData.length; i++) {
            const stop = stopsData[i];
            if (!stop.value) {
                utils.showAlert(bookingAlert, `Please select a destination for Stop ${i + 1}.`);
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }

            if (stop.isCustom) {
                isAnyDropCustom = true;
                if (!stop.customText) {
                    utils.showAlert(bookingAlert, `Please type an address for custom Stop ${i + 1}.`);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    return;
                }
                const resolvedCoords = stop.coords || await geocodeAddress(stop.customText);
                if (resolvedCoords) {
                    const stopObj = dropStops.find(s => s.id === stop.id);
                    if (stopObj) stopObj.customCoords = resolvedCoords;
                    dropWaypoints.push(resolvedCoords);
                }
                resolvedDropNames.push(stop.customText);
            } else {
                if (stop.coords) {
                    dropWaypoints.push(stop.coords);
                }
                resolvedDropNames.push(stop.value);
            }
        }
    }

    const isCustomBooking = isPickupCustom || isAnyDropCustom;
    const isMultiHop = resolvedDropNames.length > 1;

    showLoader("Querying fleet inventory & calculating rates...");

    let distanceKm = 0;
    let polyline = null;
    const allWaypoints = [];
    if (pickupCoords) allWaypoints.push(pickupCoords);
    allWaypoints.push(...dropWaypoints);

    if (category === "rental") {
        distanceKm = 0;
        polyline = null;
    } else {
        if (allWaypoints.length >= 2) {
            try {
                // Query OSRM multi-waypoint route
                const routeData = await fetchOSRMRoute(allWaypoints);
                distanceKm = Math.round(routeData.distance / 1000) || 1;
                const coords = routeData.geometry.coordinates; // array of [lng, lat]
                polyline = coords.map(coord => [coord[1], coord[0]]); // convert to [lat, lng]
            } catch (err) {
                console.warn("Routing API failed, using fallback metrics:", err.message);
                // Fallback to Haversine distance sum
                distanceKm = getHaversineRouteDistance(allWaypoints);
                polyline = allWaypoints; // Straight-line polyline fallback
            }
        }
    }

    // Check if flat metrics are applicable (only if SINGLE drop, NOT custom, and flat fare match exists in DB)
    let metrics = null;
    if (category !== "rental" && !isCustomBooking && !isMultiHop) {
        const primaryDrop = stopsData[0]?.value;
        try {
            const response = await fetch(`${API_BASE}/flat-fares`);
            if (response.ok) {
                const flatFares = await response.json();
                const matched = flatFares.find(
                    f => f.pickup_name === pickup && f.drop_name === primaryDrop
                );
                if (matched) {
                    metrics = {
                        km: matched.km || distanceKm,
                        base_fare_compact: matched.fares.compact,
                        base_fare_premium: matched.fares.premium,
                        base_fare_suv: matched.fares.suv,
                        base_fare_muv: matched.fares.muv
                    };
                }
            }
        } catch (err) {
            console.warn("Flat fares query failed, falling back to static/dynamic calculation:", err);
            metrics = getRouteMetrics(pickup, primaryDrop);
        }
    }

    // Save configuration parameters globally
    const tripTypeVal = document.querySelector('input[name="trip-type"]:checked').value;
    const finalDropName = resolvedDropNames[resolvedDropNames.length - 1] || "";
    
    currentRouteData = {
        pickup: resolvedPickupName,
        drop: finalDropName,
        drop_locations: resolvedDropNames,
        dateString: dateVal,
        timeString: timeVal,
        category: category,
        tripType: tripTypeVal,
        days: days,
        hours: category === "rental" ? parseInt(rentalHoursSelect.value) : 0,
        km: category === "rental" ? 0 : (metrics ? metrics.km : distanceKm),
        flatMetrics: metrics,
        pickupCoords: pickupCoords,
        dropCoords: dropWaypoints[dropWaypoints.length - 1] || null,
        waypoints: allWaypoints,
        polyline: polyline,
        isCustomBooking: isCustomBooking,
        isMultiHop: isMultiHop
    };

    // Update Step 2 badge distance total
    if (isMultiHop) {
        routeKmBadge.textContent = `Estimated: ${currentRouteData.km} km (${resolvedDropNames.length} Stops)`;
    } else if (isCustomBooking) {
        routeKmBadge.textContent = `Estimated: ${currentRouteData.km} km (Custom Route)`;
    } else {
        routeKmBadge.textContent = `Estimated: ${currentRouteData.km} km`;
    }

    console.log("[UAT-1] Distance Calculation Results -> Category:", category, "Resolved KM:", currentRouteData.km, "Stops:", resolvedDropNames);

    // Validation for route distance on point-to-point rides
    if (category !== "rental" && (!currentRouteData.km || currentRouteData.km <= 0)) {
        console.warn("[UAT-1] Invalid distance detected. Blocking checkout progress.");
        hideLoader(panelStep1);
        const waText = `Hi! I was trying to book a cab on the website, but the location system was unable to resolve my route: ${resolvedPickupName} to ${resolvedDropName}. Please help me book manually.`;
        const waUrl = `https://wa.me/918981538038?text=${encodeURIComponent(waText)}`;
        utils.showAlert(bookingAlert, `
            <div class="flex flex-col items-center gap-3 p-2 text-center">
                <span class="text-sm font-bold text-rose-400">⚠️ Location Resolution Error</span>
                <p class="text-xs text-slate-300">We are experiencing a connection issue with our routing system and cannot determine the distance automatically for: <br><strong class="text-white">${resolvedPickupName} ➔ ${resolvedDropName}</strong></p>
                <a href="${waUrl}" target="_blank" class="mt-2 bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-4 py-2.5 rounded-xl transition-all inline-flex items-center gap-2 text-xs shadow-md">
                    💬 Book Manually on WhatsApp
                </a>
            </div>
        `, "error");
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
    }

    // Process rates and time-aware inventory availability check for each category (Compact, Premium, SUV, MUV)
    try {
        const ratesResponse = await bookingService.fetchRates();
        const activeRates = ratesResponse.rates;
        activeRatesVersionId = ratesResponse.version_id;
        const tiers = ["compact", "premium", "suv", "muv"];
        
        for (const tier of tiers) {
            const card = document.querySelector(`.car-card[data-tier="${tier}"]`);
            const fareDisplay = card.querySelector(".car-fare-display");
            const soldOutOverlay = card.querySelector(".sold-out-overlay");

            // Calculate fare dynamically
            const fare = bookingService.calculateFare(category, currentRouteData.km, days, tier, metrics, currentRouteData.hours, activeRates, currentRouteData.timeString);
            
            if (isCustomBooking) {
                fareDisplay.innerHTML = `₹${fare.toLocaleString("en-IN")}<span class="block text-[10px] text-slate-500 font-normal">Base Rate</span>`;
            } else {
                fareDisplay.textContent = `₹${fare.toLocaleString("en-IN")}`;
            }
            card.dataset.computedFare = fare;

            // Overbooking inventory check
            const isAvailable = await bookingService.checkAvailability(tier, dateVal);
            
            if (isAvailable) {
                utils.hideElement(soldOutOverlay);
                card.classList.remove("opacity-40", "pointer-events-none");
            } else {
                utils.showElement(soldOutOverlay);
                card.classList.add("opacity-40", "pointer-events-none");
                card.classList.remove("selected-card");
            }
        }

        // Navigate visual steps to Step 2
        hideLoader(panelStep2);
        updateProgressSteps(2);
    } catch (err) {
        hideLoader(panelStep1);
        utils.showAlert(bookingAlert, "Error fetching rates: " + err.message);
    }
}

// Binds clicks to the vehicle selection cards
function setupCarSelection() {
    carCards.forEach(card => {
        card.addEventListener("click", () => {
            // Prevent clicks on inactive/sold-out cards
            if (card.classList.contains("pointer-events-none")) return;

            // Remove highlighted states from other cards
            carCards.forEach(c => c.classList.remove("selected-card"));
            
            // Add highlighted active state to selected card
            card.classList.add("selected-card");

            selectedVehicleTier = card.dataset.tier;
            selectedVehicleFare = parseInt(card.dataset.computedFare) || 0;

            // Enable submit step button
            btnSubmitStep2.disabled = false;
        });
    });
}

// Progress Dot state coordinators
function updateProgressSteps(step) {
    if (step === 1) {
        bookingProgressBar.style.width = "0%";
        
        stepDot2.className = "w-8 h-8 rounded-full bg-slate-800 text-slate-400 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300";
        stepText2.className = "text-xs font-semibold text-slate-500 mt-2";
        
        stepDot3.className = "w-8 h-8 rounded-full bg-slate-800 text-slate-400 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300";
        stepText3.className = "text-xs font-semibold text-slate-500 mt-2";
    } 
    else if (step === 2) {
        bookingProgressBar.style.width = "50%";
        
        stepDot2.className = "w-8 h-8 rounded-full bg-amber-500 text-slate-950 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300 ring-4 ring-amber-500/20";
        stepText2.className = "text-xs font-semibold text-amber-500 mt-2";
        
        stepDot3.className = "w-8 h-8 rounded-full bg-slate-800 text-slate-400 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300";
        stepText3.className = "text-xs font-semibold text-slate-500 mt-2";
    } 
    else if (step === 3) {
        bookingProgressBar.style.width = "100%";
        
        stepDot2.className = "w-8 h-8 rounded-full bg-amber-500 text-slate-950 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300 ring-4 ring-amber-500/20";
        stepText2.className = "text-xs font-semibold text-amber-500 mt-2";
        
        stepDot3.className = "w-8 h-8 rounded-full bg-emerald-500 text-slate-950 font-bold flex items-center justify-center text-sm shadow-md transition-all duration-300 ring-4 ring-emerald-500/20";
        stepText3.className = "text-xs font-semibold text-emerald-500 mt-2";
    }
}

// Navigates backwards
function navigateBackTo1() {
    utils.hideElement(bookingAlert);
    utils.hideElement(panelStep2);
    utils.showElement(panelStep1);
    updateProgressSteps(1);
    // Reset selection triggers
    btnSubmitStep2.disabled = true;
    carCards.forEach(c => c.classList.remove("selected-card"));
}

function navigateBackTo2() {
    utils.hideElement(bookingAlert);
    utils.hideElement(panelStep3);
    utils.showElement(panelStep2);
    updateProgressSteps(2);
}

async function loadVisiblePromoChips() {
    utils.hideElement(availableOffersContainer);
    offersChipsList.innerHTML = "";
    
    try {
        const promos = await bookingService.fetchVisiblePromos();
        // Filter by eligibility (estimated base fare >= min threshold)
        const eligiblePromos = promos.filter(p => selectedVehicleFare >= (parseFloat(p.min_fare_threshold) || 0));
        
        if (eligiblePromos.length > 0) {
            eligiblePromos.forEach(p => {
                const btn = document.createElement("button");
                btn.type = "button";
                // Glassmorphic chip styling
                btn.className = "bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 text-amber-400 hover:text-amber-300 font-bold px-3 py-1.5 rounded-xl text-xs transition-all duration-200 transform active:scale-95 cursor-pointer flex items-center gap-1.5";
                
                const typeLabel = p.discount_type === "percentage" ? `${p.discount_value}%` : `₹${p.discount_value}`;
                btn.textContent = `${p.code} (Save ${typeLabel})`;
                
                btn.addEventListener("click", () => {
                    promoCodeInput.value = p.code;
                    handleApplyPromo();
                });
                
                offersChipsList.appendChild(btn);
            });
            utils.showElement(availableOffersContainer);
        }
    } catch (err) {
        console.error("Failed to load visible promo chips:", err);
    }
}

// Render transparent itemized calculation breakdown for Rider Checkout
function renderRiderDetailedFareBreakdown(breakdown, discountVal = 0, promoCode = "") {
    if (!fareBreakdownContent || !breakdown) return;
    
    const params = breakdown.params || {};
    const cfg = params.config || {};
    const globalCfg = params.global_config || {};
    const category = currentRouteData.category || "local";
    const tier = selectedVehicleTier || "compact";
    const tierNames = { compact: "Sedan / Compact", premium: "Premium Sedan", suv: "SUV (Ertiga / Innova)", muv: "MUV (Innova Crysta)" };
    const tierLabel = tierNames[tier] || (tier ? tier.toUpperCase() : "");
    const categoryNames = { local: "Local City Ride", rental: "Hourly Rental", outstation: "Outstation", intercity: "Intercity" };
    const categoryLabel = categoryNames[category] || (category ? category.toUpperCase() : "");
    const tripTypeLabel = currentRouteData.tripType === "round_trip" ? "Round-Trip" : "One-Way";
    const isNight = !!params.night_applies;
    
    // Construct param badges
    const paramBadges = [];
    if (category === "rental") {
        const hrs = params.actual_hours || currentRouteData.hours || 1;
        paramBadges.push({ label: "Rental Time", val: `${hrs} Hour(s)` });
        paramBadges.push({ label: "Base Package", val: `${cfg.included_hours || 5}h / ${cfg.included_km || 50}km` });
        paramBadges.push({ label: "Extra Hr Rate", val: `₹${cfg.extra_hour_rate || 0}/hr` });
        paramBadges.push({ label: "Extra Km Rate", val: `₹${cfg.extra_km_rate || 0}/km` });
    } else if (category === "outstation" || category === "intercity") {
        const roundTripDist = Math.round((currentRouteData.km || 0) * 2);
        paramBadges.push({ label: "One-Way Est.", val: `${currentRouteData.km || 0} km` });
        paramBadges.push({ label: "Round-Trip Dist.", val: `${roundTripDist} km` });
        paramBadges.push({ label: "Min Km/Day", val: `${cfg.min_km_per_day || 250} km` });
        paramBadges.push({ label: "Per Km Rate", val: `₹${cfg.rate_per_km || 0}/km` });
    } else {
        paramBadges.push({ label: "Estimated Route", val: `${currentRouteData.km || 0} km` });
        paramBadges.push({ label: "Base Package", val: `First ${params.local_included_km || 10} km` });
        paramBadges.push({ label: "Extra Km Rate", val: `₹${cfg.extra_km_rate || 0}/km` });
        paramBadges.push({ label: "Night Rate", val: `₹${cfg.night_charge || 0}` });
    }

    // Itemized Line Items
    const lineItems = [];
    if (category === "rental") {
        lineItems.push({
            name: `Base Rental Package (${cfg.included_hours || 5}h / ${cfg.included_km || 50}km)`,
            subtext: `Includes initial ${cfg.included_hours || 5} hours and ${cfg.included_km || 50} km drive`,
            amount: breakdown.base_fare
        });
        if (breakdown.extra_hour_charge > 0) {
            const extraHrs = Math.max(0, (params.actual_hours || currentRouteData.hours || 1) - (parseFloat(cfg.included_hours) || 5));
            lineItems.push({
                name: `Extra Duration (${extraHrs} hr × ₹${cfg.extra_hour_rate || 0}/hr)`,
                subtext: `Hours beyond base package of ${cfg.included_hours || 5}h`,
                amount: breakdown.extra_hour_charge
            });
        }
        if (breakdown.extra_km_charge > 0) {
            lineItems.push({
                name: `Extra Distance Charge`,
                subtext: `Distance over included ${cfg.included_km || 50} km`,
                amount: breakdown.extra_km_charge
            });
        }
        if (breakdown.night_charge > 0) {
            lineItems.push({
                name: `Night Surcharge`,
                subtext: `Pickup scheduled between ${globalCfg.night_charge_start || '23:59'} - ${globalCfg.night_charge_end || '06:00'}`,
                amount: breakdown.night_charge
            });
        }
    } else if (category === "outstation" || category === "intercity") {
        const roundTripDist = Math.round((currentRouteData.km || 0) * 2);
        const minKm = parseFloat(cfg.min_km_per_day) || 250;
        const billedDist = Math.max(roundTripDist, minKm);
        lineItems.push({
            name: `Distance Charge (${billedDist} km × ₹${cfg.rate_per_km || 0}/km)`,
            subtext: roundTripDist < minKm ? `Billed at min daily threshold of ${minKm} km (Round-trip: ${roundTripDist} km)` : `Round-trip distance charge (${currentRouteData.km} km × 2)`,
            amount: breakdown.base_fare
        });
        if (breakdown.driver_allowance > 0) {
            lineItems.push({
                name: `Driver Day Allowance`,
                subtext: `Standard driver allowance per trip day`,
                amount: breakdown.driver_allowance
            });
        }
        if (breakdown.night_halt > 0) {
            lineItems.push({
                name: `Night Halt Charge`,
                subtext: `Overnight vehicle stay surcharge`,
                amount: breakdown.night_halt
            });
        }
    } else {
        const localInclKm = params.local_included_km || 10;
        lineItems.push({
            name: `Base Fare (Includes first ${localInclKm} km)`,
            subtext: `Base flag-down fee for ${tierLabel}`,
            amount: breakdown.base_fare
        });
        if (breakdown.extra_km_charge > 0) {
            const extraKm = Math.max(0, (currentRouteData.km || 0) - localInclKm);
            lineItems.push({
                name: `Extra Distance Charge (${extraKm} km × ₹${cfg.extra_km_rate || 0}/km)`,
                subtext: `Distance beyond base ${localInclKm} km`,
                amount: breakdown.extra_km_charge
            });
        }
        if (breakdown.night_charge > 0) {
            lineItems.push({
                name: `Night Surcharge`,
                subtext: `Pickup scheduled between ${globalCfg.night_charge_start || '23:59'} - ${globalCfg.night_charge_end || '06:00'}`,
                amount: breakdown.night_charge
            });
        }
    }

    const subtotal = breakdown.total || selectedVehicleFare;
    const finalFare = Math.max(0, subtotal - discountVal);

    fareBreakdownContent.innerHTML = `
        <div class="space-y-3 bg-slate-950/60 border border-slate-800/80 rounded-2xl p-3.5">
            <!-- Header Banner -->
            <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                <div>
                    <span class="text-[10px] uppercase font-bold text-amber-500 tracking-wider block">Pricing Calculation Summary</span>
                    <span class="text-xs font-semibold text-white">${categoryLabel} • ${tierLabel}</span>
                </div>
                <div class="flex items-center gap-1.5">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-amber-400 border border-slate-700">${tripTypeLabel}</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${isNight ? 'bg-indigo-950 text-indigo-300 border border-indigo-700' : 'bg-slate-800 text-slate-300 border border-slate-700'}">${isNight ? '🌙 Night' : '☀️ Day'}</span>
                </div>
            </div>

            <!-- Parameters Grid -->
            <div>
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">Trip Rate Parameters:</span>
                <div class="grid grid-cols-2 gap-2">
                    ${paramBadges.map(b => `
                        <div class="bg-slate-900/80 border border-slate-800/80 p-2 rounded-xl">
                            <span class="text-[9px] text-slate-400 block truncate">${b.label}</span>
                            <span class="text-xs font-bold text-white block mt-0.5 truncate">${b.val}</span>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Itemized Line Items -->
            <div>
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">Itemized Cost Breakdown:</span>
                <div class="border border-slate-800/80 rounded-xl overflow-hidden divide-y divide-slate-800/60 bg-slate-900/40">
                    ${lineItems.map(item => `
                        <div class="flex justify-between items-center p-2.5">
                            <div class="pr-2">
                                <span class="text-xs font-medium text-slate-200 block">${item.name}</span>
                                ${item.subtext ? `<span class="text-[10px] text-slate-500 block leading-tight mt-0.5">${item.subtext}</span>` : ''}
                            </div>
                            <span class="text-xs font-bold text-white whitespace-nowrap">₹${item.amount.toLocaleString("en-IN")}</span>
                        </div>
                    `).join('')}

                    ${discountVal > 0 ? `
                        <div class="flex justify-between items-center p-2.5 bg-emerald-950/30 text-emerald-400">
                            <div>
                                <span class="text-xs font-medium block">Promo Code Discount (${promoCode})</span>
                                <span class="text-[10px] text-emerald-300/70 block leading-tight mt-0.5">Applied savings</span>
                            </div>
                            <span class="text-xs font-bold whitespace-nowrap">-₹${discountVal.toLocaleString("en-IN")}</span>
                        </div>
                    ` : ''}

                    <div class="flex justify-between items-center p-2.5 bg-amber-500/10 border-t border-amber-500/20">
                        <div>
                            <span class="text-xs font-bold text-amber-400 block uppercase tracking-wide">Final Calculated Fare</span>
                            <span class="text-[10px] text-slate-400 block">Toll & parking extra if applicable</span>
                        </div>
                        <span class="text-sm font-black text-amber-400">₹${finalFare.toLocaleString("en-IN")}/-</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Switches from Step 2 to checkout summary panel (Step 3)
async function navigateToStep3() {
    if (!selectedVehicleTier) return;
    utils.hideElement(bookingAlert);

    // Populate billing values
    summaryPickup.textContent = currentRouteData.pickup;
    
    if (currentRouteData.drop_locations && currentRouteData.drop_locations.length > 1) {
        const totalStops = currentRouteData.drop_locations.length;
        summaryDrop.innerHTML = `
            <div class="space-y-1 text-right">
                ${currentRouteData.drop_locations.map((loc, idx) => `
                    <div class="flex items-center justify-end gap-1.5 text-xs">
                        <span class="text-amber-500 font-bold">${idx === totalStops - 1 ? '🏁 Drop:' : `📍 Stop ${idx + 1}:`}</span>
                        <span class="font-bold text-white">${loc}</span>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        summaryDrop.textContent = currentRouteData.drop;
    }

    summaryDatetime.textContent = `${currentRouteData.dateString} at ${currentRouteData.timeString}`;
    const tripTypeLabel = currentRouteData.tripType === "round_trip" ? "Round-Trip" : "One-Way";
    summaryCategory.textContent = `${currentRouteData.category.toUpperCase()} (${tripTypeLabel})`;
    summaryTier.textContent = selectedVehicleTier.toUpperCase();
    
    // Set base fare & reset promo state
    if (currentRouteData.isCustomBooking) {
        summaryBaseFare.textContent = `₹${selectedVehicleFare.toLocaleString("en-IN")} (Base Cost)`;
        utils.showElement(customFareNotice);
    } else {
        summaryBaseFare.textContent = `₹${selectedVehicleFare.toLocaleString("en-IN")}`;
        utils.hideElement(customFareNotice);
    }
    
    summaryGrandTotal.textContent = `₹${selectedVehicleFare.toLocaleString("en-IN")}`;
    appliedPromo = null;
    promoCodeInput.value = "";
    utils.hideElement(summaryDiscountRow);
    utils.hideElement(promoStatusMsg);
    promoStatusMsg.className = "text-xs font-semibold text-center hidden";
    promoStatusMsg.textContent = "";

    // Load visible offers for rider selection
    loadVisiblePromoChips();

    if (currentRouteData.category === "rental") {
        summaryDaysRow.firstElementChild.textContent = "Rental Duration";
        summaryDays.textContent = `${currentRouteData.hours} Hour(s)`;
        utils.showElement(summaryDaysRow);
    } else {
        utils.hideElement(summaryDaysRow);
    }

    // Compute and populate detailed fare breakdown
    try {
        const ratesResponse = await bookingService.fetchRates();
        const activeRates = ratesResponse.rates;
        currentBreakdownData = bookingService.calculateFareBreakdown(
            currentRouteData.category,
            currentRouteData.km,
            currentRouteData.days,
            selectedVehicleTier,
            currentRouteData.flatMetrics,
            currentRouteData.hours,
            activeRates,
            currentRouteData.timeString
        );
        renderRiderDetailedFareBreakdown(currentBreakdownData, 0, "");
    } catch (err) {
        console.warn("Could not calculate detailed fare breakdown for rider:", err);
    }

    utils.hideElement(panelStep2);
    utils.showElement(panelStep3);
    updateProgressSteps(3);
}

async function handleApplyPromo() {
    utils.hideElement(promoStatusMsg);
    const code = promoCodeInput.value.trim();
    if (!code) {
        promoStatusMsg.textContent = "Please enter a promo code.";
        promoStatusMsg.className = "text-xs font-semibold text-center mt-2 text-rose-500 block";
        utils.showElement(promoStatusMsg);
        return;
    }
    
    btnApplyPromo.disabled = true;
    btnApplyPromo.textContent = "Applying...";
    
    try {
        const result = await bookingService.verifyPromoCode(code, selectedVehicleFare);
        if (result.valid) {
            appliedPromo = {
                code: result.code,
                discount: result.discount
            };
            
            // Show discount line in billing breakdown
            summaryPromoCodeName.textContent = result.code;
            summaryDiscountAmount.textContent = `-₹${result.discount.toLocaleString("en-IN")}`;
            utils.showElement(summaryDiscountRow);
            
            // Calculate final grand total
            const finalFare = selectedVehicleFare - result.discount;
            summaryGrandTotal.textContent = `₹${finalFare.toLocaleString("en-IN")}`;
            
            // Re-render itemized breakdown with promo discount
            if (currentBreakdownData) {
                renderRiderDetailedFareBreakdown(currentBreakdownData, result.discount, result.code);
            }

            // Show status success message
            promoStatusMsg.textContent = result.message;
            promoStatusMsg.className = "text-xs font-semibold text-center mt-2 text-emerald-500 block";
            utils.showElement(promoStatusMsg);
        } else {
            appliedPromo = null;
            utils.hideElement(summaryDiscountRow);
            summaryGrandTotal.textContent = `₹${selectedVehicleFare.toLocaleString("en-IN")}`;
            
            if (currentBreakdownData) {
                renderRiderDetailedFareBreakdown(currentBreakdownData, 0, "");
            }

            promoStatusMsg.textContent = result.message;
            promoStatusMsg.className = "text-xs font-semibold text-center mt-2 text-rose-500 block";
            utils.showElement(promoStatusMsg);
        }
    } catch (err) {
        console.error("Error applying promo:", err);
        promoStatusMsg.textContent = "Failed to apply promo code.";
        promoStatusMsg.className = "text-xs font-semibold text-center mt-2 text-rose-500 block";
        utils.showElement(promoStatusMsg);
    } finally {
        btnApplyPromo.disabled = false;
        btnApplyPromo.textContent = "Apply";
    }
}

// Final execution loop (saves to Firestore, then opens WhatsApp redirect window)
async function handleFinalConfirm() {
    if (!currentUser || !currentProfile) {
        utils.showAlert(bookingAlert, "Your session has expired. Please reload and log in again.");
        return;
    }

    showLoader("Registering booking & compiling invoice details...");

    try {
        // 1. Fetch secure signed quote from FastAPI backend
        const quote = await bookingService.estimateQuote({
            category: currentRouteData.category,
            pickup: currentRouteData.pickup,
            drop: currentRouteData.drop,
            drop_locations: currentRouteData.drop_locations,
            date_string: currentRouteData.dateString,
            time_string: currentRouteData.timeString,
            days: (currentRouteData.category === "outstation" || currentRouteData.category === "intercity") ? currentRouteData.days : null,
            hours: currentRouteData.category === "rental" ? currentRouteData.hours : null,
            km: currentRouteData.km,
            vehicle_tier: selectedVehicleTier,
            promo_code: appliedPromo ? appliedPromo.code : null
        });

        // 2. Assemble secure booking create payload
        const bookingPayload = {
            trip_details: {
                ride_type: currentRouteData.category,
                trip_type: currentRouteData.tripType,
                pickup_location: currentRouteData.pickup,
                drop_location: currentRouteData.drop,
                drop_locations: currentRouteData.drop_locations || [currentRouteData.drop],
                pickup_date: currentRouteData.dateString,
                pickup_time: currentRouteData.timeString,
                outstation_days: (currentRouteData.category === "outstation" || currentRouteData.category === "intercity") ? currentRouteData.days : null,
                rental_hours: currentRouteData.category === "rental" ? currentRouteData.hours : null,
                pickup_coords: currentRouteData.pickupCoords || null,
                drop_coords: currentRouteData.dropCoords || null,
                route_polyline: currentRouteData.polyline ? JSON.stringify(currentRouteData.polyline) : null
            },
            fare_details: {
                vehicle_tier: selectedVehicleTier,
                estimated_km: currentRouteData.km,
                base_fare: quote.base_fare,
                discount_amount: quote.discount_amount,
                promo_code: quote.promo_code,
                estimated_fare: quote.estimated_fare,
                rates_version_id: activeRatesVersionId,
                breakdown: quote.breakdown
            },
            quote_signature: quote.signature,
            quote_id: quote.quote_id,
            expires_at: quote.expires_at
        };

        // 3. Commit record to Cloud Firestore DB via Backend
        const bookingId = await bookingService.createBooking(bookingPayload);
        bookingPayload.booking_id = bookingId;

        // Success Alert and redirection
        utils.hideElement(bookingLoader);
        utils.showElement(panelStep3);
        utils.showAlert(bookingAlert, "Booking successful! Your ride has been registered and is pending approval.", "success");

        // Smoothly route rider back to primary homepage landing
        setTimeout(() => {
            window.location.href = "../../index.html";
        }, 3000);
    } catch (error) {
        hideLoader(panelStep3);
        utils.showAlert(bookingAlert, "Booking transaction failed: " + error.message);
    }
}
