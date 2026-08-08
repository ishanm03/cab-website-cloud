// modules/shared/dbService.js

import { auth } from "./firebase.js";

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
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || errData.error?.message || `HTTP ${response.status} updating profile.`);
            }
            
            const result = await response.json();
            console.log("dbService: Successfully updated user profile via API:", uid);
            return result; // Backend returns the full serialized profile
        } catch (error) {
            console.error("dbService: Error saving user profile via API:", error);
            throw error;
        }
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
        try {
            const headers = await this.getHeaders();
            const response = await fetch(`${API_BASE}/me/profile`, {
                method: "GET",
                headers: headers
            });
            
            if (response.status === 404) {
                return null;
            }
            
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || errData.error?.message || `HTTP ${response.status} fetching profile.`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error("dbService: Error fetching user profile via API:", error);
            throw error;
        }
    }
};

export { dbService };
