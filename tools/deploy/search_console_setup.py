#!/usr/bin/env python3
"""
Google Search Console setup automation for Audio Tools Network

Usage:
    python search_console_setup.py --credentials PATH_TO_SERVICE_ACCOUNT.json

This script:
1. Adds sites to Search Console
2. Generates DNS verification records
3. Submits sitemaps

Prerequisites:
    pip install google-api-python-client google-auth
"""

import os
import sys
import json
import argparse
from config import SITES

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False
    print("Warning: google-api-python-client not installed")
    print("Run: pip install google-api-python-client google-auth")


class SearchConsoleClient:
    def __init__(self, credentials_path):
        """Initialize with service account credentials"""
        if not GSC_AVAILABLE:
            raise ImportError("google-api-python-client package required")

        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                "https://www.googleapis.com/auth/webmasters",
                "https://www.googleapis.com/auth/webmasters.readonly"
            ]
        )

        self.service = build("searchconsole", "v1", credentials=self.credentials)
        self.webmasters = build("webmasters", "v3", credentials=self.credentials)

    def list_sites(self):
        """List all sites in Search Console"""
        try:
            result = self.webmasters.sites().list().execute()
            return result.get("siteEntry", [])
        except HttpError as e:
            print(f"Error listing sites: {e}")
            return []

    def add_site(self, site_url):
        """Add a site to Search Console

        site_url should be like: https://example.com/ or sc-domain:example.com
        """
        try:
            self.webmasters.sites().add(siteUrl=site_url).execute()
            return True
        except HttpError as e:
            if e.resp.status == 403:
                print(f"  Access denied. Service account may need to be added as owner.")
            else:
                print(f"  Error adding site: {e}")
            return False

    def get_site(self, site_url):
        """Get site information"""
        try:
            return self.webmasters.sites().get(siteUrl=site_url).execute()
        except HttpError as e:
            return None

    def submit_sitemap(self, site_url, sitemap_url):
        """Submit a sitemap for a site"""
        try:
            self.webmasters.sitemaps().submit(
                siteUrl=site_url,
                feedpath=sitemap_url
            ).execute()
            return True
        except HttpError as e:
            print(f"  Error submitting sitemap: {e}")
            return False

    def list_sitemaps(self, site_url):
        """List sitemaps for a site"""
        try:
            result = self.webmasters.sitemaps().list(siteUrl=site_url).execute()
            return result.get("sitemap", [])
        except HttpError as e:
            print(f"  Error listing sitemaps: {e}")
            return []

    def delete_site(self, site_url):
        """Remove a site from Search Console"""
        try:
            self.webmasters.sites().delete(siteUrl=site_url).execute()
            return True
        except HttpError as e:
            print(f"  Error deleting site: {e}")
            return False


def generate_verification_instructions(domain):
    """Generate instructions for DNS verification"""
    return f"""
DNS Verification for {domain}
==============================

Option 1: DNS TXT Record (Recommended)
--------------------------------------
After adding the site to Search Console, you'll receive a verification code.
Add a TXT record to your DNS:

Type: TXT
Name: @ (or leave blank)
Value: google-site-verification=XXXXXXX (the code from Search Console)
TTL: Auto or 3600

Option 2: DNS CNAME Record
--------------------------
Some verification methods use CNAME:

Type: CNAME
Name: XXXXXXX (provided by Google)
Value: XXXXXXX.dv.googlehosted.com
TTL: Auto or 3600

After adding the DNS record, wait 5-10 minutes for propagation,
then click "Verify" in Search Console.

Note: With Cloudflare, DNS propagation is usually instant.
"""


def setup_site_in_console(client, site_key, site_config, dry_run=False):
    """Set up a site in Search Console"""
    domain = site_config["domain"]
    name = site_config["name"]

    # Use URL prefix method (includes https://)
    site_url = f"https://{domain}/"
    sitemap_url = f"https://{domain}/sitemap.xml"

    print(f"\nSetting up Search Console for: {name}")
    print(f"  Site URL: {site_url}")

    if dry_run:
        print(f"  [DRY RUN] Would add site: {site_url}")
        print(f"  [DRY RUN] Would submit sitemap: {sitemap_url}")
        return {"status": "dry_run", "domain": domain}

    # Check if site already exists
    existing_sites = client.list_sites()
    existing_urls = [s.get("siteUrl") for s in existing_sites]

    if site_url in existing_urls:
        print(f"  Site already exists in Search Console")
        # Submit sitemap anyway
        print(f"  Submitting sitemap...")
        client.submit_sitemap(site_url, sitemap_url)
        return {
            "status": "exists",
            "site_url": site_url,
            "sitemap_submitted": True
        }

    # Add the site
    print(f"  Adding site to Search Console...")
    success = client.add_site(site_url)

    if not success:
        print(f"  Failed to add site")
        print(generate_verification_instructions(domain))
        return {
            "status": "failed",
            "site_url": site_url,
            "needs_verification": True
        }

    print(f"  Site added successfully")

    # Submit sitemap
    print(f"  Submitting sitemap: {sitemap_url}")
    sitemap_success = client.submit_sitemap(site_url, sitemap_url)

    return {
        "status": "created",
        "site_url": site_url,
        "sitemap_submitted": sitemap_success
    }


def setup_all_sites(credentials_path, dry_run=False):
    """Set up Search Console for all sites"""
    if not GSC_AVAILABLE:
        print("Error: google-api-python-client package not installed")
        return None

    client = SearchConsoleClient(credentials_path)

    # List existing sites
    existing = client.list_sites()
    print(f"Found {len(existing)} existing sites in Search Console:")
    for site in existing:
        print(f"  - {site.get('siteUrl')}")

    results = {}

    for site_key, site_config in SITES.items():
        result = setup_site_in_console(
            client,
            site_key,
            site_config,
            dry_run
        )
        results[site_key] = result

    return results


def generate_verification_dns_records():
    """Generate placeholder DNS records for all sites

    In practice, the actual verification codes come from Search Console
    after adding each site. This generates the structure.
    """
    records = {}

    for site_key, site_config in SITES.items():
        domain = site_config["domain"]
        records[domain] = {
            "type": "TXT",
            "name": "@",
            "value": "google-site-verification=REPLACE_WITH_ACTUAL_CODE",
            "notes": "Get verification code from Search Console after adding site"
        }

    return records


def main():
    parser = argparse.ArgumentParser(description="Set up Google Search Console for Audio Tools Network")
    parser.add_argument("--credentials", help="Path to service account JSON")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--list-sites", action="store_true", help="List existing sites")
    parser.add_argument("--generate-dns", action="store_true", help="Generate DNS record templates")
    parser.add_argument("--add-site", help="Add a single site URL")
    parser.add_argument("--submit-sitemap", nargs=2, metavar=("SITE_URL", "SITEMAP_URL"),
                        help="Submit sitemap for a site")

    args = parser.parse_args()

    if args.generate_dns:
        records = generate_verification_dns_records()
        print("DNS Verification Records Needed:")
        print("=" * 50)
        for domain, record in records.items():
            print(f"\n{domain}:")
            print(f"  Type: {record['type']}")
            print(f"  Name: {record['name']}")
            print(f"  Value: {record['value']}")
            print(f"  Note: {record['notes']}")
        return

    if not args.credentials:
        print("Error: --credentials required for API operations")
        sys.exit(1)

    if not GSC_AVAILABLE:
        print("Error: google-api-python-client package required")
        print("Run: pip install google-api-python-client google-auth")
        sys.exit(1)

    client = SearchConsoleClient(args.credentials)

    if args.list_sites:
        sites = client.list_sites()
        print("Sites in Search Console:")
        for site in sites:
            print(f"  {site.get('siteUrl')}")
            print(f"    Permission: {site.get('permissionLevel')}")
        return

    if args.add_site:
        success = client.add_site(args.add_site)
        if success:
            print(f"Site added: {args.add_site}")
        return

    if args.submit_sitemap:
        site_url, sitemap_url = args.submit_sitemap
        success = client.submit_sitemap(site_url, sitemap_url)
        if success:
            print(f"Sitemap submitted: {sitemap_url}")
        return

    # Set up all sites
    results = setup_all_sites(args.credentials, args.dry_run)

    if results:
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)

        needs_verification = []
        for site_key, result in results.items():
            status = result.get("status", "unknown")
            print(f"  {site_key}: {status}")
            if result.get("needs_verification"):
                needs_verification.append(SITES[site_key]["domain"])

        if needs_verification:
            print("\n" + "=" * 50)
            print("SITES NEEDING VERIFICATION")
            print("=" * 50)
            print("\nThe following sites need DNS verification:")
            for domain in needs_verification:
                print(f"  - {domain}")
            print("\nSteps:")
            print("1. Go to https://search.google.com/search-console")
            print("2. Add each property (URL prefix method)")
            print("3. Choose DNS verification")
            print("4. Add the TXT record to Cloudflare")
            print("5. Click Verify in Search Console")


if __name__ == "__main__":
    main()
