#!/usr/bin/env python3
"""
Google Analytics 4 setup automation for Audio Tools Network

Usage:
    python google_analytics_setup.py --credentials PATH_TO_SERVICE_ACCOUNT.json

This script:
1. Creates GA4 properties for each site
2. Creates web data streams
3. Returns measurement IDs for tracking code injection

Prerequisites:
    pip install google-analytics-admin
"""

import os
import sys
import json
import argparse
from config import SITES

try:
    from google.analytics.admin import AnalyticsAdminServiceClient
    from google.analytics.admin_v1alpha.types import (
        Property,
        DataStream,
        WebStreamData
    )
    from google.oauth2 import service_account
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False
    print("Warning: google-analytics-admin not installed")
    print("Run: pip install google-analytics-admin")


class GoogleAnalyticsClient:
    def __init__(self, credentials_path):
        """Initialize with service account credentials"""
        if not GA_AVAILABLE:
            raise ImportError("google-analytics-admin package required")

        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.edit"]
        )
        self.client = AnalyticsAdminServiceClient(credentials=self.credentials)

        # Get account ID from credentials
        with open(credentials_path) as f:
            creds_data = json.load(f)
            self.service_email = creds_data.get("client_email", "")

    def list_accounts(self):
        """List all GA accounts accessible by the service account"""
        accounts = []
        for account in self.client.list_accounts():
            accounts.append({
                "name": account.name,
                "display_name": account.display_name,
                "id": account.name.split("/")[-1]
            })
        return accounts

    def list_properties(self, account_id):
        """List all properties in an account"""
        properties = []
        parent = f"accounts/{account_id}"

        for prop in self.client.list_properties(filter=f"parent:{parent}"):
            properties.append({
                "name": prop.name,
                "display_name": prop.display_name,
                "id": prop.name.split("/")[-1],
                "time_zone": prop.time_zone,
                "currency_code": prop.currency_code
            })
        return properties

    def create_property(self, account_id, display_name, time_zone="America/New_York", currency="USD"):
        """Create a new GA4 property"""
        parent = f"accounts/{account_id}"

        property_obj = Property(
            parent=parent,
            display_name=display_name,
            time_zone=time_zone,
            currency_code=currency
        )

        result = self.client.create_property(property=property_obj)

        return {
            "name": result.name,
            "display_name": result.display_name,
            "id": result.name.split("/")[-1]
        }

    def list_data_streams(self, property_id):
        """List data streams for a property"""
        parent = f"properties/{property_id}"
        streams = []

        for stream in self.client.list_data_streams(parent=parent):
            stream_info = {
                "name": stream.name,
                "type": str(stream.type_),
                "display_name": stream.display_name
            }
            if stream.web_stream_data:
                stream_info["measurement_id"] = stream.web_stream_data.measurement_id
                stream_info["default_uri"] = stream.web_stream_data.default_uri
            streams.append(stream_info)

        return streams

    def create_web_data_stream(self, property_id, display_name, default_uri):
        """Create a web data stream for a property"""
        parent = f"properties/{property_id}"

        data_stream = DataStream(
            display_name=display_name,
            type_=DataStream.DataStreamType.WEB_DATA_STREAM,
            web_stream_data=WebStreamData(
                default_uri=default_uri
            )
        )

        result = self.client.create_data_stream(
            parent=parent,
            data_stream=data_stream
        )

        return {
            "name": result.name,
            "display_name": result.display_name,
            "measurement_id": result.web_stream_data.measurement_id,
            "stream_id": result.name.split("/")[-1]
        }

    def get_measurement_id(self, property_id):
        """Get the measurement ID for a property's web stream"""
        streams = self.list_data_streams(property_id)
        for stream in streams:
            if stream.get("measurement_id"):
                return stream["measurement_id"]
        return None


def setup_analytics_for_site(client, account_id, site_key, site_config, dry_run=False):
    """Set up GA4 for a single site"""
    domain = site_config["domain"]
    name = site_config["name"]

    print(f"\nSetting up GA4 for: {name}")
    print(f"  Domain: {domain}")

    if dry_run:
        print(f"  [DRY RUN] Would create property: {name}")
        print(f"  [DRY RUN] Would create web stream for: https://{domain}")
        return {"status": "dry_run", "domain": domain}

    # Check if property already exists
    existing_props = client.list_properties(account_id)
    for prop in existing_props:
        if prop["display_name"] == name:
            print(f"  Property already exists: {prop['id']}")
            measurement_id = client.get_measurement_id(prop["id"])
            if measurement_id:
                print(f"  Measurement ID: {measurement_id}")
                return {
                    "status": "exists",
                    "property_id": prop["id"],
                    "measurement_id": measurement_id
                }

    # Create property
    print(f"  Creating property...")
    prop_result = client.create_property(
        account_id,
        name,
        time_zone="America/New_York"
    )
    property_id = prop_result["id"]
    print(f"  Property created: {property_id}")

    # Create web data stream
    print(f"  Creating web data stream...")
    stream_result = client.create_web_data_stream(
        property_id,
        f"{name} Web Stream",
        f"https://{domain}"
    )
    measurement_id = stream_result["measurement_id"]
    print(f"  Measurement ID: {measurement_id}")

    return {
        "status": "created",
        "property_id": property_id,
        "stream_id": stream_result["stream_id"],
        "measurement_id": measurement_id
    }


def setup_all_sites(credentials_path, account_id, dry_run=False):
    """Set up GA4 for all sites"""
    if not GA_AVAILABLE:
        print("Error: google-analytics-admin package not installed")
        return None

    client = GoogleAnalyticsClient(credentials_path)

    # Verify account access
    accounts = client.list_accounts()
    print(f"Found {len(accounts)} GA accounts:")
    for acc in accounts:
        print(f"  - {acc['display_name']} ({acc['id']})")

    if account_id not in [a["id"] for a in accounts]:
        print(f"Error: Account {account_id} not found or not accessible")
        return None

    results = {}

    for site_key, site_config in SITES.items():
        result = setup_analytics_for_site(
            client,
            account_id,
            site_key,
            site_config,
            dry_run
        )
        results[site_key] = result

    return results


def generate_tracking_code(measurement_id):
    """Generate the GA4 tracking code snippet"""
    return f'''<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');
</script>'''


def generate_custom_events_code():
    """Generate code for tracking custom events"""
    return '''<!-- Custom Event Tracking -->
<script>
// Track tool usage
function trackToolUsage(toolName, action, value) {
  gtag('event', action, {
    'event_category': 'Tool Usage',
    'event_label': toolName,
    'value': value
  });
}

// Track when user starts using a tool
function trackToolStart(toolName) {
  trackToolUsage(toolName, 'start', 1);
}

// Track session duration
let sessionStart = Date.now();
window.addEventListener('beforeunload', function() {
  const duration = Math.round((Date.now() - sessionStart) / 1000);
  trackToolUsage(window.toolName || 'unknown', 'session_duration', duration);
});
</script>'''


def main():
    parser = argparse.ArgumentParser(description="Set up Google Analytics 4 for Audio Tools Network")
    parser.add_argument("--credentials", required=True, help="Path to service account JSON")
    parser.add_argument("--account-id", required=True, help="GA account ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--list-accounts", action="store_true", help="List accessible accounts")
    parser.add_argument("--list-properties", action="store_true", help="List properties in account")
    parser.add_argument("--generate-code", help="Generate tracking code for measurement ID")

    args = parser.parse_args()

    if args.generate_code:
        print(generate_tracking_code(args.generate_code))
        print("\n")
        print(generate_custom_events_code())
        return

    if not GA_AVAILABLE:
        print("Error: google-analytics-admin package required")
        print("Run: pip install google-analytics-admin")
        sys.exit(1)

    client = GoogleAnalyticsClient(args.credentials)

    if args.list_accounts:
        accounts = client.list_accounts()
        print("Accessible GA Accounts:")
        for acc in accounts:
            print(f"  {acc['display_name']}")
            print(f"    ID: {acc['id']}")
        return

    if args.list_properties:
        properties = client.list_properties(args.account_id)
        print(f"Properties in account {args.account_id}:")
        for prop in properties:
            print(f"  {prop['display_name']}")
            print(f"    ID: {prop['id']}")
            measurement_id = client.get_measurement_id(prop['id'])
            if measurement_id:
                print(f"    Measurement ID: {measurement_id}")
        return

    # Set up all sites
    results = setup_all_sites(args.credentials, args.account_id, args.dry_run)

    if results:
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)

        # Also save measurement IDs to a file
        measurement_ids = {}
        for site_key, result in results.items():
            status = result.get("status", "unknown")
            measurement_id = result.get("measurement_id", "N/A")
            print(f"  {site_key}: {status}")
            if measurement_id != "N/A":
                print(f"    Measurement ID: {measurement_id}")
                measurement_ids[site_key] = measurement_id

        # Save to file
        if measurement_ids and not args.dry_run:
            output_file = "ga_measurement_ids.json"
            with open(output_file, "w") as f:
                json.dump(measurement_ids, f, indent=2)
            print(f"\nMeasurement IDs saved to: {output_file}")


if __name__ == "__main__":
    main()
