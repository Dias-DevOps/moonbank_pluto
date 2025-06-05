data "google_project" "project" {
    project_id = var.project_id 
}

resource "google_service_account" "function_sa" {
    account_id   = "function-sa"
    display_name = "Cloud Function SA"

    create_ignore_already_exists = true 
}

resource "google_project_service" "apis" {
    for_each = toset(var.gcp_apis)
    project = var.project_id
    service = each.value
    disable_on_destroy = false
}

resource "google_pubsub_topic_iam_binding" "allow_asset_feed_publish" {
    topic = google_pubsub_topic.topic.name
    role = "roles/pubsub.publisher"
    members = [
        "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudasset.iam.gserviceaccount.com"
    ]

    depends_on = [google_project_service.apis]
}

resource "null_resource" "zip_function_code" {
    provisioner "local-exec" {
        command = <<EOT
        cd ../cloudfunction && zip -r ../function-source.zip .
        EOT
    }
    triggers = {
        code_hash = sha1(join("", fileset("${path.module}/../cloudfunction", "**")))
    }
    }

resource "google_project_iam_member" "function_bq_writer" {
    project = var.project_id
    role = "roles/bigquery.dataEditor"
    member = "serviceAccount:${google_service_account.function_sa.email}"
}

resource "google_storage_bucket" "source-bucket" {
    name = "${var.project_id}-bucket"
    location = "US"
}

resource "google_storage_bucket_object" "object" {
    name = "function-source.zip"
    bucket = google_storage_bucket.source-bucket.name
    source = "../function-source.zip"

    depends_on = [null_resource.zip_function_code]
}


resource "google_bigquery_dataset" "dataset" {
    dataset_id = var.bq_dataset
}

resource "google_bigquery_table" "name" {
    dataset_id = google_bigquery_dataset.dataset.dataset_id
    table_id = var.bq_table
}

resource "google_pubsub_topic" "topic" {
    name = var.topic

    depends_on = [google_project_service.apis]
}

resource "google_pubsub_subscription" "subscription" {
    name = var.subscription
    topic = google_pubsub_topic.topic.id

    depends_on = [google_project_service.apis]
}

resource "google_cloudfunctions2_function" "function" {
    name = var.function
    location = var.gcp_region
    description = "A new function"

    build_config {
      runtime = "python313"
      entry_point = "pubsub_to_bigquery"
      source {
        storage_source {
          bucket = google_storage_bucket.source-bucket.name
          object = google_storage_bucket_object.object.name
        }
      } 
    }

    service_config {
      service_account_email = google_service_account.function_sa.email
    }

    event_trigger {
      trigger_region = var.gcp_region
      event_type = "google.cloud.pubsub.topic.v1.messagePublished"
      pubsub_topic = google_pubsub_topic.topic.id
    }

}

resource "google_cloud_asset_project_feed" "project_feed" {
    project = var.project_id
    feed_id = "activities"
    content_type = "RESOURCE"

    asset_types = ["compute.googleapis.com/Instance"]
    feed_output_config {
      pubsub_destination {
        topic = google_pubsub_topic.topic.id
      }
    }

    depends_on = [google_project_service.apis]
}