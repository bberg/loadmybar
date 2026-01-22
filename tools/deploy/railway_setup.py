#!/usr/bin/env python3
"""
Railway deployment automation for Audio Tools Network

Usage:
    python railway_setup.py --token YOUR_RAILWAY_TOKEN

This script:
1. Creates a Railway project for each site
2. Links to GitHub repository
3. Configures environment variables
4. Sets up custom domains
"""

import os
import sys
import json
import argparse
import requests
from config import SITES, GITHUB_ORG

RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"


class RailwayClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _query(self, query, variables=None):
        """Execute a GraphQL query"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            RAILWAY_API_URL,
            headers=self.headers,
            json=payload
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None

        data = response.json()
        if "errors" in data:
            print(f"GraphQL Error: {data['errors']}")
            return None

        return data.get("data")

    def get_user(self):
        """Get current user info"""
        query = """
        query {
            me {
                id
                email
                name
            }
        }
        """
        return self._query(query)

    def list_projects(self):
        """List all projects"""
        query = """
        query {
            projects {
                edges {
                    node {
                        id
                        name
                        description
                        services {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        return self._query(query)

    def create_project(self, name, description=""):
        """Create a new project"""
        query = """
        mutation($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                id
                name
            }
        }
        """
        variables = {
            "input": {
                "name": name,
                "description": description
            }
        }
        return self._query(query, variables)

    def create_service_from_github(self, project_id, repo_name, branch="main"):
        """Create a service linked to a GitHub repo"""
        # First need to get the GitHub repo ID from Railway's perspective
        query = """
        mutation($input: ServiceCreateInput!) {
            serviceCreate(input: $input) {
                id
                name
            }
        }
        """

        repo_full_name = f"{GITHUB_ORG}/{repo_name}" if GITHUB_ORG else repo_name

        variables = {
            "input": {
                "projectId": project_id,
                "source": {
                    "repo": repo_full_name
                },
                "branch": branch
            }
        }
        return self._query(query, variables)

    def add_custom_domain(self, service_id, domain):
        """Add a custom domain to a service"""
        query = """
        mutation($input: CustomDomainCreateInput!) {
            customDomainCreate(input: $input) {
                id
                domain
                status {
                    dnsRecords {
                        type
                        hostlabel
                        value
                    }
                }
            }
        }
        """
        variables = {
            "input": {
                "serviceId": service_id,
                "domain": domain
            }
        }
        return self._query(query, variables)

    def set_env_variable(self, service_id, name, value):
        """Set an environment variable"""
        query = """
        mutation($input: VariableUpsertInput!) {
            variableUpsert(input: $input)
        }
        """
        variables = {
            "input": {
                "serviceId": service_id,
                "name": name,
                "value": value
            }
        }
        return self._query(query, variables)


def setup_all_sites(token, dry_run=False):
    """Set up Railway projects for all sites"""
    client = RailwayClient(token)

    # Verify connection
    user = client.get_user()
    if not user:
        print("Failed to authenticate with Railway")
        return False

    print(f"Authenticated as: {user['me']['email']}")

    # Get existing projects
    existing = client.list_projects()
    existing_names = []
    if existing and existing.get('projects'):
        existing_names = [
            p['node']['name']
            for p in existing['projects']['edges']
        ]

    results = {}

    for site_key, site_config in SITES.items():
        project_name = site_config['name']
        print(f"\n{'='*50}")
        print(f"Setting up: {project_name}")
        print(f"Domain: {site_config['domain']}")
        print(f"{'='*50}")

        if project_name in existing_names:
            print(f"  Project '{project_name}' already exists, skipping creation")
            # TODO: Get existing project ID
            continue

        if dry_run:
            print(f"  [DRY RUN] Would create project: {project_name}")
            print(f"  [DRY RUN] Would link to GitHub: {site_config['github_repo']}")
            print(f"  [DRY RUN] Would add domain: {site_config['domain']}")
            continue

        # Create project
        print(f"  Creating project...")
        project_result = client.create_project(
            project_name,
            site_config['description']
        )

        if not project_result:
            print(f"  Failed to create project")
            results[site_key] = {"status": "failed", "step": "create_project"}
            continue

        project_id = project_result['projectCreate']['id']
        print(f"  Project created: {project_id}")

        # Create service from GitHub
        print(f"  Linking to GitHub repo: {site_config['github_repo']}...")
        service_result = client.create_service_from_github(
            project_id,
            site_config['github_repo']
        )

        if not service_result:
            print(f"  Failed to create service")
            results[site_key] = {"status": "failed", "step": "create_service"}
            continue

        service_id = service_result['serviceCreate']['id']
        print(f"  Service created: {service_id}")

        # Add custom domain
        print(f"  Adding custom domain: {site_config['domain']}...")
        domain_result = client.add_custom_domain(service_id, site_config['domain'])

        if domain_result:
            print(f"  Domain added successfully")
            dns_records = domain_result.get('customDomainCreate', {}).get('status', {}).get('dnsRecords', [])
            if dns_records:
                print(f"  DNS Records needed:")
                for record in dns_records:
                    print(f"    {record['type']} {record['hostlabel']} -> {record['value']}")

        results[site_key] = {
            "status": "success",
            "project_id": project_id,
            "service_id": service_id
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Set up Railway projects for Audio Tools Network")
    parser.add_argument("--token", required=True, help="Railway API token")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--list", action="store_true", help="List existing projects")

    args = parser.parse_args()

    client = RailwayClient(args.token)

    if args.list:
        projects = client.list_projects()
        if projects:
            print("Existing projects:")
            for p in projects['projects']['edges']:
                print(f"  - {p['node']['name']} ({p['node']['id']})")
        return

    results = setup_all_sites(args.token, dry_run=args.dry_run)

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)

    if isinstance(results, dict):
        for site, result in results.items():
            status = result.get('status', 'unknown')
            print(f"  {site}: {status}")


if __name__ == "__main__":
    main()
