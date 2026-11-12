#!/usr/bin/env python3
"""Generate a private-repository GHAS overview for organizations in a CSV."""

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


HEADERS = [
    "Org Name",
    "Private Repo Count",
    "Code Scanning Coverage",
    "Secret Scanning Coverage",
    "Dependabot Coverage",
    "Secret Scanning Enabled Repo Count",
    "Code Scanning Enabled Repo Count",
    "Autofix Enabled Repo Count",
    "Code Scanning Open",
    "Code Scanning Closed",
    "Secret Scanning Open",
    "Secret Scanning Closed",
    "Dependabot Open",
    "Dependabot Closed",
    "Total Open Alerts",
    "Total Closed Alerts",
]
GROUPS = [
    ("I", "J", "Code Scanning (all tools)", "C6E0B4"),
    ("K", "L", "Secret Scanning", "FFE699"),
    ("M", "N", "Dependabot", "BDD7EE"),
    ("O", "P", "All Alert Types", "D9D9D9"),
]
ORG_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
HEADER_NAMES = {"org", "organization", "organization_name", "org_name", "org name"}


def read_organizations(path: Path, column: Optional[str] = None) -> List[str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.reader(stream) if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("The input CSV is empty.")
    header = [cell.strip() for cell in rows[0]]
    if column:
        if column not in header:
            raise ValueError(f"CSV column not found: {column}")
        index = header.index(column)
        rows = rows[1:]
    else:
        matches = [i for i, cell in enumerate(header) if cell.lower() in HEADER_NAMES]
        index = matches[0] if matches else 0
        if matches:
            rows = rows[1:]
        elif len(header) != 1:
            raise ValueError("Use --org-column to select the organization column.")
    organizations = []
    seen = set()
    for row in rows:
        org = row[index].strip() if index < len(row) else ""
        if not ORG_PATTERN.fullmatch(org):
            raise ValueError(f"Invalid or missing GitHub organization name: {org!r}")
        if org.lower() not in seen:
            organizations.append(org)
            seen.add(org.lower())
    if not organizations:
        raise ValueError("The CSV contains no organizations.")
    return organizations


class GitHub:
    def __init__(self, token: str, api_url: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = f"{self.api_url}/{path.lstrip('/')}"
        for attempt in range(4):
            response = self.session.get(url, params=params, timeout=60)
            if attempt < 3:
                wait = None
                if response.status_code in (403, 429):
                    if "Retry-After" in response.headers:
                        wait = float(response.headers["Retry-After"])
                    elif response.headers.get("X-RateLimit-Remaining") == "0":
                        wait = max(
                            float(response.headers["X-RateLimit-Reset"]) - time.time() + 1,
                            1,
                        )
                elif response.status_code in (500, 502, 503, 504):
                    wait = 2 ** attempt
                if wait is not None:
                    print(f"Retrying {path} in {wait:.0f}s (HTTP {response.status_code}).",
                          file=sys.stderr)
                    time.sleep(wait)
                    continue
            response.raise_for_status()
            return response
        raise RuntimeError(f"Request retries exhausted: {path}")

    def items(self, path: str, **params: Any) -> Iterator[Dict[str, Any]]:
        params = {"per_page": 100, **params}
        while True:
            response = self.get(path, params)
            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Expected a list from {path}.")
            yield from data
            next_url = response.links.get("next", {}).get("url")
            if not next_url:
                break
            # Keep pagination requests on the configured API origin and base path.
            prefix = self.api_url + "/"
            if not next_url.startswith(prefix):
                raise ValueError(f"Unexpected pagination URL from {path}.")
            path = next_url[len(prefix):]
            params = {}


def error_message(error: requests.HTTPError) -> str:
    try:
        body = error.response.json() if error.response is not None else {}
    except ValueError:
        return ""
    return str(body.get("message", "")).lower() if isinstance(body, dict) else ""


def dependabot_enabled(api: "GitHub", path: str, repo: Dict[str, Any]) -> bool:
    try:
        api.get(f"{path}/vulnerability-alerts")
        return True
    except requests.HTTPError as error:
        if error.response is None or error.response.status_code != 404:
            raise
        if (repo.get("permissions") or {}).get("admin") is True:
            return False
    # Non-admins (e.g. security managers) get 404 above; the alerts endpoint states it explicitly.
    try:
        api.get(f"{path}/dependabot/alerts", {"per_page": 1})
        return True
    except requests.HTTPError as error:
        response = error.response
        if (response is not None and response.status_code == 403
                and any(text in error_message(error) for text in (
                    "dependabot alerts are disabled",
                    "dependabot alerts are not available for archived",
                ))):
            return False
        raise


def collect_org(
    api: GitHub, org: str, errors: List[Tuple[str, str, str]]
) -> Dict[str, Any]:
    row: Dict[str, Any] = dict.fromkeys(HEADERS, "N/A")
    row["Org Name"] = org

    def record(metric: str, error: Exception) -> None:
        errors.append((org, metric, str(error)))
        print(f"WARNING: {org}: {metric}: {error}", file=sys.stderr)

    try:
        repos = [
            repo for repo in api.items(f"orgs/{org}/repos", type="private")
            if repo["private"] and repo.get("visibility") != "internal"
        ]
    except (requests.RequestException, ValueError, KeyError) as error:
        record("Repositories", error)
        return row

    row["Private Repo Count"] = len(repos)
    private_names = {repo["full_name"].lower() for repo in repos}
    enabled: Dict[str, Optional[int]] = {"Code Scanning": 0, "Secret Scanning": 0,
                                        "Dependabot": 0}
    for repo in repos:
        name = repo["full_name"]
        path = f"repos/{name}"
        try:
            status = ((repo.get("security_and_analysis") or {})
                      .get("secret_scanning") or {}).get("status")
            if status not in ("enabled", "disabled"):
                raise ValueError(f"{name}: secret scanning settings are not visible.")
            if status == "enabled" and enabled["Secret Scanning"] is not None:
                enabled["Secret Scanning"] += 1
        except ValueError as error:
            enabled["Secret Scanning"] = None
            record("Secret Scanning Coverage", error)

        try:
            response = api.get(f"{path}/code-scanning/analyses", {"per_page": 1})
            analyses = response.json()
            if not isinstance(analyses, list):
                raise ValueError(f"{name}: expected a code scanning analyses list.")
            if analyses and enabled["Code Scanning"] is not None:
                enabled["Code Scanning"] += 1
        except requests.HTTPError as error:
            response = error.response
            # A bare 404/403 can also mean insufficient access, so trust only explicit messages.
            message = error_message(error)
            disabled = response is not None and response.status_code in (403, 404) and any(
                text in message for text in (
                    "code scanning is not enabled", "no analysis found",
                    "advanced security must be enabled", "code security must be enabled",
                )
            )
            if not disabled:
                enabled["Code Scanning"] = None
                record("Code Scanning Coverage", error)
        except (requests.RequestException, ValueError) as error:
            enabled["Code Scanning"] = None
            record("Code Scanning Coverage", error)

        try:
            if dependabot_enabled(api, path, repo) and enabled["Dependabot"] is not None:
                enabled["Dependabot"] += 1
        except requests.RequestException as error:
            enabled["Dependabot"] = None
            record("Dependabot Coverage", error)

    for feature, count in enabled.items():
        row[f"{feature} Coverage"] = (
            count / len(repos) if repos and count is not None
            else 0.0 if not repos else "N/A"
        )
        count_header = f"{feature} Enabled Repo Count"
        if count_header in row:
            row[count_header] = count if count is not None else "N/A"

    for feature, endpoint, closed_states in (
        ("Code Scanning", "code-scanning", {"fixed", "dismissed", "closed"}),
        ("Secret Scanning", "secret-scanning", {"resolved"}),
        ("Dependabot", "dependabot", {"fixed", "dismissed", "auto_dismissed"}),
    ):
        try:
            opened = closed = 0
            if repos:
                # Explicit states avoid relying on endpoint-specific defaults.
                closed_filter = (
                    "closed" if feature == "Code Scanning"
                    else ",".join(sorted(closed_states))
                )
                for state_filter in ("open", closed_filter):
                    for alert in api.items(f"orgs/{org}/{endpoint}/alerts", state=state_filter):
                        if alert["repository"]["full_name"].lower() not in private_names:
                            continue
                        if alert["state"] == "open":
                            opened += 1
                        elif alert["state"] in closed_states:
                            closed += 1
                        else:
                            raise ValueError(f"Unexpected {feature} alert state: {alert['state']}")
            row[f"{feature} Open"] = opened
            row[f"{feature} Closed"] = closed
        except (requests.RequestException, ValueError, KeyError) as error:
            record(f"{feature} Alerts", error)
    for state in ("Open", "Closed"):
        counts = [row[f"{feature} {state}"] for feature in enabled]
        if all(isinstance(count, int) for count in counts):
            row[f"Total {state} Alerts"] = sum(counts)
    return row


def write_report(
    path: Path, rows: List[Dict[str, Any]], errors: List[Tuple[str, str, str]]
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "GHAS Format"
    # Row 1: grouped alert headers, row 2: column headers, data from row 3 (reference layout).
    for start, end, label, color in GROUPS:
        sheet[f"{start}1"] = label
        sheet[f"{start}1"].font = Font(bold=True)
        sheet[f"{start}1"].fill = PatternFill("solid", fgColor=color)
        sheet[f"{start}1"].alignment = Alignment(horizontal="center")
        sheet.merge_cells(f"{start}1:{end}1")
    sheet.append(HEADERS)
    for cell in sheet[2]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for number, row in enumerate(rows, 3):
        values = [row[header] for header in HEADERS]
        for state, column, parts in (("Open", 15, "IKM"), ("Closed", 16, "JLN")):
            if isinstance(row[f"Total {state} Alerts"], int):
                values[column - 1] = "=" + "+".join(f"{c}{number}" for c in parts)
        sheet.append(values)
    sheet.freeze_panes = "B3"
    sheet.auto_filter.ref = f"A2:P{max(sheet.max_row, 2)}"
    for column in ("C", "D", "E"):
        for cell in sheet[column][2:]:
            cell.number_format = "0.0%"
    sheet.column_dimensions["A"].width = 40
    for column in "BCDEFGHIJKLMNOP":
        sheet.column_dimensions[column].width = 15
    notes = workbook.create_sheet("Notes")
    notes.append(["Metric", "Definition"])
    for note in (
        ("Scope", "Private repositories visible to the token; excludes public and internal repositories."),
        ("Coverage", "Enabled/active private repositories divided by private repo count; 0% for no repos."),
        ("Code Scanning", "At least one uploaded analysis, any tool; historical, not a recent-activity guarantee."),
        ("Secret Scanning", "Repository security_and_analysis.secret_scanning.status is enabled."),
        ("Dependabot", "Repository vulnerability-alerts endpoint reports alerts enabled."),
        ("Closed Alerts", "Fixed/dismissed code alerts; resolved secrets; fixed/dismissed/auto-dismissed Dependabot alerts."),
        ("Autofix Enabled Repo Count", "N/A: no reliable repository-level enablement field in the APIs used. Not inferred from CodeQL."),
        ("N/A", "Unavailable data, not zero. See Errors sheet and stderr for collection failures."),
    ):
        notes.append(note)
    notes.column_dimensions["A"].width = 30
    notes.column_dimensions["B"].width = 120
    if errors:
        error_sheet = workbook.create_sheet("Errors")
        error_sheet.append(["Org Name", "Metric", "Error"])
        for error in errors:
            error_sheet.append(error)
        for column, width in (("A", 40), ("B", 35), ("C", 120)):
            error_sheet.column_dimensions[column].width = width
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="CSV of organization logins")
    parser.add_argument("--org-column", help="Exact header for a custom CSV column")
    parser.add_argument("-o", "--output", type=Path,
                        default=Path(f"org_ghas_report_{datetime.now():%Y%m%d_%H%M%S}.xlsx"))
    parser.add_argument("--api-url", default=os.getenv("GITHUB_API_URL", "https://api.github.com"))
    args = parser.parse_args()
    if args.output.suffix.lower() != ".xlsx":
        parser.error("--output must have an .xlsx extension.")
    if not args.api_url.startswith("https://"):
        parser.error("--api-url must use HTTPS.")
    if args.input_csv.resolve() == args.output.resolve():
        parser.error("Input and output paths must differ.")
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        parser.error("Set GITHUB_TOKEN or GH_TOKEN with access to the requested organizations.")
    try:
        organizations = read_organizations(args.input_csv, args.org_column)
        api = GitHub(token, args.api_url)
        rows = []
        errors: List[Tuple[str, str, str]] = []
        print("Autofix enablement is unavailable from the APIs used; that column will be N/A.",
              file=sys.stderr)
        try:
            for index, org in enumerate(organizations, 1):
                print(f"[{index}/{len(organizations)}] Processing {org}")
                try:
                    rows.append(collect_org(api, org, errors))
                except Exception as error:  # one org must never abort the rest
                    errors.append((org, "Unexpected", repr(error)))
                    print(f"WARNING: {org}: unexpected failure: {error!r}", file=sys.stderr)
                    row = dict.fromkeys(HEADERS, "N/A")
                    row["Org Name"] = org
                    rows.append(row)
            write_report(args.output, rows, errors)
        finally:
            api.session.close()
    except (OSError, ValueError, csv.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Report saved to {args.output.resolve()}")
    if errors:
        print(f"Partial report: {len(errors)} collection error(s); see Errors sheet.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
