# terraform/environments/dev/backend.tf

terraform {
  backend "gcs" {
    bucket = "ishancabproject-tfstate-dev"
    prefix = "terraform/state"
  }
}
