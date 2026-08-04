# Copilot Seat Management via Enterprise Teams

Automates creating enterprise teams that span **all** organizations in a GitHub
Enterprise, plus a custom role that lets team members **assign or remove GitHub
Copilot seats** across every org.

Because a single enterprise team can be assigned to a maximum of **1,000
organizations**, the scripts automatically split your orgs into the minimum number
of balanced teams (e.g. 1,995 orgs → two teams of 998 / 997).

## What the scripts do

1. Create an **enterprise custom role** with the Copilot seat-management permission.
2. List every organization in the enterprise, sort alphabetically (A→Z), and split
   into balanced chunks of ≤ 1,000 orgs.
3. Create one **enterprise team** per chunk, attached to those orgs.
4. **Assign the custom role** to each team, so the permission applies in every org
   the team belongs to.

Any member added to these teams can then manage Copilot seats across all orgs.

## Files

| File | Description |
|------|-------------|
| `Setup-CopilotSeatMgmtTeams.ps1` | PowerShell 7+ implementation |
| `setup-copilot-seat-mgmt-teams.sh` | Bash implementation using the `gh` CLI |

## Prerequisites

- **GitHub Enterprise Cloud**.
- A token with **enterprise admin** scope, exposed as an environment variable
  (`GITHUB_TOKEN`, or `GH_TOKEN`/`GITHUB_TOKEN` for the `gh` CLI). **Never hardcode
  secrets.**
- The *"Managing roles and governance via enterprise teams"* feature enabled
  (currently public preview).
- Copilot enabled per organization by an enterprise owner.
- PowerShell 7+ **or** the `gh` CLI + `jq`.

## Usage

### PowerShell

```powershell
$env:GITHUB_TOKEN = 'ghp_xxx'   # enterprise admin scope
pwsh ./Setup-CopilotSeatMgmtTeams.ps1 -Enterprise 'my-enterprise'
```

### Bash / gh CLI

```bash
gh auth login                 # or export GH_TOKEN=...
./setup-copilot-seat-mgmt-teams.sh my-enterprise
```

### Optional parameters / env vars

| PowerShell param | Bash env var | Default | Meaning |
|------------------|--------------|---------|---------|
| `-RoleName` | `ROLE_NAME` | `copilot-seat-manager` | Custom role name |
| `-TeamPrefix` | `TEAM_PREFIX` | `copilot-seat-mgmt` | Team name prefix |
| `-MaxOrgsPerTeam` | `MAX_ORGS_PER_TEAM` | `1000` | Max orgs per team |

## ⚠️ Important caveats

These endpoints are **recent/preview** features. Verify the following against your
tenant's REST reference before running in production:

- Enterprise custom-role endpoint path (`/enterprises/{ent}/custom-roles`).
- The Copilot permission slug (`manage_organization_copilot_seat_assignments`).
- The assign-role-to-team endpoint
  (`/enterprises/{ent}/teams/{team_slug}/organization-roles`).

Run against a test enterprise first.

## References

- [Enterprise teams REST reference](https://docs.github.com/en/enterprise-cloud@latest/rest/enterprise-admin/enterprise-teams)
- [Creating custom roles in an enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/managing-accounts-and-repositories/managing-roles-in-your-enterprise/create-custom-roles)
- [Managing roles and governance via enterprise teams (public preview)](https://github.blog/changelog/2025-10-23-managing-roles-and-governance-via-enterprise-teams-is-in-public-preview/)
- [About custom organization roles](https://docs.github.com/en/organizations/organizing-members-into-teams/managing-custom-organization-roles-for-an-organization/about-custom-organization-roles)
