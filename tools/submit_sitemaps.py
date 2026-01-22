#!/usr/bin/env python3
"""
Submit sitemaps to Google Search Console via API.

Usage:
    python submit_sitemaps.py

Note: Manual indexing requests (URL Inspection) cannot be done via API.
      Those must be done through Search Console UI.
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Sites configuration
SITES = [
    {"name": "NoiseGenerator", "url": "https://focushum.com/", "sitemap": "https://focushum.com/sitemap.xml"},
    {"name": "ToneGenerator", "url": "https://tonesynth.com/", "sitemap": "https://tonesynth.com/sitemap.xml"},
    {"name": "BinauralBeats", "url": "https://binauralhq.com/", "sitemap": "https://binauralhq.com/sitemap.xml"},
    {"name": "DroneGenerator", "url": "https://omtones.com/", "sitemap": "https://omtones.com/sitemap.xml"},
    {"name": "FrequencyGenerator", "url": "https://testtones.com/", "sitemap": "https://testtones.com/sitemap.xml"},
    {"name": "Metronome", "url": "https://metronomely.com/", "sitemap": "https://metronomely.com/sitemap.xml"},
]

def get_service():
    """Create Search Console API service."""
    # Load service account from file
    sa_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tools", "deploy", "service-account.json"
    )

    if not os.path.exists(sa_path):
        raise FileNotFoundError(f"Service account not found: {sa_path}")

    creds = service_account.Credentials.from_service_account_file(
        sa_path,
        scopes=["https://www.googleapis.com/auth/webmasters"]
    )

    return build("searchconsole", "v1", credentials=creds)


def list_sitemaps(service, site_url: str):
    """List existing sitemaps for a site."""
    try:
        response = service.sitemaps().list(siteUrl=site_url).execute()
        return response.get("sitemap", [])
    except Exception as e:
        print(f"  Error listing sitemaps: {e}")
        return []


def submit_sitemap(service, site_url: str, sitemap_url: str):
    """Submit a sitemap to Search Console."""
    try:
        service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
        return True
    except Exception as e:
        print(f"  Error submitting sitemap: {e}")
        return False


def main():
    print("=" * 60)
    print("Google Search Console - Sitemap Submission")
    print("=" * 60)
    print()

    try:
        service = get_service()
        print("✓ Connected to Search Console API")
        print()
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)

    results = []

    for site in SITES:
        print(f"Site: {site['name']} ({site['url']})")

        # List existing sitemaps
        existing = list_sitemaps(service, site['url'])
        if existing:
            print(f"  Existing sitemaps: {len(existing)}")
            for sm in existing:
                errors = sm.get("errors", 0)
                warnings = sm.get("warnings", 0)
                status = "✓" if errors == 0 else "✗"
                print(f"    {status} {sm.get('path')} - {sm.get('lastSubmitted', 'never')}")

        # Submit sitemap
        print(f"  Submitting: {site['sitemap']}")
        success = submit_sitemap(service, site['url'], site['sitemap'])

        if success:
            print("  ✓ Sitemap submitted successfully")
            results.append((site['name'], True))
        else:
            print("  ✗ Sitemap submission failed")
            results.append((site['name'], False))

        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success_count = sum(1 for _, s in results if s)
    print(f"Submitted: {success_count}/{len(results)} sitemaps")
    print()
    print("NOTE: Manual indexing requests cannot be done via API.")
    print("      Visit Search Console to request indexing for new URLs:")
    print("      https://search.google.com/search-console")
    print()
    print("New URLs to request indexing for:")
    print("  - https://focushum.com/for-sleep")
    print("  - https://focushum.com/for-focus")
    print("  - https://binauralhq.com/for-sleep")
    print("  - https://binauralhq.com/for-meditation")


if __name__ == "__main__":
    main()
