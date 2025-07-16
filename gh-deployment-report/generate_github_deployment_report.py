#!/usr/bin/env python3
"""
GitHub Enterprise Cloud Workflow & Deployment Protection Report Generator

- Lists workflow runs and associated deployments with protection rules
- Aggregates required info into a CSV report

Inputs:
- GITHUB_TOKEN (env var)
- ENTERPRISE_ORG_NAME (arg or env)
- START_DATE, END_DATE (arg or env)

"""
import os
import sys
import requests
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import time

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_URL = 'https://api.github.com'

# --- INPUTS ---
# TODO: Parse org name, start/end date from args or env
ENTERPRISE_ORG_NAME = os.getenv('ENTERPRISE_ORG_NAME') or '<ENTERPRISE_ORG_NAME>'
DAYS = int(os.getenv('DAYS', '7'))
START_DATE = os.getenv('START_DATE')
END_DATE = os.getenv('END_DATE')

# If START_DATE and END_DATE are not set, use DAYS to compute them
if not START_DATE or not END_DATE:
    now = datetime.utcnow()
    start_dt = now - timedelta(days=DAYS)
    START_DATE = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    END_DATE = now.strftime('%Y-%m-%dT%H:%M:%SZ')

# Check required variables
if not all([GITHUB_TOKEN, ENTERPRISE_ORG_NAME]):
    print("Error: Missing one or more required environment variables: GITHUB_TOKEN, ENTERPRISE_ORG_NAME.\nPlease set them in your .env file.")
    sys.exit(1)

# --- UTILS ---
def github_api_get(url, params=None, max_retries=3):
    """Helper for authenticated GET requests to GitHub API with basic error and rate limit handling."""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
    }
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and response.headers['X-RateLimit-Remaining'] == '0':
            reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
            sleep_for = max(reset_time - int(time.time()), 1)
            print(f"Rate limit exceeded. Sleeping for {sleep_for} seconds...")
            time.sleep(sleep_for)
            continue
        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API error: {e}. Retrying...")
            time.sleep(2)
    print(f"Failed to fetch {url} after {max_retries} attempts.")
    return {}

# --- MAIN LOGIC ---
def list_org_repos(org: str) -> List[Dict[str, Any]]:
    """List all repositories in the organization, handling pagination."""
    repos = []
    url = f"{GITHUB_API_URL}/orgs/{org}/repos"
    params = {'per_page': 100, 'type': 'all'}
    while url:
        resp = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json',
        }, params=params)
        resp.raise_for_status()
        repos.extend(resp.json())
        # Check for next page
        if 'next' in resp.links:
            url = resp.links['next']['url']
            params = None  # Params only for first request
        else:
            url = None
    return repos

def list_workflow_runs(repo_full_name: str, start: str, end: str) -> List[Dict[str, Any]]:
    """List workflow runs for a repo in the date range, handling pagination and filtering by created_at."""
    runs = []
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/actions/runs"
    params = {'per_page': 100}
    while url:
        resp = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json',
        }, params=params)
        resp.raise_for_status()
        page_runs = resp.json().get('workflow_runs', [])
        # Filter by created_at
        for run in page_runs:
            created_at = run.get('created_at')
            if created_at and start <= created_at <= end:
                runs.append(run)
        # Check for next page
        if 'next' in resp.links:
            url = resp.links['next']['url']
            params = None
        else:
            url = None
    return runs

def list_deployments(repo_full_name: str) -> List[Dict[str, Any]]:
    """List all deployments for a repo, handling pagination."""
    deployments = []
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/deployments"
    params = {'per_page': 100}
    while url:
        resp = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json',
        }, params=params)
        resp.raise_for_status()
        deployments.extend(resp.json())
        if 'next' in resp.links:
            url = resp.links['next']['url']
            params = None
        else:
            url = None
    return deployments

def get_environment(repo_full_name: str, environment_name: str) -> Dict[str, Any]:
    """Get environment details for a given environment name."""
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/environments/{environment_name}"
    resp = requests.get(url, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
    })
    resp.raise_for_status()
    return resp.json()

def list_deployment_statuses(repo_full_name: str, deployment_id: int) -> List[Dict[str, Any]]:
    """List all statuses for a deployment (paginated)."""
    statuses = []
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/deployments/{deployment_id}/statuses"
    params = {'per_page': 100}
    while url:
        resp = requests.get(url, headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github+json',
        }, params=params)
        resp.raise_for_status()
        statuses.extend(resp.json())
        if 'next' in resp.links:
            url = resp.links['next']['url']
            params = None
        else:
            url = None
    return statuses

def environment_has_protection_rules(env: Dict[str, Any]) -> bool:
    """Return True if the environment has any protection rules enabled (required reviewers, wait timer, etc)."""
    protection_rules = env.get('protection_rules', [])
    # If there are any protection rules, return True
    return bool(protection_rules)

# Stub for matching deployments to workflow runs
# (to be implemented in aggregation step)
def match_deployments_to_workflow_run(workflow_run, deployments):
    """Return deployments that likely belong to this workflow run (by time/actor heuristics)."""
    matched = []
    run_actor = workflow_run.get('actor', {}).get('login')
    run_created_at = workflow_run.get('created_at')
    if not run_created_at:
        return []
    run_time = datetime.strptime(run_created_at, '%Y-%m-%dT%H:%M:%SZ')
    for dep in deployments:
        dep_creator = dep.get('creator', {}).get('login')
        dep_created_at = dep.get('created_at')
        if not dep_created_at:
            continue
        dep_time = datetime.strptime(dep_created_at, '%Y-%m-%dT%H:%M:%SZ')
        # Match if creator matches and deployment created within 5 minutes after workflow run
        if dep_creator == run_actor and abs((dep_time - run_time).total_seconds()) < 300:
            matched.append(dep)
    return matched

def extract_approval_info(statuses):
    """Return list of (approver, approval_time) for 'approved' statuses and the final deployment status."""
    approvals = []
    final_status = None
    # Find all approval statuses
    for status in statuses:
        state = status.get('state')
        creator = status.get('creator', {}).get('login')
        created_at = status.get('created_at')
        if state == 'approved':
            approvals.append((creator, created_at))
    # Find the last non-waiting status if possible
    for status in reversed(statuses):
        state = status.get('state')
        if state in ['success', 'failure', 'inactive', 'error']:
            final_status = state
            break
    if not final_status and statuses:
        final_status = statuses[-1].get('state')
    return approvals, final_status

def get_workflow_run_reviews(repo_full_name: str, run_id: int) -> list:
    """Get the review history for a workflow run (environment approvals)."""
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/actions/runs/{run_id}/approvals"
    resp = requests.get(url, headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
    })
    if resp.status_code == 404:
        # No reviews for this run
        return []
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get('environment_reviews', [])
    else:
        return []

# TODO: Add more functions for deployments, environments, statuses, etc.

REPOSITORY = os.getenv('REPOSITORY')  # Optional: <org>/<repo> or just <repo>

def main():
    # 1. List repos (all or specific)
    if REPOSITORY:
        repo_full_name = REPOSITORY if '/' in REPOSITORY else f"{ENTERPRISE_ORG_NAME}/{REPOSITORY}"
        repos = [{ 'full_name': repo_full_name }]
    else:
        repos = list_org_repos(ENTERPRISE_ORG_NAME)
    report_rows = []
    for repo in tqdm(repos, desc='Repositories'):
        repo_full_name = repo['full_name']
        workflow_runs = list_workflow_runs(repo_full_name, START_DATE, END_DATE)
        deployments = list_deployments(repo_full_name)
        for run in tqdm(workflow_runs, desc=f'Workflow runs for {repo_full_name}', leave=False):
            run_id = run.get('id')
            workflow_name = run.get('name') or run.get('workflow_name')
            triggered_by = run.get('actor', {}).get('login')
            triggered_at = run.get('created_at')
            run_status = run.get('conclusion') or run.get('status')
            # Get review history for this workflow run
            reviews = get_workflow_run_reviews(repo_full_name, run_id)
            approved_by = ''
            approval_time = ''
            approval_comment = ''
            if reviews:
                approved_reviewers = [r['user']['login'] for r in reviews if r.get('state') == 'approved' and r.get('user')]
                # approval_times = [r.get('created_at') for r in reviews if r.get('state') == 'approved' and r.get('created_at')]
                approval_comments = [r.get('comment', '') for r in reviews if r.get('state') == 'approved' and r.get('comment')]
                if not approved_reviewers:
                    print(f"DEBUG: No approver found for run {run_id}. Review objects: {reviews}")
                approved_by = ', '.join(approved_reviewers)
                # approval_time = ', '.join(approval_times)
                approval_comment = ' | '.join(approval_comments)
            else:
                approval_comment = ''
            # Match deployments to this workflow run
            matched_deployments = match_deployments_to_workflow_run(run, deployments)
            if not matched_deployments:
                report_rows.append({
                    'Workflow Run ID': run_id,
                    'Workflow Name': workflow_name,
                    'Triggered By': triggered_by,
                    'Triggered At': triggered_at,
                    'Deployment Approved By': approved_by,
                    # 'Deployment Approval Time': approval_time,
                    'Approval Comment': approval_comment,
                    'Final Status': run_status,
                    'Deployment Status': '',
                })
            for dep in matched_deployments:
                dep_id = dep.get('id')
                environment = dep.get('environment')
                dep_status = ''
                if environment:
                    try:
                        env_details = get_environment(repo_full_name, environment)
                        if environment_has_protection_rules(env_details):
                            statuses = list_deployment_statuses(repo_full_name, dep_id)
                            _, dep_status = extract_approval_info(statuses)
                    except Exception as e:
                        print(f"Error fetching environment/status info for deployment {dep_id}: {e}")
                report_rows.append({
                    'Workflow Run ID': run_id,
                    'Workflow Name': workflow_name,
                    'Triggered By': triggered_by,
                    'Triggered At': triggered_at,
                    'Deployment Approved By': approved_by,
                    # 'Deployment Approval Time': approval_time,
                    'Approval Comment': approval_comment,
                    'Final Status': run_status,
                    'Deployment Status': dep_status,
                })
    # Output to CSV
    if report_rows:
        fieldnames = list(report_rows[0].keys())
        with open('deployment_report.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"Report written to deployment_report.csv ({len(report_rows)} rows)")
    else:
        print("No data found for the specified period.")

if __name__ == '__main__':
    main() 
