// modules/shared/locationClassifier.js

/**
 * Known Predefined/Landmark Zones in Kolkata & Howrah Metropolitan Region
 */
const LOCAL_KOLKATA_HOWRAH_NODES = [
    "howrah station", "airport", "esplanade", "salt lake", "kolkata", "howrah", 
    "sealdah", "park street", "new town", "rajarhat", "dum dum", "behala", 
    "garia", "ballygunge", "jadavpur", "alipore", "shibpur", "santragachi", 
    "belur", "bally", "uttarpara", "baranagar", "kamarkundu", "serampore", 
    "rishra", "konnagar", "chinsurah", "chandannagar", "barasat", "barrackpore",
    "shyambazar", "khidirpur", "tollygunge", "kasba", "ruby", "ecospace", "sector v"
];

/**
 * Known Towns/Cities Within West Bengal (Outside Kolkata & Howrah)
 */
const INTERCITY_WB_NODES = [
    "digha", "mayapur", "shantiniketan", "mandarmani", "tarapith", "siliguri", 
    "darjeeling", "kalimpong", "kurseong", "durgapur", "asansol", "bardhaman", 
    "burdwan", "haldia", "kharagpur", "midnapore", "medinipur", "purulia", 
    "bankura", "malda", "murshidabad", "baharampur", "berhampore", "raiganj", 
    "balurghat", "cooch behar", "alipurduar", "jalpaiguri", "bolpur", "bakkhali", 
    "sundarbans", "gadiara", "mukutmanipur", "jhargram", "krishnanagar", "navadvip", 
    "nabadwip", "santipur", "kalyani", "ranaghat", "diamond harbour", "canning", 
    "kakdwip", "basirhat", "bongaon", "habra", "tamluk", "kolaghat", "mecheda",
    "tajpur", "shankarpur", "farakka", "jangipur", "katwa", "kalna", "tarakeswar"
];

/**
 * Known Outstation Nodes/Cities/States Outside West Bengal
 */
const OUTSTATION_OUTSIDE_WB_NODES = [
    "puri", "bhubaneswar", "cuttack", "ranchi", "jamshedpur", "tatanagar", 
    "dhanbad", "bokaro", "deoghar", "patna", "gaya", "bhagalpur", "muzaffarpur", 
    "guwahati", "gangtok", "kathmandu", "varanasi", "delhi", "mumbai", "odisha", 
    "orissa", "jharkhand", "bihar", "assam", "sikkim", "uttar pradesh", "chhattisgarh", 
    "raipur", "bilaspur", "rourkela", "sambalpur", "balasore", "hazaribagh"
];

/**
 * Classifies a destination into 'local', 'intercity', or 'outstation'
 * @param {string} destinationName - Name of selected node or 'Custom Location'
 * @param {Array<number>|null} coordinates - [lat, lng] array
 * @param {string} [customAddressText] - Text entered in custom address field
 * @returns {"local" | "intercity" | "outstation"}
 */
export function classifyDestination(destinationName, coordinates = null, customAddressText = "") {
    const rawTarget = ((destinationName === "Custom Location" ? customAddressText : destinationName) || "").toLowerCase().trim();
    
    // 1. Explicit keyword checks for Outstation (Outside WB)
    for (const node of OUTSTATION_OUTSIDE_WB_NODES) {
        if (rawTarget.includes(node)) {
            return "outstation";
        }
    }

    // 2. Explicit keyword checks for Intercity (Within WB)
    for (const node of INTERCITY_WB_NODES) {
        if (rawTarget.includes(node)) {
            return "intercity";
        }
    }

    // 3. Explicit keyword checks for Local (Kolkata & Howrah)
    for (const node of LOCAL_KOLKATA_HOWRAH_NODES) {
        if (rawTarget.includes(node)) {
            return "local";
        }
    }

    // 4. Coordinates Bounding Box Analysis
    if (coordinates && Array.isArray(coordinates) && coordinates.length >= 2) {
        const lat = parseFloat(coordinates[0]);
        const lng = parseFloat(coordinates[1]);

        if (!isNaN(lat) && !isNaN(lng)) {
            // A. Check Kolkata & Howrah Metropolitan Bounding Box
            // Approx: Lat 22.35 to 22.82, Lng 88.15 to 88.60
            if (lat >= 22.35 && lat <= 22.82 && lng >= 88.15 && lng <= 88.60) {
                return "local";
            }

            // B. Check West Bengal State Bounding Box
            // Approx: Lat 21.50 to 27.35, Lng 85.80 to 89.95
            if (lat >= 21.50 && lat <= 27.35 && lng >= 85.80 && lng <= 89.95) {
                return "intercity";
            }

            // C. Outside West Bengal Boundary
            return "outstation";
        }
    }

    // 5. Text heuristics for state identifiers in address
    if (rawTarget.includes("west bengal") || rawTarget.includes("wb") || rawTarget.includes("w.b.")) {
        return "intercity";
    }

    // Default fallback to local if within standard Kolkata radius
    return "local";
}
