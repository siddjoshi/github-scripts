#!/usr/bin/env python3
"""
GitHub Copilot Lines of Code Summary Reporter

This script calculates total lines of code added and deleted by GitHub Copilot
across the enterprise, providing both 28-day aggregated data and weekly breakdowns.
"""

import os
import sys
import csv
import json
import argparse
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

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

# Configuration
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
        print("   Note: Token must have 'manage_billing:copilot' or 'read:enterprise' scope")
        sys.exit(1)
    
    debug_print(f"Using API URL: {API_URL}")
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
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


def get_copilot_metrics_urls(enterprise: str, report_type: str, headers: Dict[str, str], 
                             specific_day: Optional[str] = None) -> Dict[str, Any]:
    """
    Get download URLs for Copilot usage metrics reports
    
    Args:
        enterprise: Enterprise slug
        report_type: 'enterprise' or 'users'
        headers: Request headers
        specific_day: Specific day in YYYY-MM-DD format (optional)
    
    Returns:
        Dictionary with download_links and report dates
    """
    check_rate_limit(headers)
    
    if specific_day:
        # Specific day endpoint
        url = f"{API_URL}/enterprises/{enterprise}/copilot/metrics/reports/{report_type}-1-day"
        params = {'day': specific_day}
    else:
        # Latest 28-day report
        url = f"{API_URL}/enterprises/{enterprise}/copilot/metrics/reports/{report_type}-28-day/latest"
        params = None
    
    debug_print(f"Fetching metrics URLs from: {url}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 404:
            print(f"❌ Error: Enterprise '{enterprise}' not found or metrics not available")
            print("   Make sure the enterprise slug is correct and your token has the required permissions")
            return {}
        elif response.status_code == 403:
            print(f"❌ Error: Access forbidden. Your token may not have the required permissions")
            print("   Required scope: 'manage_billing:copilot' or 'read:enterprise'")
            return {}
        elif response.status_code != 200:
            print(f"❌ Error fetching metrics URLs: {response.status_code}")
            print(f"   Response: {response.text}")
            return {}
        
        data = response.json()
        debug_print(f"Received metrics response: {json.dumps(data, indent=2)}")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching metrics URLs: {e}")
        return {}


def download_metrics_report(download_url: str) -> List[Dict]:
    """
    Download and parse NDJSON metrics report from signed URL
    
    Args:
        download_url: Signed URL to download the report
    
    Returns:
        List of parsed JSON records
    """
    debug_print(f"Downloading report from: {download_url}")
    
    try:
        time.sleep(API_DELAY)
        response = requests.get(download_url, timeout=60)
        
        if response.status_code != 200:
            print(f"⚠️  Error downloading report: {response.status_code}")
            return []
        
        # Parse NDJSON (newline-delimited JSON)
        records = []
        for line in response.text.strip().split('\n'):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    debug_print(f"Failed to parse line: {e}")
                    continue
        
        debug_print(f"Downloaded {len(records)} records")
        return records
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error downloading report: {e}")
        return []


def aggregate_loc_totals(records: List[Dict]) -> Dict[str, int]:
    """
    Aggregate total lines of code added and deleted across all features
    
    Args:
        records: List of NDJSON records
    
    Returns:
        Dictionary with total loc_added and loc_deleted
    """
    total_added = 0
    total_deleted = 0
    
    for record in records:
        for item in record.get('totals_by_language_feature', []):
            total_added += item.get('loc_added_sum', 0)
            total_deleted += item.get('loc_deleted_sum', 0)
    
    return {
        'loc_added': total_added,
        'loc_deleted': total_deleted
    }


def aggregate_loc_by_feature(records: List[Dict]) -> Dict[str, Dict[str, int]]:
    """
    Aggregate lines of code added and deleted by feature
    
    Args:
        records: List of NDJSON records
    
    Returns:
        Dictionary of feature -> {loc_added, loc_deleted}
    """
    feature_metrics = defaultdict(lambda: {
        'loc_added': 0,
        'loc_deleted': 0
    })
    
    for record in records:
        for item in record.get('totals_by_language_feature', []):
            feature = item.get('feature', 'unknown')
            feature_metrics[feature]['loc_added'] += item.get('loc_added_sum', 0)
            feature_metrics[feature]['loc_deleted'] += item.get('loc_deleted_sum', 0)
    
    return dict(feature_metrics)


def get_date_range_from_28day_report(report_start_day: str, report_end_day: str) -> List[str]:
    """
    Generate list of dates in YYYY-MM-DD format for the 28-day period
    
    Args:
        report_start_day: Start date in YYYY-MM-DD format
        report_end_day: End date in YYYY-MM-DD format
    
    Returns:
        List of date strings
    """
    start_date = datetime.strptime(report_start_day, '%Y-%m-%d')
    end_date = datetime.strptime(report_end_day, '%Y-%m-%d')
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    return dates


def calculate_weekly_breakdown(enterprise: str, headers: Dict[str, str], 
                               report_start_day: str, report_end_day: str) -> Dict[str, Dict]:
    """
    Calculate weekly breakdown by fetching daily reports and aggregating
    
    Args:
        enterprise: Enterprise slug
        headers: Request headers
        report_start_day: Start date of 28-day period
        report_end_day: End date of 28-day period
    
    Returns:
        Dictionary with weekly totals and per-feature weekly totals
    """
    dates = get_date_range_from_28day_report(report_start_day, report_end_day)
    
    print(f"\n📅 Fetching daily reports for {len(dates)} days...")
    print("   This may take a few minutes due to API rate limits...")
    
    # Initialize weekly aggregators
    weekly_totals = {
        'Week 1': {'loc_added': 0, 'loc_deleted': 0},
        'Week 2': {'loc_added': 0, 'loc_deleted': 0},
        'Week 3': {'loc_added': 0, 'loc_deleted': 0},
        'Week 4': {'loc_added': 0, 'loc_deleted': 0}
    }
    
    weekly_feature_totals = {
        'Week 1': defaultdict(lambda: {'loc_added': 0, 'loc_deleted': 0}),
        'Week 2': defaultdict(lambda: {'loc_added': 0, 'loc_deleted': 0}),
        'Week 3': defaultdict(lambda: {'loc_added': 0, 'loc_deleted': 0}),
        'Week 4': defaultdict(lambda: {'loc_added': 0, 'loc_deleted': 0})
    }
    
    # Fetch daily reports
    for i, day in enumerate(dates, 1):
        # Determine which week (0-indexed: 0-6 = Week 1, 7-13 = Week 2, etc.)
        week_num = min((i - 1) // 7, 3)  # Cap at Week 4 (index 3)
        week_key = f'Week {week_num + 1}'
        
        print(f"   [{i}/{len(dates)}] Fetching data for {day} ({week_key})...", end='\r')
        
        # Get daily report
        metrics_info = get_copilot_metrics_urls(enterprise, 'users', headers, specific_day=day)
        
        if not metrics_info or not metrics_info.get('download_links'):
            debug_print(f"No data available for {day}")
            continue
        
        # Download and process each file for this day
        for download_url in metrics_info.get('download_links', []):
            records = download_metrics_report(download_url)
            
            # Aggregate totals for this day
            day_totals = aggregate_loc_totals(records)
            weekly_totals[week_key]['loc_added'] += day_totals['loc_added']
            weekly_totals[week_key]['loc_deleted'] += day_totals['loc_deleted']
            
            # Aggregate by feature for this day
            day_features = aggregate_loc_by_feature(records)
            for feature, metrics in day_features.items():
                weekly_feature_totals[week_key][feature]['loc_added'] += metrics['loc_added']
                weekly_feature_totals[week_key][feature]['loc_deleted'] += metrics['loc_deleted']
        
        # Small delay to respect rate limits
        time.sleep(API_DELAY)
    
    print(f"\n✅ Completed fetching daily reports")
    
    # Convert defaultdicts to regular dicts
    for week in weekly_feature_totals:
        weekly_feature_totals[week] = dict(weekly_feature_totals[week])
    
    return {
        'weekly_totals': weekly_totals,
        'weekly_feature_totals': weekly_feature_totals
    }


def generate_summary_report(enterprise: str, output_file: Optional[str] = None) -> Dict:
    """
    Generate Copilot LoC summary report with 28-day and weekly breakdowns
    
    Args:
        enterprise: Enterprise slug
        output_file: Optional output file path
    
    Returns:
        Dictionary with report data
    """
    headers = get_headers()
    
    print(f"\n🔍 Fetching GitHub Copilot LoC summary for enterprise: {enterprise}")
    print("=" * 70)
    
    # Get 28-day metrics
    print("\n📊 Fetching 28-day aggregated metrics...")
    metrics_info = get_copilot_metrics_urls(enterprise, 'users', headers)
    
    if not metrics_info:
        print("❌ Failed to fetch metrics information")
        return {}
    
    download_links = metrics_info.get('download_links', [])
    if not download_links:
        print("❌ No download links available")
        return {}
    
    start_day = metrics_info.get('report_start_day', 'unknown')
    end_day = metrics_info.get('report_end_day', 'unknown')
    print(f"📅 Report period: {start_day} to {end_day}")
    
    # Download and aggregate 28-day reports
    print(f"\n📥 Downloading {len(download_links)} report file(s)...")
    all_records = []
    for i, url in enumerate(download_links, 1):
        print(f"   [{i}/{len(download_links)}] Downloading report...")
        records = download_metrics_report(url)
        all_records.extend(records)
    
    print(f"✅ Downloaded {len(all_records)} total user records")
    
    if not all_records:
        print("❌ No data available in reports")
        return {}
    
    # Calculate 28-day totals
    print("\n📊 Calculating 28-day totals...")
    total_28day = aggregate_loc_totals(all_records)
    feature_28day = aggregate_loc_by_feature(all_records)
    
    # Calculate weekly breakdowns
    print("\n📊 Calculating weekly breakdowns...")
    weekly_data = calculate_weekly_breakdown(enterprise, headers, start_day, end_day)
    
    # Prepare report data
    report_data = {
        'enterprise': enterprise,
        'report_start_day': start_day,
        'report_end_day': end_day,
        'generated_at': datetime.now().isoformat(),
        'total_users': len(set(r.get('user_login', '') for r in all_records)),
        '28day_totals': total_28day,
        '28day_feature_totals': feature_28day,
        'weekly_totals': weekly_data['weekly_totals'],
        'weekly_feature_totals': weekly_data['weekly_feature_totals']
    }
    
    # Print summary
    print("\n" + "=" * 70)
    print("📈 LINES OF CODE SUMMARY")
    print("=" * 70)
    print(f"Enterprise: {enterprise}")
    print(f"Report Period: {start_day} to {end_day}")
    print(f"Total users: {report_data['total_users']}")
    
    print(f"\n📊 28-Day Totals (All Features):")
    print(f"   Lines Added: {total_28day['loc_added']:,}")
    print(f"   Lines Deleted: {total_28day['loc_deleted']:,}")
    print(f"   Net Change: {total_28day['loc_added'] - total_28day['loc_deleted']:,}")
    
    print(f"\n📅 Weekly Totals (All Features):")
    for week in ['Week 1', 'Week 2', 'Week 3', 'Week 4']:
        week_data = weekly_data['weekly_totals'][week]
        net = week_data['loc_added'] - week_data['loc_deleted']
        print(f"   {week}:")
        print(f"      Lines Added: {week_data['loc_added']:,}")
        print(f"      Lines Deleted: {week_data['loc_deleted']:,}")
        print(f"      Net Change: {net:,}")
    
    print(f"\n📊 28-Day Totals by Feature:")
    for feature in sorted(feature_28day.keys()):
        metrics = feature_28day[feature]
        net = metrics['loc_added'] - metrics['loc_deleted']
        print(f"   {feature}:")
        print(f"      Lines Added: {metrics['loc_added']:,}")
        print(f"      Lines Deleted: {metrics['loc_deleted']:,}")
        print(f"      Net Change: {net:,}")
    
    # Save to CSV
    if output_file:
        output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(OUTPUT_DIR) / f"copilot_loc_summary_{enterprise}_{timestamp}.csv"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write CSV with multiple sheets (using separate files for simplicity)
    # Summary sheet
    summary_file = output_path
    with open(summary_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['period', 'loc_added', 'loc_deleted', 'net_change']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # 28-day total
        writer.writerow({
            'period': '28-Day Total',
            'loc_added': total_28day['loc_added'],
            'loc_deleted': total_28day['loc_deleted'],
            'net_change': total_28day['loc_added'] - total_28day['loc_deleted']
        })
        
        # Weekly totals
        for week in ['Week 1', 'Week 2', 'Week 3', 'Week 4']:
            week_data = weekly_data['weekly_totals'][week]
            writer.writerow({
                'period': week,
                'loc_added': week_data['loc_added'],
                'loc_deleted': week_data['loc_deleted'],
                'net_change': week_data['loc_added'] - week_data['loc_deleted']
            })
    
    print(f"\n✅ Summary saved to: {summary_file}")
    
    # Feature breakdown sheet
    feature_file = output_path.parent / f"{output_path.stem}_features.csv"
    with open(feature_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['feature', 'period', 'loc_added', 'loc_deleted', 'net_change']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Get all unique features
        all_features = set(feature_28day.keys())
        for week_data in weekly_data['weekly_feature_totals'].values():
            all_features.update(week_data.keys())
        
        # Write 28-day feature totals
        for feature in sorted(all_features):
            if feature in feature_28day:
                metrics = feature_28day[feature]
                writer.writerow({
                    'feature': feature,
                    'period': '28-Day Total',
                    'loc_added': metrics['loc_added'],
                    'loc_deleted': metrics['loc_deleted'],
                    'net_change': metrics['loc_added'] - metrics['loc_deleted']
                })
            else:
                writer.writerow({
                    'feature': feature,
                    'period': '28-Day Total',
                    'loc_added': 0,
                    'loc_deleted': 0,
                    'net_change': 0
                })
        
        # Write weekly feature totals
        for week in ['Week 1', 'Week 2', 'Week 3', 'Week 4']:
            week_features = weekly_data['weekly_feature_totals'][week]
            for feature in sorted(all_features):
                if feature in week_features:
                    metrics = week_features[feature]
                    writer.writerow({
                        'feature': feature,
                        'period': week,
                        'loc_added': metrics['loc_added'],
                        'loc_deleted': metrics['loc_deleted'],
                        'net_change': metrics['loc_added'] - metrics['loc_deleted']
                    })
                else:
                    writer.writerow({
                        'feature': feature,
                        'period': week,
                        'loc_added': 0,
                        'loc_deleted': 0,
                        'net_change': 0
                    })
    
    print(f"✅ Feature breakdown saved to: {feature_file}")
    
    return report_data


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate GitHub Copilot lines of code summary with 28-day and weekly breakdowns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python copilot_loc_summary.py my-enterprise
  python copilot_loc_summary.py my-enterprise --output summary.csv

Environment variables (can be set in .env file):
  GITHUB_TOKEN: Required GitHub personal access token (must have 'manage_billing:copilot' or 'read:enterprise' scope)
  GITHUB_API_URL: GitHub API base URL (default: {API_URL})
  OUTPUT_DIR: Default output directory (default: {OUTPUT_DIR})
  DEBUG: Enable debug mode (true/false, default: false)
  RATE_LIMIT_THRESHOLD: Rate limit threshold (default: {RATE_LIMIT_THRESHOLD})
  API_DELAY: Delay between API requests in seconds (default: {API_DELAY})

Output:
  Generates two CSV files:
  - Summary file: 28-day totals and weekly totals (all features combined)
  - Features file: Per-feature breakdown for 28-day and weekly periods
        """
    )
    
    parser.add_argument('enterprise', 
                       help='GitHub Enterprise slug/name')
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
    debug_print(f"  Output file: {args.output}")
    debug_print(f"  API URL: {API_URL}")
    debug_print(f"  Output directory: {OUTPUT_DIR}")
    
    try:
        report_data = generate_summary_report(
            enterprise=args.enterprise,
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



