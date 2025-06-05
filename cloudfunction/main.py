import base64
import json
import os
import datetime
import functions_framework
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT")
BQ_DATASET = os.getenv("BQ_DATASET", "activities")
BQ_TABLE = os.getenv("BQ_TABLE", "resources")
TABLE_ID = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

REQUIRED_LABELS_CONFIG = os.getenv("REQUIRED_LABELS_JSON", '["owner", "cost-center", "environment"]')
try:
    REQUIRED_LABELS = json.loads(REQUIRED_LABELS_CONFIG)
except json.JSONDecodeError:
    print(f"Warning: Could not parse REQUIRED_LABELS_JSON: {REQUIRED_LABELS_CONFIG}. Using default.")
    REQUIRED_LABELS = ["owner", "cost-center", "environment"]


def get_vm_details(asset_data):
    """Extracts VM specific details from the asset data."""
    resource_data = asset_data.get("resource", {}).get("data", {})
    
    vm_details = {
        "asset_full_name": asset_data.get("name"),
        "asset_type": asset_data.get("assetType"),
        "vm_name": resource_data.get("name"),
        "vm_id": str(resource_data.get("id", "")), 
        "creation_timestamp": resource_data.get("creationTimestamp"),
        "project_id": None, 
        "machine_type": None,
        "zone": None,
        "labels": resource_data.get("labels", {}), 
        "network_ip": None,
    }

    if vm_details["asset_full_name"]:
        parts = vm_details["asset_full_name"].split('/')
        if len(parts) > 3 and parts[2] == "projects":
            vm_details["project_id"] = parts[3]

    machine_type_full = resource_data.get("machineType", "")
    if machine_type_full:
        vm_details["machine_type"] = machine_type_full.split('/')[-1]

    zone_full = resource_data.get("zone", "")
    if zone_full:
        vm_details["zone"] = zone_full.split('/')[-1]
    
    network_interfaces = resource_data.get("networkInterfaces", [])
    if network_interfaces:
        vm_details["network_ip"] = network_interfaces[0].get("networkIP")
        
    return vm_details

def check_label_compliance(instance_labels):
    """Checks for required labels and returns compliance status and details."""
    if not isinstance(instance_labels, dict):
        instance_labels = {}

    missing_labels = [label for label in REQUIRED_LABELS if label not in instance_labels]
    
    if not missing_labels:
        compliance_status = "COMPLIANT"
        compliance_details = "All required labels are present."
    else:
        compliance_status = "NON_COMPLIANT"
        compliance_details = f"Missing required labels: {', '.join(missing_labels)}"
        
    return compliance_status, compliance_details

@functions_framework.cloud_event
def pubsub_to_bigquery(cloud_event):
    try:
        pubsub_message_b64 = cloud_event.data["message"]["data"]
        pubsub_message_str = base64.b64decode(pubsub_message_b64).decode('utf-8')
        print(f"Received raw message: {pubsub_message_str}")

        asset_payload = json.loads(pubsub_message_str)

        if asset_payload.get("assetType") != "compute.googleapis.com/Instance":
            print(f"Skipping asset type: {asset_payload.get('assetType')}")
            return

        vm_info = get_vm_details(asset_payload)
        
        compliance_status, compliance_details = check_label_compliance(vm_info["labels"])

        row_to_insert = {
            "asset_full_name": vm_info["asset_full_name"],
            "asset_type": vm_info["asset_type"],
            "vm_name": vm_info["vm_name"],
            "vm_id": vm_info["vm_id"],
            "creation_timestamp": vm_info["creation_timestamp"],
            "machine_type": vm_info["machine_type"],
            "zone": vm_info["zone"],
            "project_id": vm_info["project_id"],
            "labels": json.dumps(vm_info["labels"]) if vm_info["labels"] else None, 
            "network_ip": vm_info["network_ip"],
            "compliance_status": compliance_status,
            "compliance_details": compliance_details,
            "ingestion_timestamp": datetime.datetime.utcnow().isoformat(), 
            "raw_payload": pubsub_message_str
        }

        client = bigquery.Client()
        table_ref = client.get_table(TABLE_ID)


        errors = client.insert_rows_json(table_ref, [row_to_insert])

        if not errors:
            print(f"Successfully inserted row for VM: {vm_info.get('vm_name', 'Unknown VM')}")
        else:
            print(f"Errors inserting into BigQuery for VM {vm_info.get('vm_name', 'Unknown VM')}: {errors}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Pub/Sub message: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")