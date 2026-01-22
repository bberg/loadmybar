#!/usr/bin/env python3
"""
Simple domain availability checker using Domainr API
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv('/Users/bb/www/audio-tools-network/.env')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '').strip().strip('"')

def check_domain(domain):
    url = "https://domainr.p.rapidapi.com/v2/status"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "domainr.p.rapidapi.com"
    }
    params = {"domain": domain}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        if "status" in data and len(data["status"]) > 0:
            status = data["status"][0].get("status", ["unknown"])
            return status
        return ["error"]
    except Exception as e:
        return [f"error: {e}"]

if __name__ == "__main__":
    domains = sys.argv[1:] if len(sys.argv) > 1 else []

    for domain in domains:
        status = check_domain(domain)
        # Available indicators: inactive, undelegated
        # Taken indicators: active, registered
        is_available = any(s in str(status) for s in ['inactive', 'undelegated'])
        marker = "✅ AVAILABLE" if is_available else "❌ taken"
        print(f"{domain}: {status} {marker}")
