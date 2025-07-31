# PR Merged Report

This script calculates the average number of pull requests (PRs) merged per developer for a given GitHub organization (part of an enterprise). Optionally, it can also provide a detailed report of PRs merged by each individual developer.

## Features
- Calculates the average number of PRs merged per developer in a GitHub organization.
- Optionally outputs a detailed report of PRs merged by each developer.
- Designed for organizations that are part of a GitHub Enterprise.

## Usage

```bash
python pr_merged_report.py --org <github-org-name> [--token <github-token>] [--individual yes|no]
```

- `--org`: Name of the GitHub organization.
- `--token`: (Optional) GitHub personal access token for authentication (recommended for higher rate limits).
- `--individual`: (Optional) Set to `yes` to get individual PR merged report, `no` (default) for only the average.

## Example

```bash
python pr_merged_report.py --org my-enterprise-org --individual yes
```