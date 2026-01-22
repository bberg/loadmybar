#!/usr/bin/env python3
"""
Master deployment orchestration for Audio Tools Network

This script coordinates all deployment steps:
1. Railway project creation
2. Cloudflare DNS configuration
3. Google Analytics setup
4. Search Console verification
5. Analytics code injection
6. SEO file generation

Usage:
    python deploy_all.py --check    # Verify all prerequisites
    python deploy_all.py --dry-run  # Show what would be done
    python deploy_all.py --deploy   # Run full deployment

Prerequisites:
    - Railway API token
    - Cloudflare API token
    - Google Cloud service account JSON
    - All domains purchased on Cloudflare
"""

import os
import sys
import json
import argparse
from config import SITES, ALL_DOMAINS, GITHUB_ORG


def check_prerequisites():
    """Check if all required files and environment are ready"""
    print("Checking Prerequisites")
    print("=" * 50)

    issues = []

    # Check for config
    print("\n[Config]")
    print(f"  Sites configured: {len(SITES)}")
    for site_key, site_config in SITES.items():
        path = site_config.get("local_path")
        if os.path.exists(path):
            print(f"  ✓ {site_key}: {path}")
        else:
            print(f"  ✗ {site_key}: {path} (NOT FOUND)")
            issues.append(f"Site path not found: {path}")

    # Check for environment file
    print("\n[Environment]")
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    if os.path.exists(env_file):
        print(f"  ✓ .env file exists")
    else:
        print(f"  ✗ .env file not found")
        issues.append("Create .env file with API tokens")

    # Check required API tokens
    print("\n[API Tokens Required]")
    required_tokens = [
        ("RAILWAY_TOKEN", "Railway API token"),
        ("CLOUDFLARE_TOKEN", "Cloudflare API token"),
        ("GOOGLE_CREDENTIALS_PATH", "Path to Google service account JSON")
    ]

    for env_var, description in required_tokens:
        value = os.environ.get(env_var)
        if value:
            print(f"  ✓ {env_var}: Set")
        else:
            print(f"  ✗ {env_var}: Not set ({description})")
            issues.append(f"Set {env_var} environment variable")

    # Check Python packages
    print("\n[Python Packages]")
    packages = [
        ("requests", True),
        ("google.analytics.admin", False),
        ("googleapiclient", False)
    ]

    for package, required in packages:
        try:
            __import__(package)
            print(f"  ✓ {package}: Installed")
        except ImportError:
            status = "Required" if required else "Optional"
            print(f"  ✗ {package}: Not installed ({status})")
            if required:
                issues.append(f"Install {package}: pip install {package}")

    # Summary
    print("\n" + "=" * 50)
    if issues:
        print(f"ISSUES FOUND: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("ALL PREREQUISITES MET ✓")
        return True


def show_deployment_plan():
    """Show what will be deployed"""
    print("\nDeployment Plan")
    print("=" * 50)

    print("\n[Sites to Deploy]")
    for site_key, site_config in SITES.items():
        print(f"\n  {site_config['name']}")
        print(f"    Domain: {site_config['domain']}")
        print(f"    GitHub: {GITHUB_ORG or 'personal'}/{site_config['github_repo']}")
        print(f"    Local:  {site_config['local_path']}")

    print("\n[Deployment Steps]")
    steps = [
        "1. Generate sitemaps and robots.txt for each site",
        "2. Create Railway projects and link to GitHub",
        "3. Get Railway deployment URLs",
        "4. Configure Cloudflare DNS for each domain",
        "5. Create GA4 properties and get measurement IDs",
        "6. Inject analytics tracking code into sites",
        "7. Add sites to Google Search Console",
        "8. Submit sitemaps to Search Console",
        "9. Verify all deployments"
    ]
    for step in steps:
        print(f"  {step}")


def run_step(step_name, module_name, function_name, *args, **kwargs):
    """Run a deployment step with error handling"""
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print('='*50)

    try:
        module = __import__(module_name)
        func = getattr(module, function_name)
        result = func(*args, **kwargs)
        print(f"\n✓ {step_name} completed")
        return result
    except Exception as e:
        print(f"\n✗ {step_name} failed: {e}")
        return None


def deploy_all(dry_run=False):
    """Run full deployment"""
    import generate_seo_files
    import railway_setup
    import cloudflare_setup
    import google_analytics_setup
    import search_console_setup
    import inject_analytics

    # Get tokens from environment
    railway_token = os.environ.get("RAILWAY_TOKEN")
    cloudflare_token = os.environ.get("CLOUDFLARE_TOKEN")
    google_creds = os.environ.get("GOOGLE_CREDENTIALS_PATH")
    ga_account_id = os.environ.get("GA_ACCOUNT_ID")

    results = {
        "seo_files": None,
        "railway": None,
        "cloudflare": None,
        "analytics": None,
        "search_console": None,
        "injection": None
    }

    # Step 1: Generate SEO files
    print("\n" + "="*60)
    print("STEP 1: Generate SEO Files (sitemaps, robots.txt)")
    print("="*60)
    results["seo_files"] = generate_seo_files.generate_all_sites(dry_run)

    # Step 2: Railway deployment
    if railway_token:
        print("\n" + "="*60)
        print("STEP 2: Create Railway Projects")
        print("="*60)
        results["railway"] = railway_setup.setup_all_sites(railway_token, dry_run)
    else:
        print("\nSkipping Railway setup: RAILWAY_TOKEN not set")

    # Step 3: Cloudflare DNS
    # This needs Railway URLs, so we need to get them first
    if cloudflare_token and results.get("railway"):
        print("\n" + "="*60)
        print("STEP 3: Configure Cloudflare DNS")
        print("="*60)

        # Build railway_urls mapping
        railway_urls = {}
        for site_key, result in results["railway"].items():
            if result and result.get("status") == "success":
                # Railway URLs are typically project-name.railway.app
                # This would need to be fetched from Railway API after deployment
                domain = SITES[site_key]["domain"]
                project_name = SITES[site_key]["name"].lower().replace(" ", "-")
                railway_urls[domain] = f"{project_name}.up.railway.app"

        if railway_urls:
            results["cloudflare"] = cloudflare_setup.setup_all_domains(
                cloudflare_token,
                railway_urls,
                dry_run
            )
    else:
        print("\nSkipping Cloudflare setup: Token not set or Railway not deployed")

    # Step 4: Google Analytics
    if google_creds and ga_account_id:
        print("\n" + "="*60)
        print("STEP 4: Set Up Google Analytics 4")
        print("="*60)
        results["analytics"] = google_analytics_setup.setup_all_sites(
            google_creds,
            ga_account_id,
            dry_run
        )
    else:
        print("\nSkipping GA setup: GOOGLE_CREDENTIALS_PATH or GA_ACCOUNT_ID not set")

    # Step 5: Inject analytics
    if results.get("analytics"):
        print("\n" + "="*60)
        print("STEP 5: Inject Analytics Code")
        print("="*60)

        # Build measurement IDs dict
        measurement_ids = {}
        for site_key, result in results["analytics"].items():
            if result and result.get("measurement_id"):
                measurement_ids[site_key] = result["measurement_id"]

        if measurement_ids:
            results["injection"] = inject_analytics.inject_all_sites(
                measurement_ids,
                dry_run
            )
    else:
        print("\nSkipping analytics injection: No measurement IDs available")

    # Step 6: Search Console
    if google_creds:
        print("\n" + "="*60)
        print("STEP 6: Set Up Google Search Console")
        print("="*60)
        results["search_console"] = search_console_setup.setup_all_sites(
            google_creds,
            dry_run
        )
    else:
        print("\nSkipping Search Console: GOOGLE_CREDENTIALS_PATH not set")

    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)

    for step, result in results.items():
        if result is None:
            status = "SKIPPED"
        elif isinstance(result, dict):
            successes = sum(1 for r in result.values() if r and r.get("status") == "success")
            status = f"{successes}/{len(result)} succeeded"
        else:
            status = "OK"
        print(f"  {step}: {status}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Audio Tools Network",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  RAILWAY_TOKEN           Railway API token
  CLOUDFLARE_TOKEN        Cloudflare API token
  GOOGLE_CREDENTIALS_PATH Path to Google service account JSON
  GA_ACCOUNT_ID           Google Analytics account ID

Examples:
  python deploy_all.py --check      Check prerequisites
  python deploy_all.py --plan       Show deployment plan
  python deploy_all.py --dry-run    Simulate deployment
  python deploy_all.py --deploy     Run full deployment
"""
    )

    parser.add_argument("--check", action="store_true",
                        help="Check prerequisites")
    parser.add_argument("--plan", action="store_true",
                        help="Show deployment plan")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate deployment without making changes")
    parser.add_argument("--deploy", action="store_true",
                        help="Run full deployment")
    parser.add_argument("--step", choices=[
        "seo", "railway", "cloudflare", "analytics", "inject", "search-console"
    ], help="Run a specific step only")

    args = parser.parse_args()

    if args.check:
        check_prerequisites()
        return

    if args.plan:
        show_deployment_plan()
        return

    if args.deploy or args.dry_run:
        # First check prerequisites
        if not check_prerequisites():
            print("\nFix the issues above before deploying.")
            sys.exit(1)

        show_deployment_plan()

        if not args.dry_run:
            print("\n" + "="*60)
            response = input("Proceed with deployment? (yes/no): ")
            if response.lower() != "yes":
                print("Deployment cancelled.")
                return

        deploy_all(dry_run=args.dry_run)
        return

    if args.step:
        # Run individual step
        print(f"Running step: {args.step}")
        # Implementation for individual steps would go here
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
