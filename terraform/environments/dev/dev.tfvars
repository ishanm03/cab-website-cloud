# terraform/environments/dev/dev.tfvars

project_id        = "ishancabproject"
# Target GCP Region (matches GCS tfstate bucket location)
region            = "asia-east1"
environment       = "dev"
app_name          = "sethcabs"
hmac_quote_secret = "dev_strong_secret_key_change_me_in_prod"
