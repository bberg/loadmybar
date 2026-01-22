"""
Configuration for site deployment
"""

# Site configurations
SITES = {
    "plate-calculator": {
        "name": "LoadMyBar",
        "domain": "loadmybar.com",
        "local_path": "/Users/bb/www/plate-calculator",
        "github_repo": "plate-calculator",
        "description": "Weightlifting plate calculator - calculate which plates to load on your barbell"
    }
}

# GitHub organization (set to None for personal repos)
GITHUB_ORG = None

# Network-wide settings
NETWORK_NAME = "LoadMyBar"
CONTACT_EMAIL = ""

# All domains
ALL_DOMAINS = {
    "loadmybar.com": "Plate Calculator"
}
