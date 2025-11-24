#!/usr/bin/env python3
"""
GitHub Enterprise Organization Members List Generator

This script generates a comprehensive report listing all organizations in a GitHub Enterprise
along with detailed member information for each organization.
"""

import os
import sys
import json
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
OUTPUT_FORMAT = os.getenv('OUTPUT_FORMAT', 'markdown')  # markdown, json, text, html
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
        print("   Note: Token must have 'admin:enterprise' or 'read:enterprise' scope")
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
            
            debug_print(f"Response type: {type(data)}")
            debug_print(f"Response keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
            
            # Handle both paginated responses and direct arrays
            if isinstance(data, dict) and 'organizations' in data:
                orgs = data['organizations']
            elif isinstance(data, list):
                orgs = data
            else:
                print(f"❌ Unexpected API response format")
                debug_print(f"Response data: {data}")
                return []
            
            debug_print(f"Found {len(orgs)} organizations on this page")
            
            if not orgs:
                debug_print("No organizations in this page, stopping pagination")
                break
                
            organizations.extend(orgs)
            print(f"   📄 Fetched page {page}, total organizations so far: {len(organizations)}")
            
            # Check if there are more pages
            # GitHub API indicates no more pages when we get fewer results than per_page
            if len(orgs) < params['per_page']:
                debug_print(f"Received {len(orgs)} orgs (less than {params['per_page']}), no more pages")
                break
            
            page += 1
            time.sleep(API_DELAY)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching organizations: {e}")
            break
    
    debug_print(f"Total organizations found: {len(organizations)}")
    return organizations


def get_organization_members(org_login: str, headers: Dict[str, str]) -> List[Dict]:
    """
    Get all members of an organization with their details
    
    Args:
        org_login: Organization login name
        headers: Request headers with authentication
    
    Returns:
        List of member dictionaries with user details
    """
    members = []
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
                
            page_members = response.json()
            if not page_members:
                break
            
            # Enrich member data with additional details
            for member in page_members:
                member_data = {
                    'login': member.get('login', 'Unknown'),
                    'id': member.get('id', ''),
                    'type': member.get('type', 'User'),
                    'site_admin': member.get('site_admin', False),
                    'profile_url': member.get('html_url', ''),
                    'avatar_url': member.get('avatar_url', '')
                }
                
                # Optionally fetch additional user details
                if DEBUG:
                    user_details = get_user_details(member['login'], headers)
                    if user_details:
                        member_data.update({
                            'name': user_details.get('name', ''),
                            'email': user_details.get('email', ''),
                            'company': user_details.get('company', ''),
                            'location': user_details.get('location', '')
                        })
                
                members.append(member_data)
            
            page += 1
            time.sleep(API_DELAY)
            
        except requests.exceptions.RequestException as e:
            debug_print(f"Error fetching members for {org_login}: {e}")
            break
    
    return members


def get_user_details(username: str, headers: Dict[str, str]) -> Optional[Dict]:
    """
    Get detailed information about a user
    
    Args:
        username: GitHub username
        headers: Request headers with authentication
    
    Returns:
        User details dictionary or None
    """
    check_rate_limit(headers)
    url = f"{API_URL}/users/{username}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            debug_print(f"Could not fetch user details for {username}: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        debug_print(f"Error fetching user details for {username}: {e}")
        return None


def generate_markdown_report(enterprise_slug: str, org_data: List[Dict], output_file: str) -> None:
    """Generate a Markdown formatted report"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# GitHub Enterprise Organization Members Report\n\n")
        f.write(f"**Enterprise:** {enterprise_slug}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Organizations:** {len(org_data)}\n\n")
        
        total_members = sum(org['member_count'] for org in org_data)
        f.write(f"**Total Members:** {total_members}\n\n")
        
        f.write("---\n\n")
        
        # Table of Contents
        f.write("## Table of Contents\n\n")
        for i, org in enumerate(org_data, 1):
            anchor = org['organization_name'].lower().replace(' ', '-')
            f.write(f"{i}. [{org['organization_name']}](#{anchor}) ({org['member_count']} members)\n")
        f.write("\n---\n\n")
        
        # Organization details
        for org in org_data:
            f.write(f"## {org['organization_name']}\n\n")
            f.write(f"**Member Count:** {org['member_count']}\n\n")
            
            if org['members']:
                f.write("### Members\n\n")
                f.write("| # | Username | Type | Profile |\n")
                f.write("|---|----------|------|----------|\n")
                
                for i, member in enumerate(org['members'], 1):
                    username = member['login']
                    member_type = member.get('type', 'User')
                    profile_url = member.get('profile_url', '')
                    
                    f.write(f"| {i} | `{username}` | {member_type} | [Profile]({profile_url}) |\n")
                
                f.write("\n")
            else:
                f.write("*No members found or unable to access member list.*\n\n")
            
            f.write("---\n\n")
        
        # Summary footer
        f.write("## Summary\n\n")
        f.write(f"- **Total Organizations:** {len(org_data)}\n")
        f.write(f"- **Total Members:** {total_members}\n")
        f.write(f"- **Average Members per Organization:** {total_members / len(org_data) if org_data else 0:.1f}\n")


def generate_text_report(enterprise_slug: str, org_data: List[Dict], output_file: str) -> None:
    """Generate a plain text formatted report"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("GITHUB ENTERPRISE ORGANIZATION MEMBERS REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Enterprise: {enterprise_slug}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Organizations: {len(org_data)}\n")
        
        total_members = sum(org['member_count'] for org in org_data)
        f.write(f"Total Members: {total_members}\n\n")
        
        f.write("=" * 80 + "\n\n")
        
        # Organization details
        for i, org in enumerate(org_data, 1):
            f.write(f"[{i}] ORGANIZATION: {org['organization_name']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Member Count: {org['member_count']}\n\n")
            
            if org['members']:
                f.write("MEMBERS:\n\n")
                
                for j, member in enumerate(org['members'], 1):
                    username = member['login']
                    member_type = member.get('type', 'User')
                    profile_url = member.get('profile_url', '')
                    
                    f.write(f"  {j:3d}. {username}\n")
                    f.write(f"       Type: {member_type}\n")
                    f.write(f"       Profile: {profile_url}\n\n")
            else:
                f.write("No members found or unable to access member list.\n\n")
            
            f.write("\n")
        
        # Summary footer
        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Organizations: {len(org_data)}\n")
        f.write(f"Total Members: {total_members}\n")
        f.write(f"Average Members per Organization: {total_members / len(org_data) if org_data else 0:.1f}\n")


def generate_json_report(enterprise_slug: str, org_data: List[Dict], output_file: str) -> None:
    """Generate a JSON formatted report"""
    
    total_members = sum(org['member_count'] for org in org_data)
    
    report = {
        'enterprise': enterprise_slug,
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_organizations': len(org_data),
            'total_members': total_members,
            'average_members_per_org': total_members / len(org_data) if org_data else 0
        },
        'organizations': org_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_html_report(enterprise_slug: str, org_data: List[Dict], output_file: str) -> None:
    """Generate an HTML formatted report"""
    
    total_members = sum(org['member_count'] for org in org_data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # HTML Header
        f.write("<!DOCTYPE html>\n")
        f.write("<html lang=\"en\">\n")
        f.write("<head>\n")
        f.write("    <meta charset=\"UTF-8\">\n")
        f.write("    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n")
        f.write(f"    <title>GitHub Enterprise Organizations - {enterprise_slug}</title>\n")
        f.write("    <style>\n")
        f.write("        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f6f8fa; }\n")
        f.write("        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }\n")
        f.write("        h1 { color: #24292e; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }\n")
        f.write("        h2 { color: #0366d6; margin-top: 30px; }\n")
        f.write("        .summary { background: #f6f8fa; padding: 20px; border-radius: 6px; margin: 20px 0; }\n")
        f.write("        .summary-item { margin: 10px 0; font-size: 16px; }\n")
        f.write("        .org-section { margin: 30px 0; padding: 20px; border: 1px solid #e1e4e8; border-radius: 6px; }\n")
        f.write("        .org-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }\n")
        f.write("        .member-count { background: #0366d6; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }\n")
        f.write("        table { width: 100%; border-collapse: collapse; margin-top: 15px; }\n")
        f.write("        th { background: #f6f8fa; text-align: left; padding: 12px; border-bottom: 2px solid #e1e4e8; }\n")
        f.write("        td { padding: 10px 12px; border-bottom: 1px solid #e1e4e8; }\n")
        f.write("        tr:hover { background: #f6f8fa; }\n")
        f.write("        a { color: #0366d6; text-decoration: none; }\n")
        f.write("        a:hover { text-decoration: underline; }\n")
        f.write("        .username { font-family: 'SFMono-Regular', Consolas, monospace; background: #f6f8fa; padding: 3px 6px; border-radius: 3px; }\n")
        f.write("        .toc { background: #fff8dc; padding: 20px; border-radius: 6px; margin: 20px 0; }\n")
        f.write("        .toc ul { list-style-type: none; padding-left: 0; }\n")
        f.write("        .toc li { margin: 8px 0; }\n")
        f.write("    </style>\n")
        f.write("</head>\n")
        f.write("<body>\n")
        f.write("    <div class=\"container\">\n")
        
        # Title
        f.write(f"        <h1>GitHub Enterprise Organization Members Report</h1>\n")
        
        # Summary
        f.write("        <div class=\"summary\">\n")
        f.write(f"            <div class=\"summary-item\"><strong>Enterprise:</strong> {enterprise_slug}</div>\n")
        f.write(f"            <div class=\"summary-item\"><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>\n")
        f.write(f"            <div class=\"summary-item\"><strong>Total Organizations:</strong> {len(org_data)}</div>\n")
        f.write(f"            <div class=\"summary-item\"><strong>Total Members:</strong> {total_members}</div>\n")
        f.write(f"            <div class=\"summary-item\"><strong>Average Members per Org:</strong> {total_members / len(org_data) if org_data else 0:.1f}</div>\n")
        f.write("        </div>\n")
        
        # Table of Contents
        f.write("        <div class=\"toc\">\n")
        f.write("            <h2>Table of Contents</h2>\n")
        f.write("            <ul>\n")
        for i, org in enumerate(org_data, 1):
            org_id = org['organization_name'].lower().replace(' ', '-').replace('.', '-')
            f.write(f"                <li>{i}. <a href=\"#{org_id}\">{org['organization_name']}</a> ({org['member_count']} members)</li>\n")
        f.write("            </ul>\n")
        f.write("        </div>\n")
        
        # Organizations
        for org in org_data:
            org_id = org['organization_name'].lower().replace(' ', '-').replace('.', '-')
            f.write(f"        <div class=\"org-section\" id=\"{org_id}\">\n")
            f.write("            <div class=\"org-header\">\n")
            f.write(f"                <h2>{org['organization_name']}</h2>\n")
            f.write(f"                <span class=\"member-count\">{org['member_count']} members</span>\n")
            f.write("            </div>\n")
            
            if org['members']:
                f.write("            <table>\n")
                f.write("                <thead>\n")
                f.write("                    <tr>\n")
                f.write("                        <th>#</th>\n")
                f.write("                        <th>Username</th>\n")
                f.write("                        <th>Type</th>\n")
                f.write("                        <th>Profile</th>\n")
                f.write("                    </tr>\n")
                f.write("                </thead>\n")
                f.write("                <tbody>\n")
                
                for i, member in enumerate(org['members'], 1):
                    username = member['login']
                    member_type = member.get('type', 'User')
                    profile_url = member.get('profile_url', '')
                    
                    f.write("                    <tr>\n")
                    f.write(f"                        <td>{i}</td>\n")
                    f.write(f"                        <td><span class=\"username\">{username}</span></td>\n")
                    f.write(f"                        <td>{member_type}</td>\n")
                    f.write(f"                        <td><a href=\"{profile_url}\" target=\"_blank\">View Profile</a></td>\n")
                    f.write("                    </tr>\n")
                
                f.write("                </tbody>\n")
                f.write("            </table>\n")
            else:
                f.write("            <p><em>No members found or unable to access member list.</em></p>\n")
            
            f.write("        </div>\n")
        
        # HTML Footer
        f.write("    </div>\n")
        f.write("</body>\n")
        f.write("</html>\n")


def generate_members_report(enterprise_slug: str, output_format: str = 'markdown', 
                          output_file: Optional[str] = None) -> List[Dict]:
    """
    Generate a comprehensive report of organizations and their members
    
    Args:
        enterprise_slug: The enterprise slug/name
        output_format: Output format (markdown, json, text, html)
        output_file: Optional file path to save the report
    
    Returns:
        List of organization data with members
    """
    headers = get_headers()
    
    print(f"\n🔍 Generating members report for GitHub Enterprise: {enterprise_slug}")
    print("=" * 70)
    
    # Get all organizations
    organizations = get_enterprise_organizations(enterprise_slug, headers)
    
    if not organizations:
        print("❌ No organizations found or unable to access enterprise")
        return []
    
    print(f"\n📊 Found {len(organizations)} organizations")
    print("🔄 Fetching member lists for each organization...\n")
    
    report_data = []
    
    for i, org in enumerate(organizations, 1):
        org_login = org.get('login', 'Unknown')
        print(f"[{i}/{len(organizations)}] Processing: {org_login}")
        
        # Get members
        members = get_organization_members(org_login, headers)
        print(f"   👥 Found {len(members)} members")
        
        report_data.append({
            'organization_name': org_login,
            'member_count': len(members),
            'members': members
        })
        
        print()
    
    # Generate output file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension_map = {
            'markdown': 'md',
            'json': 'json',
            'text': 'txt',
            'html': 'html'
        }
        extension = extension_map.get(output_format, 'txt')
        output_file = f"enterprise_members_{enterprise_slug}_{timestamp}.{extension}"
    
    output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate report based on format
    print("=" * 70)
    print(f"📝 Generating {output_format.upper()} report...")
    
    if output_format == 'markdown':
        generate_markdown_report(enterprise_slug, report_data, output_path)
    elif output_format == 'json':
        generate_json_report(enterprise_slug, report_data, output_path)
    elif output_format == 'text':
        generate_text_report(enterprise_slug, report_data, output_path)
    elif output_format == 'html':
        generate_html_report(enterprise_slug, report_data, output_path)
    else:
        print(f"❌ Unknown output format: {output_format}")
        return report_data
    
    # Print summary
    total_members = sum(org['member_count'] for org in report_data)
    print("\n" + "=" * 70)
    print("📈 REPORT SUMMARY")
    print("=" * 70)
    print(f"Enterprise: {enterprise_slug}")
    print(f"Total Organizations: {len(report_data)}")
    print(f"Total Members: {total_members}")
    print(f"Average Members per Organization: {total_members / len(report_data) if report_data else 0:.1f}")
    print(f"\n✅ Report saved to: {output_path}")
    
    return report_data


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate a comprehensive report of GitHub Enterprise organizations and their members",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python org_members_list.py my-enterprise
  python org_members_list.py my-enterprise --format html
  python org_members_list.py my-enterprise --format json --output report.json
  python org_members_list.py my-enterprise --format markdown --debug

Output Formats:
  markdown  - Easy-to-read Markdown format with tables (default)
  html      - Interactive HTML page with styling
  json      - Machine-readable JSON format
  text      - Plain text format

Environment variables (can be set in .env file):
  GITHUB_TOKEN: Required GitHub personal access token (must have 'admin:enterprise' or 'read:enterprise' scope)
  GITHUB_API_URL: GitHub API base URL (default: {API_URL})
  OUTPUT_DIR: Default output directory (default: {OUTPUT_DIR})
  OUTPUT_FORMAT: Default output format (default: {OUTPUT_FORMAT})
  DEBUG: Enable debug mode (true/false, default: false)
  RATE_LIMIT_THRESHOLD: Rate limit threshold (default: {RATE_LIMIT_THRESHOLD})
  API_DELAY: Delay between API requests in seconds (default: {API_DELAY})
        """
    )
    
    parser.add_argument('enterprise', 
                       help='GitHub Enterprise slug/name')
    parser.add_argument('--format', '-f',
                       choices=['markdown', 'json', 'text', 'html'],
                       default=OUTPUT_FORMAT,
                       help=f'Output format (default: {OUTPUT_FORMAT})')
    parser.add_argument('--output', '-o', 
                       help='Output file path (default: auto-generated with timestamp)')
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
    debug_print(f"  Output format: {args.format}")
    debug_print(f"  Output file: {args.output}")
    debug_print(f"  API URL: {API_URL}")
    debug_print(f"  Output directory: {OUTPUT_DIR}")
    
    try:
        report_data = generate_members_report(
            enterprise_slug=args.enterprise,
            output_format=args.format,
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
