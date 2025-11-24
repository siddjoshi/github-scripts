#!/usr/bin/env python3
"""
GitHub Enterprise Organization Report Generator

This script generates a CSV report listing all organizations in a GitHub Enterprise
with their member counts and repository counts.
"""

import os
import sys
import csv
import argparse
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent
    env_file = script_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"📋 Loaded configuration from: {env_file}")
    else:
        load_dotenv()
except ImportError:
    print("💡 Tip: Install python-dotenv to use .env files: pip install python-dotenv")

# Detect if running in GitHub Actions
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'

if IS_GITHUB_ACTIONS:
    print("🤖 Running in GitHub Actions environment")

# Configuration
# In GitHub Actions, use ENTERPRISE_GITHUB_TOKEN to avoid conflict with pre-defined GITHUB_TOKEN
if IS_GITHUB_ACTIONS:
    GITHUB_TOKEN = os.getenv('ENTERPRISE_GITHUB_TOKEN')
else:
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

API_URL = os.getenv('GITHUB_API_URL', 'https://api.github.com')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '.')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
RATE_LIMIT_THRESHOLD = int(os.getenv('RATE_LIMIT_THRESHOLD', '10'))
API_DELAY = float(os.getenv('API_DELAY', '0.1'))


def debug_print(message: str) -> None:
    """Print debug messages if debug mode is enabled"""
    if DEBUG:
        print(f"🐛 DEBUG: {message}")


def get_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests"""
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN not found!")
        print("   Please set it as an environment variable or in a .env file")
        print("   Example: GITHUB_TOKEN=your_token_here")
        print("   Get your token from: https://github.com/settings/tokens")
        print("   Note: Token must have 'admin:enterprise' scope to access enterprise data")
        sys.exit(1)
    
    debug_print(f"Using API URL: {API_URL}")
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }


def check_rate_limit(headers: Dict[str, str]) -> None:
    """Check GitHub API rate limit and wait if necessary"""
    try:
        response = requests.get(f"{API_URL}/rate_limit", headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            remaining = data['rate']['remaining']
            reset_time = data['rate']['reset']
            
            debug_print(f"Rate limit: {remaining} requests remaining")
            
            if remaining < RATE_LIMIT_THRESHOLD:
                wait_time = reset_time - int(time.time()) + 5
                if wait_time > 0:
                    print(f"⏳ Rate limit nearly exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
    except Exception as e:
        debug_print(f"Could not check rate limit: {e}")


def get_enterprise_organizations(enterprise_slug: str, headers: Dict[str, str]) -> List[Dict]:
    """
    Fetch all organizations from a GitHub Enterprise
    
    Args:
        enterprise_slug: The enterprise slug/name
        headers: Request headers with authentication
    
    Returns:
        List of organization dictionaries
    """
    organizations = []
    page = 1
    
    print(f"🏢 Fetching organizations for enterprise: {enterprise_slug}")
    
    while True:
        check_rate_limit(headers)
        url = f"{API_URL}/enterprises/{enterprise_slug}/organizations"
        params = {
            'per_page': 100,
            'page': page
        }
        
        debug_print(f"Fetching orgs page {page}: {url}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 404:
                print(f"❌ Error: Enterprise '{enterprise_slug}' not found or not accessible")
                print("   Make sure the enterprise slug is correct and your token has 'admin:enterprise' scope")
                print(f"   API URL used: {url}")
                print(f"   Status code: {response.status_code}")
                if DEBUG:
                    print(f"   Response: {response.text}")
                
                # Try alternative: check if it's an organization instead
                print(f"\n💡 Attempting to treat '{enterprise_slug}' as a single organization...")
                org_url = f"{API_URL}/orgs/{enterprise_slug}"
                debug_print(f"Trying organization endpoint: {org_url}")
                
                org_response = requests.get(org_url, headers=headers, timeout=30)
                if org_response.status_code == 200:
                    print(f"   ✅ Found as organization (not enterprise)")
                    org_data = org_response.json()
                    return [org_data]
                else:
                    print(f"   ❌ Also not found as organization")
                    debug_print(f"   Org check status: {org_response.status_code}")
                
                return []
            elif response.status_code == 403:
                print(f"❌ Error: Access forbidden. Your token may not have the required permissions")
                print("   Required scope: 'admin:enterprise' or 'read:enterprise'")
                print(f"   Response: {response.text}")
                return []
            elif response.status_code != 200:
                print(f"❌ Error fetching organizations: {response.status_code}")
                print(f"   Response: {response.text}")
                return []
                
            data = response.json()
            
            # Handle both paginated responses and direct arrays
            if isinstance(data, dict) and 'organizations' in data:
                orgs = data['organizations']
            elif isinstance(data, list):
                orgs = data
            else:
                print(f"❌ Unexpected API response format")
                debug_print(f"Response data: {data}")
                return []
            
            if not orgs:
                break
                
            organizations.extend(orgs)
            print(f"   📄 Fetched page {page}, total organizations so far: {len(organizations)}")
            page += 1
            time.sleep(API_DELAY)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching organizations: {e}")
            break
    
    debug_print(f"Total organizations found: {len(organizations)}")
    return organizations


def get_organization_member_count(org_login: str, headers: Dict[str, str]) -> int:
    """
    Get the number of members in an organization
    
    Args:
        org_login: Organization login name
        headers: Request headers with authentication
    
    Returns:
        Number of members in the organization
    """
    check_rate_limit(headers)
    
    # First try to get it from organization details
    url = f"{API_URL}/orgs/{org_login}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # Some API versions include member count in org details
            if 'total_members' in data:
                return data['total_members']
            # For GitHub Enterprise, try public_members + private calculation
            # We need to actually count members
            pass
        else:
            debug_print(f"Could not fetch org details for {org_login}: {response.status_code}")
    except requests.exceptions.RequestException as e:
        debug_print(f"Error fetching org details for {org_login}: {e}")
    
    # Count members by paginating through members list
    member_count = 0
    page = 1
    
    while True:
        check_rate_limit(headers)
        url = f"{API_URL}/orgs/{org_login}/members"
        params = {
            'per_page': 100,
            'page': page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                debug_print(f"Could not fetch members for {org_login}: {response.status_code}")
                break
                
            members = response.json()
            if not members:
                break
                
            member_count += len(members)
            page += 1
            time.sleep(API_DELAY)
            
        except requests.exceptions.RequestException as e:
            debug_print(f"Error fetching members for {org_login}: {e}")
            break
    
    return member_count


def get_organization_repo_count(org_login: str, headers: Dict[str, str]) -> int:
    """
    Get the number of repositories in an organization
    
    Args:
        org_login: Organization login name
        headers: Request headers with authentication
    
    Returns:
        Number of repositories in the organization
    """
    check_rate_limit(headers)
    
    # Try to get it from organization details first
    url = f"{API_URL}/orgs/{org_login}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            # The org details include public_repos count
            if 'public_repos' in data:
                public_repos = data['public_repos']
                # For a complete count, we still need to count all repos
                # including private ones
                debug_print(f"Org {org_login} has {public_repos} public repos (counting all)")
        else:
            debug_print(f"Could not fetch org details for {org_login}: {response.status_code}")
    except requests.exceptions.RequestException as e:
        debug_print(f"Error fetching org details for {org_login}: {e}")
    
    # Count all repositories (public + private)
    repo_count = 0
    page = 1
    
    while True:
        check_rate_limit(headers)
        url = f"{API_URL}/orgs/{org_login}/repos"
        params = {
            'per_page': 100,
            'page': page,
            'type': 'all'  # Include public and private
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                debug_print(f"Could not fetch repos for {org_login}: {response.status_code}")
                break
                
            repos = response.json()
            if not repos:
                break
                
            repo_count += len(repos)
            page += 1
            time.sleep(API_DELAY)
            
        except requests.exceptions.RequestException as e:
            debug_print(f"Error fetching repos for {org_login}: {e}")
            break
    
    return repo_count


def generate_enterprise_report(enterprise_slug: str, output_file: Optional[str] = None) -> List[Dict]:
    """
    Generate a report of all organizations in an enterprise
    
    Args:
        enterprise_slug: The enterprise slug/name
        output_file: Optional CSV file path to save the report
    
    Returns:
        List of organization data dictionaries
    """
    headers = get_headers()
    
    print(f"\n🔍 Generating report for GitHub Enterprise: {enterprise_slug}")
    print("=" * 70)
    
    # Get all organizations
    organizations = get_enterprise_organizations(enterprise_slug, headers)
    
    if not organizations:
        print("❌ No organizations found or unable to access enterprise")
        return []
    
    print(f"\n📊 Found {len(organizations)} organizations")
    print("🔄 Fetching member and repository counts for each organization...\n")
    
    report_data = []
    
    for i, org in enumerate(organizations, 1):
        org_login = org.get('login', 'Unknown')
        print(f"[{i}/{len(organizations)}] Processing: {org_login}")
        
        # Get member count
        member_count = get_organization_member_count(org_login, headers)
        print(f"   👥 Members: {member_count}")
        
        # Get repository count
        repo_count = get_organization_repo_count(org_login, headers)
        print(f"   📚 Repositories: {repo_count}")
        
        report_data.append({
            'organization_name': org_login,
            'member_count': member_count,
            'repository_count': repo_count
        })
        
        print()
    
    # Print summary
    print("=" * 70)
    print("📈 REPORT SUMMARY")
    print("=" * 70)
    print(f"Enterprise: {enterprise_slug}")
    print(f"Total Organizations: {len(report_data)}")
    print(f"Total Members: {sum(org['member_count'] for org in report_data)}")
    print(f"Total Repositories: {sum(org['repository_count'] for org in report_data)}")
    
    # Save to CSV if output file specified
    if output_file:
        try:
            output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['organization_name', 'member_count', 'repository_count']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for org_data in report_data:
                    writer.writerow(org_data)
            
            print(f"\n✅ Report saved to: {output_path}")
            
        except Exception as e:
            print(f"\n❌ Error saving CSV file: {e}")
    else:
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"enterprise_org_report_{enterprise_slug}_{timestamp}.csv"
        output_path = Path(OUTPUT_DIR) / default_filename
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['organization_name', 'member_count', 'repository_count']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for org_data in report_data:
                    writer.writerow(org_data)
            
            print(f"\n✅ Report saved to: {output_path}")
            
        except Exception as e:
            print(f"\n❌ Error saving CSV file: {e}")
    
    return report_data


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate a CSV report of GitHub Enterprise organizations with member and repo counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python enterprise_org_report.py my-enterprise
  python enterprise_org_report.py my-enterprise --output report.csv
  python enterprise_org_report.py my-enterprise --debug

Environment variables (can be set in .env file):
  GITHUB_TOKEN: Required GitHub personal access token (must have 'admin:enterprise' or 'read:enterprise' scope)
  GITHUB_API_URL: GitHub API base URL (default: {API_URL})
  OUTPUT_DIR: Default output directory (default: {OUTPUT_DIR})
  DEBUG: Enable debug mode (true/false, default: false)
  RATE_LIMIT_THRESHOLD: Rate limit threshold (default: {RATE_LIMIT_THRESHOLD})
  API_DELAY: Delay between API requests in seconds (default: {API_DELAY})

CSV Output Format:
  organization_name,member_count,repository_count
  org1,25,150
  org2,10,75
        """
    )
    
    parser.add_argument('enterprise', 
                       help='GitHub Enterprise slug/name')
    parser.add_argument('--output', '-o', 
                       help='Output CSV file path (default: auto-generated with timestamp)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Enable debug mode for verbose output')
    
    args = parser.parse_args()
    
    # Override debug mode if specified via command line
    if args.debug:
        global DEBUG
        DEBUG = True
        debug_print("Debug mode enabled via command line")
    
    debug_print(f"Configuration:")
    debug_print(f"  Enterprise: {args.enterprise}")
    debug_print(f"  Output file: {args.output}")
    debug_print(f"  API URL: {API_URL}")
    debug_print(f"  Output directory: {OUTPUT_DIR}")
    
    try:
        report_data = generate_enterprise_report(
            enterprise_slug=args.enterprise,
            output_file=args.output
        )
        
        if not report_data:
            print("\n❌ No data generated")
            sys.exit(1)
        
        print("\n✨ Report generation completed successfully!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Report generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
