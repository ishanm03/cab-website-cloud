# terraform/environments/dev/variables.tf

variable "project_id" {
  type        = string
  description = "GCP Project ID to provision resources in"
}

variable "region" {
  type        = string
  default     = "asia-east1"
  description = "Region to deploy resources"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Target deployment environment"
}

variable "app_name" {
  type        = string
  default     = "sethcabs"
  description = "Application prefix for resources"
}

variable "hmac_quote_secret" {
  type        = string
  sensitive   = true
  description = "HMAC quote signing key"
}
