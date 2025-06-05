terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "6.37.0"
    }
  }
}

provider "google" {
  project = var.project_id
  billing_project = var.project_id
  region = var.gcp_region
  user_project_override = true
}