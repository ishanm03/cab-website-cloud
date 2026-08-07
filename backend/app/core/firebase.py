# backend/app/core/firebase.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings

# Initialize Firebase Admin App globally once
firebase_app = None
db = None

try:
    if not firebase_admin._apps:
        if settings.FIREBASE_SERVICE_ACCOUNT_PATH and os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_PATH):
            print(f"SethCabs Backend: Initializing Firebase Admin SDK via service account key file: {settings.FIREBASE_SERVICE_ACCOUNT_PATH}")
            cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Fallback to Application Default Credentials (ADC) or environmental defaults
            print("SethCabs Backend: Initializing Firebase Admin SDK via default service account credentials.")
            project_id = getattr(settings, "PROJECT_ID", None) or os.getenv("GOOGLE_CLOUD_PROJECT") or "ishancabproject"
            firebase_app = firebase_admin.initialize_app(options={"projectId": project_id})
    else:
        firebase_app = firebase_admin.get_app()
        
    db = firestore.client()
    print("SethCabs Backend: Firebase Admin SDK and Firestore client successfully initialized.")
except Exception as e:
    print(f"SethCabs Backend: WARNING: Failed to initialize Firebase Admin SDK. Backend features requiring database writes will fail. Details: {e}")
    # We do not crash the server startup immediately to allow health checks to function in degraded states.
