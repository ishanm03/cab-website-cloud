# terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
}

module "firebase" {
  source      = "../../modules/firebase"
  project_id  = var.project_id
  environment = var.environment
  app_name    = var.app_name
}

module "cloud_run" {
  source            = "../../modules/cloud_run"
  project_id        = var.project_id
  region            = var.region
  environment       = var.environment
  app_name          = var.app_name
  hmac_quote_secret = var.hmac_quote_secret
}

output "backend_url" {
  value       = module.cloud_run.backend_url
  description = "Target API endpoint for Cloud Run FastAPI"
}
