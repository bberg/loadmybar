#!/usr/bin/env python3
"""
Domain search using Domainr API (RapidAPI)
Usage: python3 domain_search_api.py "noise generator"
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv('/Users/bb/www/audio-tools-network/.env')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', '').strip().strip('"')

HEADERS = {
    'x-rapidapi-key': RAPIDAPI_KEY,
    'x-rapidapi-host': 'domainr.p.rapidapi.com'
}

def search_domains(query, defaults='com,io,co,net'):
    """Search for domain suggestions"""
    url = 'https://domainr.p.rapidapi.com/v2/search'
    params = {
        'query': query,
        'defaults': defaults,
        'registrar': 'dnsimple.com'
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        return [r['domain'] for r in data.get('results', [])]
    return []

def check_availability(domain):
    """Check if domain is available"""
    url = 'https://domainr.p.rapidapi.com/v2/status'
    params = {'domain': domain}
    response = requests.get(url, headers=HEADERS, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get('status'):
            status_info = data['status'][0]
            status_str = status_info.get('status', '')
            summary = status_info.get('summary', '')
            # Available statuses: inactive, undelegated
            # Taken statuses: active, reserved, marketed
            is_available = 'inactive' in status_str or 'undelegated' in status_str
            return {
                'domain': domain,
                'available': is_available,
                'status': status_str,
                'summary': summary
            }
    return {'domain': domain, 'available': False, 'status': 'error', 'summary': 'error'}

def search_and_check(query, extra_domains=None):
    """Search for domains and check availability"""
    print(f"🔍 Searching domains for: {query}")
    print("=" * 50)

    # Get suggestions from API
    suggestions = search_domains(query)

    # Add extra domains if provided
    if extra_domains:
        suggestions.extend(extra_domains)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for d in suggestions:
        if d not in seen:
            seen.add(d)
            unique.append(d)

    print(f"Found {len(unique)} domain suggestions\n")

    available = []
    taken = []

    for domain in unique:
        result = check_availability(domain)
        if result['available']:
            available.append(result)
            print(f"✅ {domain} - AVAILABLE")
        else:
            taken.append(result)
            print(f"❌ {domain} - {result['summary']}")

    print("\n" + "=" * 50)
    print(f"SUMMARY: {len(available)} available, {len(taken)} taken")

    if available:
        print("\n🎯 AVAILABLE DOMAINS:")
        for r in available:
            print(f"   • {r['domain']}")

    return available, taken

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 domain_search_api.py 'search query' [extra,domains,to,check]")
        sys.exit(1)

    query = sys.argv[1]
    extra = sys.argv[2].split(',') if len(sys.argv) > 2 else None

    search_and_check(query, extra)
