#!/usr/bin/env python3
"""
GitHub Copilot Usage Metrics Reporter

This script fetches GitHub Copilot usage metrics from the GitHub API and generates
reports with lines of code (LoC) metrics and acceptance rates for different features.
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
from typing import Dict, List, Optional, Any
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


def calculate_acceptance_rate(accepted: int, generated: int) -> float:
    """Calculate acceptance rate as percentage"""
    if generated == 0:
        return 0.0
    return (accepted / generated) * 100


def calculate_loc_acceptance_rate(added: int, suggested: int) -> float:
    """Calculate LoC acceptance rate as percentage"""
    if suggested == 0:
        return 0.0
    return (added / suggested) * 100


def aggregate_metrics_by_feature(records: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate metrics by feature across all records
    
    Args:
        records: List of NDJSON records
    
    Returns:
        Dictionary of aggregated metrics by feature
    """
    feature_metrics = defaultdict(lambda: {
        'loc_suggested_to_add_sum': 0,
        'loc_suggested_to_delete_sum': 0,
        'loc_added_sum': 0,
        'loc_deleted_sum': 0,
        'code_generation_activity_count': 0,
        'code_acceptance_activity_count': 0,
        'user_count': set()
    })
    
    for record in records:
        user_login = record.get('user_login', 'unknown')
        
        # Process totals_by_language_feature
        for item in record.get('totals_by_language_feature', []):
            feature = item.get('feature', 'unknown')
            language = item.get('language', 'unknown')
            
            # Create a combined key for feature-language combination
            key = f"{feature}"
            
            feature_metrics[key]['loc_suggested_to_add_sum'] += item.get('loc_suggested_to_add_sum', 0)
            feature_metrics[key]['loc_suggested_to_delete_sum'] += item.get('loc_suggested_to_delete_sum', 0)
            feature_metrics[key]['loc_added_sum'] += item.get('loc_added_sum', 0)
            feature_metrics[key]['loc_deleted_sum'] += item.get('loc_deleted_sum', 0)
            feature_metrics[key]['code_generation_activity_count'] += item.get('code_generation_activity_count', 0)
            feature_metrics[key]['code_acceptance_activity_count'] += item.get('code_acceptance_activity_count', 0)
            feature_metrics[key]['user_count'].add(user_login)
    
    # Convert sets to counts
    for feature in feature_metrics:
        feature_metrics[feature]['user_count'] = len(feature_metrics[feature]['user_count'])
    
    return dict(feature_metrics)


def aggregate_metrics_by_language_feature(records: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate metrics by language and feature combination
    
    Args:
        records: List of NDJSON records
    
    Returns:
        Dictionary of aggregated metrics by language-feature
    """
    lang_feature_metrics = defaultdict(lambda: {
        'loc_suggested_to_add_sum': 0,
        'loc_suggested_to_delete_sum': 0,
        'loc_added_sum': 0,
        'loc_deleted_sum': 0,
        'code_generation_activity_count': 0,
        'code_acceptance_activity_count': 0,
        'user_count': set()
    })
    
    for record in records:
        user_login = record.get('user_login', 'unknown')
        
        # Process totals_by_language_feature
        for item in record.get('totals_by_language_feature', []):
            feature = item.get('feature', 'unknown')
            language = item.get('language', 'unknown')
            
            # Create a combined key for feature-language combination
            key = f"{language}:{feature}"
            
            lang_feature_metrics[key]['loc_suggested_to_add_sum'] += item.get('loc_suggested_to_add_sum', 0)
            lang_feature_metrics[key]['loc_suggested_to_delete_sum'] += item.get('loc_suggested_to_delete_sum', 0)
            lang_feature_metrics[key]['loc_added_sum'] += item.get('loc_added_sum', 0)
            lang_feature_metrics[key]['loc_deleted_sum'] += item.get('loc_deleted_sum', 0)
            lang_feature_metrics[key]['code_generation_activity_count'] += item.get('code_generation_activity_count', 0)
            lang_feature_metrics[key]['code_acceptance_activity_count'] += item.get('code_acceptance_activity_count', 0)
            lang_feature_metrics[key]['user_count'].add(user_login)
    
    # Convert sets to counts
    for key in lang_feature_metrics:
        lang_feature_metrics[key]['user_count'] = len(lang_feature_metrics[key]['user_count'])
    
    return dict(lang_feature_metrics)


def generate_metrics_report(enterprise: str, specific_day: Optional[str] = None,
                           output_format: str = 'csv', output_file: Optional[str] = None) -> Dict:
    """
    Generate Copilot usage metrics report
    
    Args:
        enterprise: Enterprise slug
        specific_day: Specific day in YYYY-MM-DD format (optional)
        output_format: Output format ('csv' or 'json')
        output_file: Optional output file path
    
    Returns:
        Dictionary with report data
    """
    headers = get_headers()
    
    print(f"\n🔍 Fetching GitHub Copilot usage metrics for enterprise: {enterprise}")
    print("=" * 70)
    
    # Get metrics URLs
    metrics_info = get_copilot_metrics_urls(enterprise, 'users', headers, specific_day)
    
    if not metrics_info:
        print("❌ Failed to fetch metrics information")
        return {}
    
    download_links = metrics_info.get('download_links', [])
    if not download_links:
        print("❌ No download links available")
        return {}
    
    if specific_day:
        report_date = metrics_info.get('report_day', 'unknown')
        print(f"📅 Report date: {report_date}")
    else:
        start_day = metrics_info.get('report_start_day', 'unknown')
        end_day = metrics_info.get('report_end_day', 'unknown')
        print(f"📅 Report period: {start_day} to {end_day}")
    
    # Download and aggregate all reports
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
    
    # Aggregate metrics
    print("\n📊 Aggregating metrics by feature...")
    feature_metrics = aggregate_metrics_by_feature(all_records)
    
    print("\n📊 Aggregating metrics by language and feature...")
    lang_feature_metrics = aggregate_metrics_by_language_feature(all_records)
    
    # Prepare report data
    report_data = {
        'enterprise': enterprise,
        'report_date': metrics_info.get('report_day') if specific_day else None,
        'report_start_day': metrics_info.get('report_start_day'),
        'report_end_day': metrics_info.get('report_end_day'),
        'generated_at': datetime.now().isoformat(),
        'total_users': len(set(r.get('user_login', '') for r in all_records)),
        'feature_metrics': {},
        'language_feature_metrics': {}
    }
    
    # Calculate acceptance rates for features
    for feature, metrics in feature_metrics.items():
        code_acceptance_rate = calculate_acceptance_rate(
            metrics['code_acceptance_activity_count'],
            metrics['code_generation_activity_count']
        )
        
        loc_acceptance_rate = calculate_loc_acceptance_rate(
            metrics['loc_added_sum'],
            metrics['loc_suggested_to_add_sum']
        )
        
        report_data['feature_metrics'][feature] = {
            **metrics,
            'code_acceptance_rate': round(code_acceptance_rate, 2),
            'loc_acceptance_rate': round(loc_acceptance_rate, 2) if metrics['loc_suggested_to_add_sum'] > 0 else None
        }
    
    # Calculate acceptance rates for language-feature combinations
    for key, metrics in lang_feature_metrics.items():
        code_acceptance_rate = calculate_acceptance_rate(
            metrics['code_acceptance_activity_count'],
            metrics['code_generation_activity_count']
        )
        
        loc_acceptance_rate = calculate_loc_acceptance_rate(
            metrics['loc_added_sum'],
            metrics['loc_suggested_to_add_sum']
        )
        
        report_data['language_feature_metrics'][key] = {
            **metrics,
            'code_acceptance_rate': round(code_acceptance_rate, 2),
            'loc_acceptance_rate': round(loc_acceptance_rate, 2) if metrics['loc_suggested_to_add_sum'] > 0 else None
        }
    
    # Print summary
    print("\n" + "=" * 70)
    print("📈 METRICS SUMMARY")
    print("=" * 70)
    print(f"Enterprise: {enterprise}")
    print(f"Total users in report: {report_data['total_users']}")
    print(f"\n📊 Feature Breakdown:")
    
    for feature, metrics in sorted(report_data['feature_metrics'].items()):
        print(f"\n  {feature}:")
        print(f"    Users: {metrics['user_count']}")
        print(f"    LoC Suggested: {metrics['loc_suggested_to_add_sum']:,}")
        print(f"    LoC Added: {metrics['loc_added_sum']:,}")
        print(f"    LoC Deleted: {metrics['loc_deleted_sum']:,}")
        print(f"    Code Generations: {metrics['code_generation_activity_count']:,}")
        print(f"    Code Acceptances: {metrics['code_acceptance_activity_count']:,}")
        print(f"    Code Acceptance Rate: {metrics['code_acceptance_rate']:.2f}%")
        if metrics['loc_acceptance_rate'] is not None:
            print(f"    LoC Acceptance Rate: {metrics['loc_acceptance_rate']:.2f}%")
        else:
            print(f"    LoC Acceptance Rate: N/A (no suggestions for this feature)")
    
    # Save to file
    if output_file or output_format:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == 'csv':
            if not output_file:
                output_file = f"copilot_metrics_{enterprise}_{timestamp}.csv"
            
            output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write feature metrics CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'feature', 'users', 'loc_suggested_to_add', 'loc_added', 'loc_deleted',
                    'code_generations', 'code_acceptances', 'code_acceptance_rate_%',
                    'loc_acceptance_rate_%'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for feature, metrics in sorted(report_data['feature_metrics'].items()):
                    writer.writerow({
                        'feature': feature,
                        'users': metrics['user_count'],
                        'loc_suggested_to_add': metrics['loc_suggested_to_add_sum'],
                        'loc_added': metrics['loc_added_sum'],
                        'loc_deleted': metrics['loc_deleted_sum'],
                        'code_generations': metrics['code_generation_activity_count'],
                        'code_acceptances': metrics['code_acceptance_activity_count'],
                        'code_acceptance_rate_%': metrics['code_acceptance_rate'],
                        'loc_acceptance_rate_%': metrics['loc_acceptance_rate'] if metrics['loc_acceptance_rate'] is not None else 'N/A'
                    })
            
            print(f"\n✅ Feature metrics saved to: {output_path}")
            
            # Write language-feature metrics CSV
            lang_output_file = output_file.replace('.csv', '_by_language.csv')
            lang_output_path = Path(OUTPUT_DIR) / lang_output_file if not Path(lang_output_file).is_absolute() else Path(lang_output_file)
            
            with open(lang_output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'language', 'feature', 'users', 'loc_suggested_to_add', 'loc_added', 'loc_deleted',
                    'code_generations', 'code_acceptances', 'code_acceptance_rate_%',
                    'loc_acceptance_rate_%'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for key, metrics in sorted(report_data['language_feature_metrics'].items()):
                    language, feature = key.split(':', 1)
                    writer.writerow({
                        'language': language,
                        'feature': feature,
                        'users': metrics['user_count'],
                        'loc_suggested_to_add': metrics['loc_suggested_to_add_sum'],
                        'loc_added': metrics['loc_added_sum'],
                        'loc_deleted': metrics['loc_deleted_sum'],
                        'code_generations': metrics['code_generation_activity_count'],
                        'code_acceptances': metrics['code_acceptance_activity_count'],
                        'code_acceptance_rate_%': metrics['code_acceptance_rate'],
                        'loc_acceptance_rate_%': metrics['loc_acceptance_rate'] if metrics['loc_acceptance_rate'] is not None else 'N/A'
                    })
            
            print(f"✅ Language-feature metrics saved to: {lang_output_path}")
            
        else:  # JSON
            if not output_file:
                output_file = f"copilot_metrics_{enterprise}_{timestamp}.json"
            
            output_path = Path(OUTPUT_DIR) / output_file if not Path(output_file).is_absolute() else Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            json_data = report_data.copy()
            for feature in json_data['feature_metrics']:
                if 'user_count' in json_data['feature_metrics'][feature] and isinstance(json_data['feature_metrics'][feature]['user_count'], set):
                    json_data['feature_metrics'][feature]['user_count'] = len(json_data['feature_metrics'][feature]['user_count'])
            
            for key in json_data['language_feature_metrics']:
                if 'user_count' in json_data['language_feature_metrics'][key] and isinstance(json_data['language_feature_metrics'][key]['user_count'], set):
                    json_data['language_feature_metrics'][key]['user_count'] = len(json_data['language_feature_metrics'][key]['user_count'])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Report saved to: {output_path}")
    
    return report_data


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate GitHub Copilot usage metrics report with LoC and acceptance rates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python copilot_usage_metrics.py my-enterprise
  python copilot_usage_metrics.py my-enterprise --format json
  python copilot_usage_metrics.py my-enterprise --day 2025-12-01
  python copilot_usage_metrics.py my-enterprise --output metrics.csv

Environment variables (can be set in .env file):
  GITHUB_TOKEN: Required GitHub personal access token (must have 'manage_billing:copilot' or 'read:enterprise' scope)
  GITHUB_API_URL: GitHub API base URL (default: {API_URL})
  OUTPUT_DIR: Default output directory (default: {OUTPUT_DIR})
  DEBUG: Enable debug mode (true/false, default: false)
  RATE_LIMIT_THRESHOLD: Rate limit threshold (default: {RATE_LIMIT_THRESHOLD})
  API_DELAY: Delay between API requests in seconds (default: {API_DELAY})

Output Formats:
  csv  - CSV format with feature metrics and language-feature breakdown (default)
  json - JSON format with complete data structure

Metrics Calculated:
  - Code Acceptance Rate: (code_acceptance_activity_count / code_generation_activity_count) * 100
  - LoC Acceptance Rate: (loc_added_sum / loc_suggested_to_add_sum) * 100
  - Raw LoC data for all features including agent_edit mode
        """
    )
    
    parser.add_argument('enterprise', 
                       help='GitHub Enterprise slug/name')
    parser.add_argument('--format', '-f',
                       choices=['csv', 'json'],
                       default='csv',
                       help='Output format (default: csv)')
    parser.add_argument('--day', '-d',
                       help='Specific day to fetch metrics for (YYYY-MM-DD format). If not specified, fetches latest 28-day report')
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
    debug_print(f"  Format: {args.format}")
    debug_print(f"  Day: {args.day}")
    debug_print(f"  Output file: {args.output}")
    debug_print(f"  API URL: {API_URL}")
    debug_print(f"  Output directory: {OUTPUT_DIR}")
    
    try:
        report_data = generate_metrics_report(
            enterprise=args.enterprise,
            specific_day=args.day,
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
