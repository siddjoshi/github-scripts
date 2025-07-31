import argparse
import requests
import sys
from collections import defaultdict

GITHUB_API_URL = "https://api.github.com"


def get_merged_prs(org, token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    # Get all repos in the org
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API_URL}/orgs/{org}/repos?per_page=100&page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to fetch repos: {resp.status_code} {resp.text}")
            sys.exit(1)
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    
    # For each repo, get merged PRs
    pr_counts = defaultdict(int)
    total_prs = 0
    for repo in repos:
        repo_name = repo["name"]
        page = 1
        while True:
            pr_url = f"{GITHUB_API_URL}/repos/{org}/{repo_name}/pulls?state=closed&per_page=100&page={page}"
            pr_resp = requests.get(pr_url, headers=headers)
            if pr_resp.status_code != 200:
                print(f"Failed to fetch PRs for {repo_name}: {pr_resp.status_code} {pr_resp.text}")
                break
            prs = pr_resp.json()
            if not prs:
                break
            for pr in prs:
                if pr.get("merged_at"):
                    user = pr["user"]["login"]
                    pr_counts[user] += 1
                    total_prs += 1
            page += 1
    return pr_counts, total_prs


def main():
    parser = argparse.ArgumentParser(description="Calculate average PRs merged per developer in a GitHub org.")
    parser.add_argument("--org", required=True, help="GitHub organization name")
    parser.add_argument("--token", help="GitHub personal access token")
    parser.add_argument("--individual", choices=["yes", "no"], default="no", help="Show individual PR merged report (yes/no)")
    args = parser.parse_args()

    pr_counts, total_prs = get_merged_prs(args.org, args.token)
    num_devs = len(pr_counts)
    avg_prs = total_prs / num_devs if num_devs else 0

    print(f"\nGitHub Organization: {args.org}")
    print(f"Total merged PRs: {total_prs}")
    print(f"Number of developers with merged PRs: {num_devs}")
    print(f"Average merged PRs per developer: {avg_prs:.2f}\n")

    if args.individual == "yes":
        print("Merged PRs per developer:")
        for user, count in sorted(pr_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {user}: {count}")

if __name__ == "__main__":
    main()