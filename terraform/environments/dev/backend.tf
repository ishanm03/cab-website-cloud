# terraform/environments/dev/backend.tf

terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Comment out this GCS block for local state. Enable in production CI/CD.
# terraform {
#   backend "gcs" {
#     bucket = "sethcabs-tfstate-dev"
#     prefix = "terraform/state"
#   }
# }
