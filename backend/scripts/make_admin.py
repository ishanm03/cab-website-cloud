# backend/scripts/make_admin.py
import sys
import os

# Set python path to find 'app' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import firebase_admin
from firebase_admin import auth as firebase_auth
from app.core import firebase  # Triggers global init code

def make_admin(email: str):
    email_clean = email.strip()
    if not email_clean:
        print("Error: Email address cannot be empty.")
        sys.exit(1)
        
    print(f"SethCabs CLI: Searching for user with email: '{email_clean}'...")
    try:
        user = firebase_auth.get_user_by_email(email_clean)
        uid = user.uid
        print(f"SethCabs CLI: Found user: '{user.display_name or 'No Display Name'}' (UID: {uid})")
        
        # Merge existing custom claims or set new admin claim
        existing_claims = user.custom_claims or {}
        new_claims = {**existing_claims, "admin": True}
        
        firebase_auth.set_custom_user_claims(uid, new_claims)
        print(f"SethCabs CLI: Successfully set custom claims {new_claims} on user UID: {uid}")
        print("Note: The user will need to refresh their authentication ID token for changes to apply.")
    except firebase_auth.UserNotFoundError:
        print(f"Error: No user found with email: '{email_clean}'. Please verify the email in your Firebase Console.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to set custom claims: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 make_admin.py <user_email>")
        sys.exit(1)
        
    target_email = sys.argv[1]
    make_admin(target_email)
