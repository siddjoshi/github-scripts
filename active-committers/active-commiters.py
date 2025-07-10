import requests
import time
import os
import sys
from datetime import datetime, timedelta
from typing import Set, List, Dict, Optional
import argparse
import json
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env file in the script directory
    script_dir = Path(__file__).parent
    env_file = script_dir / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"📋 Loaded configuration from: {env_file}")
    else:
        load_dotenv()  # Load from current directory or environment
except ImportError:
    print("💡 Tip: Install python-dotenv to use .env files: pip install python-dotenv")

# Configuration with environment variable support
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
API_URL = os.getenv('GITHUB_API_URL', 'https://api.github.com')
DEFAULT_DAYS = int(os.getenv('DEFAULT_DAYS', '365'))
DEFAULT_ORG = os.getenv('DEFAULT_ORG')
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
        response = requests.get(f"{API_URL}/rate_limit", headers=headers)
        if response.status_code == 200:
            data = response.json()
            remaining = data['rate']['remaining']
            reset_time = data['rate']['reset']
            
            debug_print(f"Rate limit: {remaining} requests remaining")
            
            if remaining < RATE_LIMIT_THRESHOLD:
                wait_time = reset_time - int(time.time()) + 5  # Add 5 seconds buffer
                if wait_time > 0:
                    print(f"⏳ Rate limit nearly exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
    except Exception as e:
        debug_print(f"Could not check rate limit: {e}")

def get_all_repos(org: str, headers: Dict[str, str]) -> List[Dict]:
    """Fetch all repositories from the organization"""
    repos = []
    page = 1
    
    print(f"📚 Fetching repositories for organization: {org}")
    
    while True:
        check_rate_limit(headers)
        url = f"{API_URL}/orgs/{org}/repos?per_page=100&page={page}&type=all"
        
        debug_print(f"Fetching repos page {page}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 404:
                print(f"❌ Error: Organization '{org}' not found or not accessible")
                print("   Make sure the organization name is correct and your token has the right permissions")
                return []
            elif response.status_code != 200:
                print(f"❌ Error fetching repos: {response.status_code} - {response.text}")
                break
                
            page_data = response.json()
            if not page_data:
                break
                
            repos.extend(page_data)
            print(f"   📄 Fetched page {page}, total repos so far: {len(repos)}")
            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error fetching repositories: {e}")
            break
    
    debug_print(f"Total repositories found: {len(repos)}")
    return repos

def get_active_contributors(owner: str, repo_name: str, headers: Dict[str, str], 
                          since_date: Optional[datetime] = None) -> Set[str]:
    """
    Fetch active contributors for a repository
    Active = contributors who have made commits since the specified date
    """
    contributors = set()
    
    if since_date is None:
        since_date = datetime.now() - timedelta(days=DEFAULT_DAYS)
    
    since_str = since_date.isoformat()
    page = 1
    
    while True:
        check_rate_limit(headers)
        # Get commits since the specified date
        url = f"{API_URL}/repos/{owner}/{repo_name}/commits"
        params = {
            'since': since_str,
            'per_page': 100,
            'page': page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 409:  # Repository is empty
                print(f"  Repository {repo_name} is empty")
                break
            elif response.status_code == 404:
                print(f"  Repository {repo_name} not found or not accessible")
                break
            elif response.status_code != 200:
                print(f"  Failed to fetch commits for {repo_name}: {response.status_code}")
                break
                
            commits = response.json()
            if not commits:
                break
            
            for commit in commits:
                # Get author information
                if commit.get('author') and commit['author'].get('login'):
                    contributors.add(commit['author']['login'])
                
                # Also check committer if different from author
                if (commit.get('committer') and 
                    commit['committer'].get('login') and 
                    commit['committer']['login'] != commit.get('author', {}).get('login')):
                    contributors.add(commit['committer']['login'])
            
            page += 1
            time.sleep(API_DELAY)  # Configurable delay between API requests
            
        except requests.exceptions.RequestException as e:
            print(f"  Network error fetching commits for {repo_name}: {e}")
            break
    
    return contributors

def get_repo_contributors_stats(owner: str, repo_name: str, headers: Dict[str, str]) -> Dict:
    """Get contributor statistics for a repository"""
    check_rate_limit(headers)
    url = f"{API_URL}/repos/{owner}/{repo_name}/stats/contributors"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 202:
            # GitHub is computing the statistics, wait and retry
            print(f"  Computing stats for {repo_name}, waiting...")
            time.sleep(3)
            response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Could not get stats for {repo_name}: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"  Network error getting stats for {repo_name}: {e}")
        return []

def analyze_organization_activity(org_name: str, days_back: int = DEFAULT_DAYS, 
                                include_stats: bool = False, output_file: Optional[str] = None) -> Dict:
    """
    Analyze active committers in a GitHub organization
    
    Args:
        org_name: GitHub organization name
        days_back: Number of days to look back for activity
        include_stats: Whether to include detailed statistics
        output_file: Optional file to save results
    
    Returns:
        Dictionary with analysis results
    """
    headers = get_headers()
    since_date = datetime.now() - timedelta(days=days_back)
    
    print(f"\n🔍 Analyzing GitHub organization: {org_name}")
    print(f"📅 Looking for activity since: {since_date.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # Get all repositories
    repos = get_all_repos(org_name, headers)
    if not repos:
        return {"error": "No repositories found or organization not accessible"}
    
    print(f"\n📚 Found {len(repos)} repositories")
    
    all_active_committers = set()
    repo_stats = {}
    
    for i, repo in enumerate(repos, 1):
        repo_name = repo['name']
        print(f"\n[{i}/{len(repos)}] 🔍 Analyzing repository: {repo_name}")
        
        # Get active contributors
        active_contributors = get_active_contributors(org_name, repo_name, headers, since_date)
        
        if active_contributors:
            all_active_committers.update(active_contributors)
            repo_stats[repo_name] = {
                'active_contributors': list(active_contributors),
                'active_count': len(active_contributors),
                'last_updated': repo.get('updated_at'),
                'language': repo.get('language'),
                'private': repo.get('private', False)
            }
            
            print(f"  ✅ Found {len(active_contributors)} active contributors")
            
            # Get detailed stats if requested
            if include_stats:
                stats = get_repo_contributors_stats(org_name, repo_name, headers)
                if stats:
                    repo_stats[repo_name]['detailed_stats'] = stats
        else:
            print(f"  ❌ No active contributors found")
    
    # Prepare results
    results = {
        'organization': org_name,
        'analysis_date': datetime.now().isoformat(),
        'days_analyzed': days_back,
        'since_date': since_date.isoformat(),
        'total_repositories': len(repos),
        'repositories_with_activity': len(repo_stats),
        'total_active_committers': len(all_active_committers),
        'active_committers': sorted(list(all_active_committers)),
        'repository_stats': repo_stats
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Organization: {org_name}")
    print(f"Total repositories: {len(repos)}")
    print(f"Repositories with activity: {len(repo_stats)}")
    print(f"Total active committers: {len(all_active_committers)}")
    print(f"Analysis period: Last {days_back} days")
    
    if all_active_committers:
        print(f"\n👥 Active committers:")
        for committer in sorted(all_active_committers):
            print(f"  • {committer}")
    
    # Save to file if requested
    if output_file:
        try:
            # Create output directory if it doesn't exist
            output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_path}")
        except Exception as e:
            print(f"\n❌ Error saving to file: {e}")
    
    return results

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Analyze active committers in a GitHub organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python active-commiters.py myorg
  python active-commiters.py myorg --days 90 --stats
  python active-commiters.py myorg --output results.json
  
Environment variables (can be set in .env file):
  GITHUB_TOKEN: Required GitHub personal access token
  DEFAULT_ORG: Default organization to analyze
  DEFAULT_DAYS: Default number of days to look back (default: {DEFAULT_DAYS})
  GITHUB_API_URL: GitHub API base URL (default: {API_URL})
  OUTPUT_DIR: Default output directory (default: {OUTPUT_DIR})
  DEBUG: Enable debug mode (true/false, default: false)
  RATE_LIMIT_THRESHOLD: Rate limit threshold (default: {RATE_LIMIT_THRESHOLD})
  API_DELAY: Delay between API requests (default: {API_DELAY})
        """
    )
    
    # Use DEFAULT_ORG from environment if available, otherwise make it required
    if DEFAULT_ORG:
        parser.add_argument('organization', 
                           nargs='?',
                           default=DEFAULT_ORG,
                           help=f'GitHub organization name to analyze (default from env: {DEFAULT_ORG})')
    else:
        parser.add_argument('organization', 
                           help='GitHub organization name to analyze')
    
    parser.add_argument('--days', '-d', 
                       type=int, 
                       default=DEFAULT_DAYS,
                       help=f'Number of days to look back for activity (default: {DEFAULT_DAYS})')
    parser.add_argument('--stats', '-s', 
                       action='store_true',
                       help='Include detailed contributor statistics')
    parser.add_argument('--output', '-o', 
                       help='Output file to save results (JSON format)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Enable debug mode for verbose output')
    
    args = parser.parse_args()
    
    # Override debug mode if specified via command line
    if args.debug:
        global DEBUG
        DEBUG = True
        debug_print("Debug mode enabled via command line")
    
    debug_print(f"Configuration loaded:")
    debug_print(f"  Organization: {args.organization}")
    debug_print(f"  Days back: {args.days}")
    debug_print(f"  Include stats: {args.stats}")
    debug_print(f"  Output file: {args.output}")
    debug_print(f"  API URL: {API_URL}")
    debug_print(f"  Output directory: {OUTPUT_DIR}")
    
    try:
        results = analyze_organization_activity(
            org_name=args.organization,
            days_back=args.days,
            include_stats=args.stats,
            output_file=args.output
        )
        
        if 'error' in results:
            print(f"\n❌ Error: {results['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
