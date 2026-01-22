#!/usr/bin/env python3
"""
Test domain search for NoiseGenerator site
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/bb/www/audio-tools-network/.env')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY').strip().strip('"')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY').strip().strip('"')

from domain_search import generate_domain_suggestions, check_domain_availability, pick_best_domain

if __name__ == "__main__":
    # Test with NoiseGenerator
    topic = "white noise, pink noise, brown noise generator for sleep, focus, relaxation, and tinnitus relief"
    direction = "for a free online tool website about"

    print(f"=== Domain Search for: {topic} ===\n")

    # 1) Generate domain suggestions
    print("Step 1: Generating domain suggestions with GPT...")
    suggestions = generate_domain_suggestions(OPENAI_API_KEY, topic, direction, number=30)
    print(f"Generated {len(suggestions)} suggestions:")
    for s in suggestions[:10]:
        print(f"  - {s}")
    print(f"  ... and {len(suggestions)-10} more\n")

    # 2) Check availability
    print("Step 2: Checking domain availability...")
    available_domains = []
    for domain in suggestions:
        try:
            availability = check_domain_availability(domain, RAPIDAPI_KEY)
            status = availability.get('status_codes', [])
            print(f"  {domain}: {status}")

            # Check for available statuses
            if isinstance(status, list):
                status_str = ' '.join(status)
            else:
                status_str = str(status)

            if any(s in status_str for s in ['inactive', 'undelegated', 'available']):
                available_domains.append(domain)
                print(f"    ^ AVAILABLE!")
        except Exception as e:
            print(f"  Error checking {domain}: {e}")

    print(f"\nFound {len(available_domains)} available domains:")
    for d in available_domains:
        print(f"  - {d}")

    # 3) Rank available domains
    if available_domains:
        print("\nStep 3: Ranking available domains with GPT...")
        ranked = pick_best_domain(OPENAI_API_KEY, available_domains, topic)
        print("Ranked domains (best to worst):")
        for i, d in enumerate(ranked[:10], 1):
            print(f"  {i}. {d}")
    else:
        print("\nNo available domains found to rank.")
