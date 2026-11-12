# Organization GHAS report

Reads GitHub organization logins from CSV and creates an Excel report matching the
first 16 columns of the supplied GHAS workbook, from **Org Name** through
**Total Closed Alerts**. Owner logins and every column after them are excluded.
The source workbook is not needed at runtime.

## Setup and usage

Python 3.9+:

```powershell
python -m pip install -r .\org-ghas-report\requirements.txt
$env:GITHUB_TOKEN = "<your-token>"
python .\org-ghas-report\org_ghas_report.py .\organizations.csv --output .\results\ghas_report.xlsx
```

`GH_TOKEN` is also supported. Tokens are read only from the environment, never
from command-line arguments. All GitHub requests are read-only.

Input example:

```csv
organization
my-org
another-org
```

A single column without a header also works. Common headers (`org`,
`organization`, `organization_name`, `org_name`, `Org Name`) are detected
case-insensitively. For another header or a multi-column file:

```powershell
python .\org-ghas-report\org_ghas_report.py .\organizations.csv --org-column "GitHub Organization"
```

Blank lines are skipped, surrounding whitespace is trimmed, UTF-8 BOMs are
accepted, and duplicate organization names are removed case-insensitively.
Invalid names and empty input fail before any GitHub requests.

For GitHub Enterprise Server, supply
`--api-url https://github.example.com/api/v3` or set `GITHUB_API_URL`.
Endpoint/feature availability depends on the server version.

## Permissions

Use an organization owner or security manager account with access to **all**
repositories to avoid an incomplete inventory. For classic PATs, the APIs
typically require `repo`, `read:org`, and `security_events` scopes; authorize
the token for SAML SSO where required.

Fine-grained tokens need repository Metadata, Administration (read, for checking
Dependabot enablement), Code scanning alerts (read), Secret scanning alerts
(read), and Dependabot alerts (read), covering every requested repository and
organization. A fine-grained PAT is scoped to one resource owner; for multiple
organizations a suitably authorized classic token may be necessary.
The script cannot detect repositories GitHub silently hides from a limited token.

## Metric definitions

All metrics cover **private repositories only** (including archived repositories
and forks). Public and internal repositories are excluded. This scope is applied
to both coverage and alert counts.

| Columns | Definition |
|---|---|
| Private Repo Count | Private repositories returned to the token |
| Code Scanning Coverage / Enabled Repo Count | Repositories with at least one uploaded analysis from any tool |
| Secret Scanning Coverage / Enabled Repo Count | Repositories with secret scanning explicitly enabled in their security settings |
| Dependabot Coverage | Repositories with Dependabot **alerts** enabled, not version updates or security-update PRs |
| Autofix Enabled Repo Count | `N/A`: the APIs used do not expose a reliable repository-level Autofix enablement field; CodeQL activity is not a substitute |
| Code Scanning Open / Closed | Default-branch alerts from all tools; closed includes fixed and dismissed |
| Secret Scanning Open / Closed | Open / resolved alerts |
| Dependabot Open / Closed | Open / fixed, dismissed, and auto-dismissed alerts |
| Total Open / Closed Alerts | Excel formulas `=I+K+M` / `=J+L+N` (as in the reference); `N/A` if any contributing count is unavailable |

The main **GHAS Format** sheet mirrors the reference layout: row 1 holds the
merged group headers (Code Scanning (all tools), Secret Scanning, Dependabot,
All Alert Types), row 2 the column headers, and data starts at row 3 with panes
frozen at `B3`.

Coverage is enabled/active repository count divided by Private Repo Count, shown
as an Excel percentage (0% for organizations with no private repositories).
Code scanning analyses are historical: a past analysis does not prove that the
scanner is still configured or recently active. These are explicit definitions
for this script, not a claim to reproduce undocumented calculations in the
reference workbook.

The report includes a **Notes** sheet with definitions. Missing permissions,
ambiguous 404s, unavailable endpoints, and other collection failures produce
`N/A`, warnings on stderr, and an **Errors** sheet, not misleading zeros.
If any repository's enablement is unknown, the corresponding organization's
coverage/count is `N/A` rather than a partial count. A 404 from the Dependabot
enablement endpoint means disabled only when repository admin permission is
confirmed; for non-admins (such as security managers) the script falls back to
the repository Dependabot alerts endpoint, whose explicit "disabled" / "archived"
403 messages count as disabled. Missing secret-scanning settings are treated as unknown.
Autofix is always explicitly unavailable and does not by itself cause a failure.

One organization failing (not found, SAML not authorized, no access, or an
unexpected error) never stops the run: its row is `N/A`, the cause is listed on
the Errors sheet, the remaining organizations are reported, and the script exits 1.

Pagination is followed for repositories and alerts. Rate-limit response headers
are honored, and transient server errors are retried up to three times.
Large organizations with many alerts may take time; requests are sequential.
Only counts and collection errors are written, not alert contents or secrets.

Exit status is `0` for successful collection and `1` for invalid input, file
errors, or a partial report. Partial reports are still saved so successful
organizations and metrics remain available.

## Tests

```powershell
python -m unittest discover -s .\org-ghas-report -p "test_*.py" -v
```
