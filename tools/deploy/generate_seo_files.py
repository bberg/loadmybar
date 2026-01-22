#!/usr/bin/env python3
"""
Generate sitemaps and robots.txt for all Audio Tools Network sites

Usage:
    python generate_seo_files.py
    python generate_seo_files.py --site noise-generator
"""

import os
import sys
import argparse
from datetime import datetime
from config import SITES, ALL_DOMAINS


def generate_sitemap(domain, pages=None):
    """Generate sitemap.xml content

    Args:
        domain: The domain name (e.g., focushum.com)
        pages: Optional list of page paths (default: just root)
    """
    if pages is None:
        pages = ["/"]

    today = datetime.now().strftime("%Y-%m-%d")

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for page in pages:
        priority = "1.0" if page == "/" else "0.8"
        url = f"https://{domain}{page}"

        xml_parts.append(f"""  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{priority}</priority>
  </url>""")

    xml_parts.append('</urlset>')

    return '\n'.join(xml_parts)


def generate_robots_txt(domain):
    """Generate robots.txt content"""
    return f"""# robots.txt for {domain}
User-agent: *
Allow: /

# Sitemap
Sitemap: https://{domain}/sitemap.xml
"""


def generate_cross_links_footer(current_domain):
    """Generate HTML for cross-linking footer to other sites"""
    links = []
    for domain, name in ALL_DOMAINS.items():
        if domain != current_domain:
            links.append(f'<a href="https://{domain}" target="_blank">{name}</a>')

    return f"""<!-- Related Tools Footer -->
<div class="related-tools">
  <h4>Related Audio Tools</h4>
  <div class="tool-links">
    {' | '.join(links)}
  </div>
</div>"""


def write_seo_files(site_key, site_config, dry_run=False):
    """Generate and write SEO files for a site"""
    local_path = site_config["local_path"]
    domain = site_config["domain"]
    name = site_config["name"]

    print(f"\nGenerating SEO files for: {name}")
    print(f"  Path: {local_path}")
    print(f"  Domain: {domain}")

    # Determine file locations
    static_dir = os.path.join(local_path, "static")

    # Some Flask apps serve static files from root via routes
    # Check for static directory, otherwise use root
    if os.path.exists(static_dir):
        sitemap_path = os.path.join(static_dir, "sitemap.xml")
        robots_path = os.path.join(static_dir, "robots.txt")
    else:
        sitemap_path = os.path.join(local_path, "sitemap.xml")
        robots_path = os.path.join(local_path, "robots.txt")

    # Generate content
    sitemap_content = generate_sitemap(domain)
    robots_content = generate_robots_txt(domain)

    if dry_run:
        print(f"  [DRY RUN] Would create: {sitemap_path}")
        print(f"  [DRY RUN] Would create: {robots_path}")
        return True

    # Write sitemap
    with open(sitemap_path, 'w') as f:
        f.write(sitemap_content)
    print(f"  Created: {sitemap_path}")

    # Write robots.txt
    with open(robots_path, 'w') as f:
        f.write(robots_content)
    print(f"  Created: {robots_path}")

    return True


def update_flask_routes(site_key, site_config, dry_run=False):
    """Add routes to serve sitemap and robots.txt from Flask"""
    local_path = site_config["local_path"]
    app_path = os.path.join(local_path, "app.py")

    if not os.path.exists(app_path):
        print(f"  app.py not found: {app_path}")
        return False

    with open(app_path, 'r') as f:
        content = f.read()

    # Check if routes already exist
    if 'sitemap.xml' in content and 'robots.txt' in content:
        print(f"  SEO routes already exist in app.py")
        return True

    # Route code to add
    seo_routes = '''
# SEO routes
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')
'''

    if dry_run:
        print(f"  [DRY RUN] Would add SEO routes to: {app_path}")
        return True

    # Check if send_from_directory is imported
    if 'send_from_directory' not in content:
        # Add to imports
        content = content.replace(
            'from flask import',
            'from flask import send_from_directory,'
        )
        # If that didn't work, try another pattern
        if 'send_from_directory' not in content:
            content = content.replace(
                'from flask import Flask',
                'from flask import Flask, send_from_directory'
            )

    # Find a good place to add routes (before if __name__ == '__main__')
    if "if __name__ ==" in content:
        content = content.replace(
            "if __name__ ==",
            f"{seo_routes}\nif __name__ =="
        )
    else:
        # Append to end
        content += seo_routes

    with open(app_path, 'w') as f:
        f.write(content)

    print(f"  Added SEO routes to: {app_path}")
    return True


def generate_all_sites(dry_run=False):
    """Generate SEO files for all sites"""
    results = {}

    for site_key, site_config in SITES.items():
        success = write_seo_files(site_key, site_config, dry_run)

        # Also update Flask routes
        if success:
            update_flask_routes(site_key, site_config, dry_run)

        results[site_key] = {
            "status": "success" if success else "failed"
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Generate SEO files for Audio Tools Network sites")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--site", help="Generate for single site only")
    parser.add_argument("--show-sitemap", help="Show sitemap content for a domain")
    parser.add_argument("--show-robots", help="Show robots.txt content for a domain")
    parser.add_argument("--show-crosslinks", help="Show cross-links HTML for a domain")

    args = parser.parse_args()

    if args.show_sitemap:
        print(generate_sitemap(args.show_sitemap))
        return

    if args.show_robots:
        print(generate_robots_txt(args.show_robots))
        return

    if args.show_crosslinks:
        print(generate_cross_links_footer(args.show_crosslinks))
        return

    if args.site:
        if args.site not in SITES:
            print(f"Site not found: {args.site}")
            sys.exit(1)

        write_seo_files(args.site, SITES[args.site], args.dry_run)
        update_flask_routes(args.site, SITES[args.site], args.dry_run)
    else:
        results = generate_all_sites(args.dry_run)

        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        for site_key, result in results.items():
            print(f"  {site_key}: {result['status']}")


if __name__ == "__main__":
    main()
