#!/usr/bin/env python3
"""
Cloudflare DNS automation for Audio Tools Network

Usage:
    python cloudflare_setup.py --token YOUR_CF_TOKEN --zone-id ZONE_ID

This script:
1. Gets zone information for each domain
2. Configures DNS records for Railway
3. Sets up SSL/TLS settings
4. Configures page rules if needed
"""

import os
import sys
import json
import argparse
import requests
from config import SITES, ALL_DOMAINS

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"


class CloudflareClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, data=None):
        """Make an API request"""
        url = f"{CLOUDFLARE_API_URL}{endpoint}"

        response = requests.request(
            method,
            url,
            headers=self.headers,
            json=data
        )

        result = response.json()

        if not result.get("success", False):
            errors = result.get("errors", [])
            print(f"Cloudflare API Error: {errors}")
            return None

        return result.get("result")

    def verify_token(self):
        """Verify the API token is valid"""
        return self._request("GET", "/user/tokens/verify")

    def list_zones(self):
        """List all zones (domains) in the account"""
        return self._request("GET", "/zones")

    def get_zone(self, domain):
        """Get zone info for a specific domain"""
        zones = self._request("GET", f"/zones?name={domain}")
        if zones and len(zones) > 0:
            return zones[0]
        return None

    def create_dns_record(self, zone_id, record_type, name, content, proxied=True, ttl=1):
        """Create a DNS record

        Args:
            zone_id: The zone ID
            record_type: A, AAAA, CNAME, TXT, etc.
            name: Record name (@ for root, or subdomain)
            content: Record value
            proxied: Whether to proxy through Cloudflare (orange cloud)
            ttl: TTL in seconds (1 = automatic)
        """
        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        return self._request("POST", f"/zones/{zone_id}/dns_records", data)

    def update_dns_record(self, zone_id, record_id, record_type, name, content, proxied=True, ttl=1):
        """Update an existing DNS record"""
        data = {
            "type": record_type,
            "name": name,
            "content": content,
            "ttl": ttl,
            "proxied": proxied
        }
        return self._request("PUT", f"/zones/{zone_id}/dns_records/{record_id}", data)

    def list_dns_records(self, zone_id, record_type=None, name=None):
        """List DNS records for a zone"""
        params = []
        if record_type:
            params.append(f"type={record_type}")
        if name:
            params.append(f"name={name}")

        query = "&".join(params)
        endpoint = f"/zones/{zone_id}/dns_records"
        if query:
            endpoint += f"?{query}"

        return self._request("GET", endpoint)

    def delete_dns_record(self, zone_id, record_id):
        """Delete a DNS record"""
        return self._request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")

    def set_ssl_mode(self, zone_id, mode="full"):
        """Set SSL/TLS mode

        Modes: off, flexible, full, strict
        """
        data = {"value": mode}
        return self._request("PATCH", f"/zones/{zone_id}/settings/ssl", data)

    def set_always_https(self, zone_id, enabled=True):
        """Enable/disable Always Use HTTPS"""
        data = {"value": "on" if enabled else "off"}
        return self._request("PATCH", f"/zones/{zone_id}/settings/always_use_https", data)

    def set_min_tls_version(self, zone_id, version="1.2"):
        """Set minimum TLS version"""
        data = {"value": version}
        return self._request("PATCH", f"/zones/{zone_id}/settings/min_tls_version", data)


def setup_domain_dns(client, domain, railway_url, dry_run=False):
    """Set up DNS records for a domain pointing to Railway"""

    print(f"\nSetting up DNS for: {domain}")
    print(f"  Railway URL: {railway_url}")

    # Get zone info
    zone = client.get_zone(domain)
    if not zone:
        print(f"  ERROR: Zone not found for {domain}")
        print(f"  Make sure the domain is added to your Cloudflare account")
        return None

    zone_id = zone["id"]
    print(f"  Zone ID: {zone_id}")

    # Get existing records
    existing = client.list_dns_records(zone_id) or []
    existing_by_name = {r["name"]: r for r in existing}

    results = {"zone_id": zone_id, "records": []}

    # Records to create
    records_needed = [
        # Root domain -> Railway CNAME
        {
            "type": "CNAME",
            "name": "@",
            "content": railway_url,
            "proxied": True
        },
        # www -> root domain
        {
            "type": "CNAME",
            "name": "www",
            "content": domain,
            "proxied": True
        }
    ]

    for record in records_needed:
        record_name = record["name"]
        full_name = domain if record_name == "@" else f"{record_name}.{domain}"

        if dry_run:
            print(f"  [DRY RUN] Would create {record['type']} record: {full_name} -> {record['content']}")
            continue

        # Check if record exists
        if full_name in existing_by_name:
            existing_record = existing_by_name[full_name]
            if existing_record["type"] == record["type"] and existing_record["content"] == record["content"]:
                print(f"  Record already exists: {full_name}")
                results["records"].append({"action": "exists", "name": full_name})
                continue
            else:
                # Update existing record
                print(f"  Updating record: {full_name}")
                result = client.update_dns_record(
                    zone_id,
                    existing_record["id"],
                    record["type"],
                    record_name,
                    record["content"],
                    record["proxied"]
                )
                if result:
                    results["records"].append({"action": "updated", "name": full_name})
                else:
                    results["records"].append({"action": "failed", "name": full_name})
        else:
            # Create new record
            print(f"  Creating record: {full_name} -> {record['content']}")
            result = client.create_dns_record(
                zone_id,
                record["type"],
                record_name,
                record["content"],
                record["proxied"]
            )
            if result:
                results["records"].append({"action": "created", "name": full_name})
            else:
                results["records"].append({"action": "failed", "name": full_name})

    # Configure SSL settings
    if not dry_run:
        print(f"  Configuring SSL settings...")
        client.set_ssl_mode(zone_id, "full")
        client.set_always_https(zone_id, True)
        client.set_min_tls_version(zone_id, "1.2")
        print(f"  SSL configured: Full mode, Always HTTPS, TLS 1.2+")
    else:
        print(f"  [DRY RUN] Would configure SSL: Full mode, Always HTTPS, TLS 1.2+")

    return results


def add_txt_record(client, domain, name, value, dry_run=False):
    """Add a TXT record (useful for verification)"""
    zone = client.get_zone(domain)
    if not zone:
        print(f"Zone not found for {domain}")
        return None

    zone_id = zone["id"]

    if dry_run:
        print(f"[DRY RUN] Would create TXT record: {name}.{domain} -> {value}")
        return True

    result = client.create_dns_record(
        zone_id,
        "TXT",
        name,
        value,
        proxied=False  # TXT records can't be proxied
    )

    return result


def setup_all_domains(token, railway_urls, dry_run=False):
    """Set up DNS for all domains

    Args:
        token: Cloudflare API token
        railway_urls: Dict mapping domain to Railway URL
                      e.g., {"focushum.com": "noise-gen-abc123.railway.app"}
    """
    client = CloudflareClient(token)

    # Verify token
    verify = client.verify_token()
    if not verify:
        print("Failed to verify Cloudflare token")
        return False

    print(f"Token verified. Status: {verify.get('status')}")

    # List zones to verify domains are in account
    zones = client.list_zones()
    if zones:
        print(f"\nFound {len(zones)} zones in account:")
        for z in zones:
            print(f"  - {z['name']} ({z['id']})")

    results = {}

    for site_key, site_config in SITES.items():
        domain = site_config["domain"]
        railway_url = railway_urls.get(domain)

        if not railway_url:
            print(f"\nSkipping {domain}: No Railway URL provided")
            continue

        result = setup_domain_dns(client, domain, railway_url, dry_run)
        results[domain] = result

    return results


def main():
    parser = argparse.ArgumentParser(description="Set up Cloudflare DNS for Audio Tools Network")
    parser.add_argument("--token", required=True, help="Cloudflare API token")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--list-zones", action="store_true", help="List all zones")
    parser.add_argument("--domain", help="Set up single domain")
    parser.add_argument("--railway-url", help="Railway URL for the domain")

    args = parser.parse_args()

    client = CloudflareClient(args.token)

    # Verify token first
    verify = client.verify_token()
    if not verify:
        print("Failed to verify token. Check your API token.")
        sys.exit(1)

    print(f"Token verified successfully")

    if args.list_zones:
        zones = client.list_zones()
        if zones:
            print("\nZones in account:")
            for z in zones:
                print(f"  {z['name']}")
                print(f"    ID: {z['id']}")
                print(f"    Status: {z['status']}")
                print(f"    Name servers: {', '.join(z.get('name_servers', []))}")
        return

    if args.domain and args.railway_url:
        # Set up single domain
        result = setup_domain_dns(client, args.domain, args.railway_url, args.dry_run)
        if result:
            print(f"\nDNS setup complete for {args.domain}")
    else:
        print("\nTo set up DNS, provide --domain and --railway-url")
        print("Or use from Python with setup_all_domains()")


if __name__ == "__main__":
    main()
