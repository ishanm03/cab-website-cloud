# terraform/modules/cloud_run/main.tf

variable "project_id" { type = string }
variable "region" { type = string }
variable "environment" { type = string }
variable "app_name" { type = string }
variable "hmac_quote_secret" { type = string }

# Create Artifact Registry docker repository
resource "google_artifact_registry_repository" "backend_repo" {
  location      = var.region
  repository_id = "${var.app_name}-backend-${var.environment}"
  description   = "Docker repository for ${var.app_name} backend"
  format        = "DOCKER"
}

# Create dedicated service account for Cloud Run backend
resource "google_service_account" "backend_sa" {
  account_id   = "${var.app_name}-backend-${var.environment}-sa"
  display_name = "Service Account for ${var.app_name} Backend on Cloud Run (${var.environment})"
}

# Bind IAM roles for Firestore and Firebase Auth access
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_project_iam_member" "firebase_admin" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Create Secret Manager Secret for HMAC quote validation key
resource "google_secret_manager_secret" "hmac_secret" {
  secret_id = "${var.app_name}-hmac-quote-secret-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "hmac_secret_version" {
  secret      = google_secret_manager_secret.hmac_secret.id
  secret_data = var.hmac_quote_secret
}

resource "google_secret_manager_secret_iam_member" "sa_secret_access" {
  secret_id = google_secret_manager_secret.hmac_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Create Cloud Run V2 service
resource "google_cloud_run_v2_service" "backend_service" {
  name     = "${var.app_name}-backend-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.backend_sa.email

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name = "HMAC_QUOTE_SECRET"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.hmac_secret.secret_id
            version = "latest"
          }
        }
      }
    }

    scaling {
      max_instance_count = 1
      min_instance_count = 0
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
  }
}

# Grant public unauthenticated access
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.backend_service.name
  location = google_cloud_run_v2_service.backend_service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "backend_url" {
  value = google_cloud_run_v2_service.backend_service.uri
}
