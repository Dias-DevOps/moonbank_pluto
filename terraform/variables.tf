variable "gcp_region" {
    description = "The GCP region to create resources in"
    type = string
}

variable "project_id" {
    description = "Project ID where all the resources will be deployed"
    type = string
}

variable "gcp_apis" {
    type = list(string)
    default = [ 
        "serviceusage.googleapis.com",
        "compute.googleapis.com",
        "iam.googleapis.com",
        "bigquery.googleapis.com",
        "storage.googleapis.com",
        "pubsub.googleapis.com",
        "cloudfunctions.googleapis.com",
        "eventarc.googleapis.com",
        "cloudasset.googleapis.com",
        "cloudresourcemanager.googleapis.com",
        "cloudbuild.googleapis.com",
        "run.googleapis.com"
    ]
}

variable "bq_dataset" {
    description = "BigQuery dataset"
    type = string
}

variable "bq_table" {
    description = "BigQuery table"
    type =  string
}

variable "topic" {
    description = "PubSub topic"
    type = string  
}

variable "subscription" {
    description = "PubSub subscription"
    type = string
}

variable "function" {
    description = "Cloud function name"
    type = string
}
