output "function_name" {
  value = google_cloudfunctions2_function.function.name
}

output "function_status" {
  value = google_cloudfunctions2_function.function.state
}