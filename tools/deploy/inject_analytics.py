#!/usr/bin/env python3
"""
Inject Google Analytics tracking code into all sites

Usage:
    python inject_analytics.py --measurement-ids ga_measurement_ids.json

This script:
1. Reads measurement IDs from JSON file
2. Injects GA4 tracking code into each site's templates
3. Adds custom event tracking for tool usage
"""

import os
import sys
import json
import argparse
import re
from config import SITES


def get_ga_tracking_code(measurement_id, tool_name):
    """Generate GA4 tracking code with custom events"""
    return f'''<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');

  // Tool name for custom events
  window.toolName = '{tool_name}';

  // Track tool usage events
  function trackEvent(action, label, value) {{
    gtag('event', action, {{
      'event_category': 'Tool Usage',
      'event_label': label || window.toolName,
      'value': value || 1
    }});
  }}

  // Track session start
  trackEvent('session_start', window.toolName);

  // Track session duration on page unload
  var sessionStart = Date.now();
  window.addEventListener('beforeunload', function() {{
    var duration = Math.round((Date.now() - sessionStart) / 1000);
    gtag('event', 'session_duration', {{
      'event_category': 'Engagement',
      'event_label': window.toolName,
      'value': duration
    }});
  }});
</script>'''


def inject_into_template(template_path, tracking_code, dry_run=False):
    """Inject tracking code into an HTML template"""

    if not os.path.exists(template_path):
        print(f"  Template not found: {template_path}")
        return False

    with open(template_path, 'r') as f:
        content = f.read()

    # Check if already injected
    if 'googletagmanager.com/gtag' in content:
        print(f"  Analytics already present in: {template_path}")
        return True

    # Find </head> tag and inject before it
    if '</head>' not in content:
        print(f"  No </head> tag found in: {template_path}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would inject analytics into: {template_path}")
        return True

    # Inject tracking code before </head>
    new_content = content.replace(
        '</head>',
        f'{tracking_code}\n</head>'
    )

    with open(template_path, 'w') as f:
        f.write(new_content)

    print(f"  Injected analytics into: {template_path}")
    return True


def inject_analytics_for_site(site_key, site_config, measurement_id, dry_run=False):
    """Inject analytics into a site's templates"""
    local_path = site_config["local_path"]
    name = site_config["name"]

    print(f"\nInjecting analytics for: {name}")
    print(f"  Path: {local_path}")
    print(f"  Measurement ID: {measurement_id}")

    tracking_code = get_ga_tracking_code(measurement_id, name)

    # Find template files
    templates_dir = os.path.join(local_path, "templates")
    if not os.path.exists(templates_dir):
        print(f"  Templates directory not found: {templates_dir}")
        return False

    # Look for index.html or base.html
    template_files = []
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            template_files.append(os.path.join(templates_dir, filename))

    if not template_files:
        print(f"  No HTML templates found in: {templates_dir}")
        return False

    # Inject into main template (usually index.html or base.html)
    # For Flask apps with extends, inject into base.html if it exists
    main_template = None
    for tpl in template_files:
        if 'base.html' in tpl:
            main_template = tpl
            break
        if 'index.html' in tpl:
            main_template = tpl

    if main_template:
        return inject_into_template(main_template, tracking_code, dry_run)
    else:
        # Inject into all templates
        success = True
        for tpl in template_files:
            if not inject_into_template(tpl, tracking_code, dry_run):
                success = False
        return success


def inject_all_sites(measurement_ids, dry_run=False):
    """Inject analytics into all sites"""
    results = {}

    for site_key, site_config in SITES.items():
        measurement_id = measurement_ids.get(site_key)

        if not measurement_id:
            print(f"\nSkipping {site_key}: No measurement ID found")
            results[site_key] = {"status": "skipped", "reason": "no_measurement_id"}
            continue

        success = inject_analytics_for_site(
            site_key,
            site_config,
            measurement_id,
            dry_run
        )

        results[site_key] = {
            "status": "success" if success else "failed",
            "measurement_id": measurement_id
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Inject Google Analytics into Audio Tools Network sites")
    parser.add_argument("--measurement-ids", required=True,
                        help="Path to JSON file with measurement IDs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done")
    parser.add_argument("--site", help="Inject into single site only")

    args = parser.parse_args()

    # Load measurement IDs
    with open(args.measurement_ids, 'r') as f:
        measurement_ids = json.load(f)

    print(f"Loaded {len(measurement_ids)} measurement IDs")

    if args.site:
        if args.site not in SITES:
            print(f"Site not found: {args.site}")
            sys.exit(1)

        measurement_id = measurement_ids.get(args.site)
        if not measurement_id:
            print(f"No measurement ID for: {args.site}")
            sys.exit(1)

        inject_analytics_for_site(
            args.site,
            SITES[args.site],
            measurement_id,
            args.dry_run
        )
    else:
        results = inject_all_sites(measurement_ids, args.dry_run)

        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        for site_key, result in results.items():
            print(f"  {site_key}: {result['status']}")


if __name__ == "__main__":
    main()
