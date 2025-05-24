# Project PLUTO Starter Code
# Use as the base for a Cloud Run Function (or in a container)
# Tested with Cloud Run Function using Python 3.12 and eventarc
# Change entry point from hello_pubsub to pubsub_to_bigquery
# Ensure service account has permissions to pub/sub topic
# Update requirements file
# Assumes a dataset called activities exists
# Assumes a table call resources
# resources schema - single column:  message:string
import base64
import functions_framework
from google.cloud import bigquery
table_id = "activities.resources"

# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def pubsub_to_bigquery(cloud_event):
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode('utf-8') 
    print(pubsub_message)
    client = bigquery.Client()
    table = client.get_table(table_id)
    row_to_insert = [(pubsub_message,)]     # NOTE - the trailing comma is required for this case - it expects a tuple
    errors = client.insert_rows(table, row_to_insert)
    if errors == []:
        print("Row Inserted")
    else:
        print(errors)