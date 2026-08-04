#!/usr/bin/env bash
#
# Creates a Copilot seat-management custom role and enterprise teams covering all
# organizations in the enterprise, then assigns the role to each team.
#
# Requires the GitHub CLI (gh) authenticated with an enterprise-admin token.
# gh reads GH_TOKEN / GITHUB_TOKEN from the environment - never hardcode secrets.
#
# NOTE: Enterprise custom-role and role-on-team endpoints are recent/preview
# features - confirm exact paths & field names against your tenant before running.
#
# Usage:
#   gh auth login                 # or export GH_TOKEN=...
#   ./setup-copilot-seat-mgmt-teams.sh my-enterprise

set -euo pipefail

ENTERPRISE="${1:?enterprise slug required}"
ROLE_NAME="${ROLE_NAME:-copilot-seat-manager}"
TEAM_PREFIX="${TEAM_PREFIX:-copilot-seat-mgmt}"
MAX_ORGS_PER_TEAM="${MAX_ORGS_PER_TEAM:-1000}"
BASE="/enterprises/${ENTERPRISE}"

# 1. Create the enterprise custom role with the Copilot seat-management permission.
ROLE_ID=$(gh api -X POST "${BASE}/custom-roles" \
  -f name="${ROLE_NAME}" \
  -f description="Assign/remove Copilot seats across organizations" \
  -f 'permissions[]=manage_organization_copilot_seat_assignments' \
  --jq '.id')
echo "Created custom role '${ROLE_NAME}' (id: ${ROLE_ID})."

# 2. List all orgs, sort A-Z.
mapfile -t ORGS < <(gh api --paginate "${BASE}/organizations" --jq '.[].login' | sort)
TOTAL=${#ORGS[@]}
echo "Total organizations: ${TOTAL}"

# Balance the split so no team exceeds the limit.
TEAM_COUNT=$(( (TOTAL + MAX_ORGS_PER_TEAM - 1) / MAX_ORGS_PER_TEAM ))
CHUNK_SIZE=$(( (TOTAL + TEAM_COUNT - 1) / TEAM_COUNT ))

# 3. Create each team, attach its orgs, assign the role.
index=1
for (( start=0; start<TOTAL; start+=CHUNK_SIZE )); do
  chunk=("${ORGS[@]:start:CHUNK_SIZE}")
  team_name="${TEAM_PREFIX}-${index}"

  # Build a JSON array of org logins for this chunk.
  orgs_json=$(printf '%s\n' "${chunk[@]}" | jq -R . | jq -s .)

  team_slug=$(gh api -X POST "${BASE}/teams" \
    -f name="${team_name}" \
    -f description="Copilot seat managers (batch ${index})" \
    -f organization_access="manual" \
    -f organizations="${orgs_json}" \
    --jq '.slug')
  echo "Created team '${team_name}' with ${#chunk[@]} orgs."

  gh api -X POST "${BASE}/teams/${team_slug}/organization-roles" \
    -F role_id="${ROLE_ID}" >/dev/null
  echo "Assigned role '${ROLE_NAME}' to team '${team_name}'."

  index=$(( index + 1 ))
done

echo "Done. Members added to these teams can manage Copilot seats across all orgs."
