# terraform/modules/firebase/main.tf

variable "project_id" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }

# Enable needed services
resource "google_project_service" "firebase" {
  project = var.project_id
  service = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"
  disable_on_destroy = false
}


# Register a Web App in Firebase
resource "google_firebase_web_app" "web_app" {
  provider     = google-beta
  project      = var.project_id
  display_name = "${var.app_name}-web-${var.environment}"

  depends_on = [
    google_project_service.firebase
  ]
}
