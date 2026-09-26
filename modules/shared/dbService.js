// modules/shared/dbService.js

import { auth, db } from "./firebase.js";
import { 
    doc, 
    setDoc, 
    getDoc, 
    serverTimestamp 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
    ? "http://localhost:8000/api/v1" 
    : "/api/v1";

/**
 * Service to manage all Firestore database interactions for SethCabs
 */
const dbService = {
    /**
     * Helper to prepare HTTP headers with JWT token
     */
    async getHeaders() {
        const headers = {
            "Content-Type": "application/json"
        };
        if (auth && auth.currentUser) {
            try {
                const token = await auth.currentUser.getIdToken();
                headers["Authorization"] = `Bearer ${token}`;
            } catch (err) {
                console.error("dbService: Failed to fetch ID token:", err);
            }
        }
        return headers;
    },

    /**
     * Creates or updates a customer profile with audit records
     * @param {string} uid - Unique Firebase Authentication user ID
     * @param {object} profileData - Customer details (name, city, phone, email, auth_provider)
     */
    async saveUserProfile(uid, profileData) {
        if (uid === "admin_poc_uid") {
            console.log("dbService: Admin PoC user profile bypassed API call.");
            return { uid, ...profileData, status: "active" };
        }
        
        let clientSaveSuccess = false;
        let clientPayload = null;

        // 1. Direct Firestore write via Client SDK (instant & reliable)
        if (db) {
            try {
                const userDocRef = doc(db, "users", uid);
                const userSnapshot = await getDoc(userDocRef);
                
                if (!userSnapshot.exists()) {
                    clientPayload = {
                        uid: uid,
                        name: profileData.name || "",
                        city: profileData.city || "Kolkata",
                        phone: profileData.phone || "",
                        email: profileData.email || (auth?.currentUser?.email || null),
                        auth_provider: profileData.auth_provider || "google",
                        status: "active",
                        creation_ts: serverTimestamp(),
                        updated_ts: serverTimestamp()
                    };
                    await setDoc(userDocRef, clientPayload);
                    console.log("dbService: Successfully created new user profile in Firestore directly:", uid);
                } else {
                    const updatePayload = {
                        updated_ts: serverTimestamp()
                    };
                    if (profileData.name) updatePayload.name = profileData.name;
                    if (profileData.city) updatePayload.city = profileData.city;
                    if (profileData.phone) updatePayload.phone = profileData.phone;
                    if (profileData.email) updatePayload.email = profileData.email;
                    if (profileData.auth_provider) updatePayload.auth_provider = profileData.auth_provider;

                    await setDoc(userDocRef, updatePayload, { merge: true });
                    clientPayload = { ...userSnapshot.data(), ...updatePayload };
                    console.log("dbService: Successfully updated existing user profile in Firestore directly:", uid);
                }
                clientSaveSuccess = true;
            } catch (fsErr) {
                console.warn("dbService: Direct Firestore write encountered notice:", fsErr);
            }
        }

        // 2. Sync to Backend API if available
        try {
            const headers = await this.getHeaders();
            const response = await fetch(`${API_BASE}/me/profile`, {
                method: "PUT",
                headers: headers,
                body: JSON.stringify({
                    name: profileData.name || undefined,
                    city: profileData.city || undefined,
                    phone: profileData.phone || undefined,
                    email: profileData.email || undefined,
                    auth_provider: profileData.auth_provider || undefined
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log("dbService: Successfully synced user profile via API:", uid);
                return result;
            }
        } catch (apiErr) {
            console.warn("dbService: Backend API sync bypassed (local/offline mode):", apiErr.message);
        }

        if (clientSaveSuccess && clientPayload) {
            return clientPayload;
        }

        return { uid, ...profileData, status: "active" };
    },

    /**
     * Fetches user profile data from Firestore
     * @param {string} uid - Unique Firebase Authentication user ID
     * @returns {Promise<object|null>} Profile data or null
     */
    async getUserProfile(uid) {
        if (uid === "admin_poc_uid") {
            return {
                uid: "admin_poc_uid",
                email: "admin@sethcabs.com",
                name: "Admin Manager",
                phone: "+919999999999",
                status: "active",
                auth_provider: "password"
            };
        }

        // 1. Try Direct Firestore read first
        if (db) {
            try {
                const userDocRef = doc(db, "users", uid);
                const userSnapshot = await getDoc(userDocRef);
                if (userSnapshot.exists()) {
                    const data = userSnapshot.data();
                    console.log("dbService: Found profile in Firestore directly:", uid, data);
                    return data;
                }
            } catch (fsErr) {
                console.warn("dbService: Direct Firestore read notice:", fsErr);
            }
        }

        // 2. Fallback to backend API
        try {
            const headers = await this.getHeaders();
            const response = await fetch(`${API_BASE}/me/profile`, {
                method: "GET",
                headers: headers
            });
            
            if (response.status === 404) {
                return null;
            }
            
            if (response.ok) {
                const result = await response.json();
                return result;
            }
        } catch (error) {
            console.warn("dbService: API get profile bypassed:", error.message);
        }

        return null;
    }
};

export { dbService };

