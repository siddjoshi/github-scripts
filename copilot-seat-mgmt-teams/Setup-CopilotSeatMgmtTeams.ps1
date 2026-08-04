#Requires -Version 7.0
<#
.SYNOPSIS
    Creates a Copilot seat-management custom role and enterprise teams covering all
    organizations in the enterprise, then assigns the role to each team.
.DESCRIPTION
    Uses the GitHub enterprise teams / custom roles REST API.
    The token is read from the GITHUB_TOKEN environment variable (never hardcode secrets).
    Requires a token with enterprise admin scope.

    NOTE: Enterprise custom-role and role-on-team endpoints are recent/preview features -
    confirm the exact paths & field names against your tenant's REST reference before running.
.PARAMETER Enterprise
    The enterprise slug.
.PARAMETER RoleName
    The name of the enterprise custom role to create.
.PARAMETER TeamPrefix
    Prefix used to name each enterprise team (a numeric suffix is appended).
.PARAMETER MaxOrgsPerTeam
    Maximum organizations per team (GitHub limit is 1000).
.EXAMPLE
    $env:GITHUB_TOKEN = 'ghp_xxx'
    pwsh ./Setup-CopilotSeatMgmtTeams.ps1 -Enterprise 'my-enterprise'
#>

param(
    [Parameter(Mandatory)][string]$Enterprise,
    [string]$RoleName    = "copilot-seat-manager",
    [string]$TeamPrefix  = "copilot-seat-mgmt",
    [ValidateRange(1, 1000)][int]$MaxOrgsPerTeam = 1000
)

$ErrorActionPreference = 'Stop'

# Never hardcode secrets/tokens - read from environment.
$token = $env:GITHUB_TOKEN
if (-not $token) { throw "GITHUB_TOKEN environment variable is not set." }

$headers = @{
    Authorization          = "Bearer $token"
    Accept                 = "application/vnd.github+json"
    'X-GitHub-Api-Version' = "2022-11-28"
}
$base = "https://api.github.com/enterprises/$Enterprise"

# ---------------------------------------------------------------------------
# 1. Create an enterprise custom role with Copilot seat-management permission
# ---------------------------------------------------------------------------
$roleBody = @{
    name        = $RoleName
    description = "Assign/remove Copilot seats across organizations"
    # Confirm the exact permission slug for your tenant.
    permissions = @("manage_organization_copilot_seat_assignments")
} | ConvertTo-Json

$role = Invoke-RestMethod -Uri "$base/custom-roles" -Headers $headers `
        -Method Post -Body $roleBody -ContentType "application/json"
Write-Host "Created custom role '$($role.name)' (id: $($role.id))."

# ---------------------------------------------------------------------------
# 2. Gather all orgs, sort A-Z, split into balanced chunks of <= MaxOrgsPerTeam
# ---------------------------------------------------------------------------
$orgs = [System.Collections.Generic.List[string]]::new()
$page = 1
do {
    $resp = Invoke-RestMethod -Uri "$base/organizations?per_page=100&page=$page" `
            -Headers $headers -Method Get
    foreach ($o in $resp) { $orgs.Add($o.login) }
    $page++
} while ($resp.Count -eq 100)

$sorted = $orgs | Sort-Object
Write-Host "Total organizations: $($sorted.Count)"

# Balance the split so no team exceeds the limit (e.g. 1995 -> 998 / 997).
$teamCount = [math]::Ceiling($sorted.Count / $MaxOrgsPerTeam)
$chunkSize = [math]::Ceiling($sorted.Count / $teamCount)
$chunks = for ($i = 0; $i -lt $sorted.Count; $i += $chunkSize) {
    ,($sorted[$i..([math]::Min($i + $chunkSize - 1, $sorted.Count - 1))])
}

# ---------------------------------------------------------------------------
# 3. Create each team, attach its orgs, and assign the custom role
# ---------------------------------------------------------------------------
$index = 1
foreach ($chunk in $chunks) {
    $teamName = "$TeamPrefix-$index"

    $teamBody = @{
        name                = $teamName
        description         = "Copilot seat managers (batch $index)"
        organization_access = "manual"
        organizations       = @($chunk)
    } | ConvertTo-Json

    $team = Invoke-RestMethod -Uri "$base/teams" -Headers $headers `
            -Method Post -Body $teamBody -ContentType "application/json"
    Write-Host "Created team '$($team.name)' with $($chunk.Count) orgs."

    # Assign the custom org role to this enterprise team (applies in every attached org).
    $roleAssignBody = @{ role_id = $role.id } | ConvertTo-Json
    Invoke-RestMethod -Uri "$base/teams/$($team.slug)/organization-roles" `
        -Headers $headers -Method Post -Body $roleAssignBody -ContentType "application/json"
    Write-Host "Assigned role '$RoleName' to team '$($team.name)'."

    $index++
}

Write-Host "Done. Members added to these teams can manage Copilot seats across all orgs."
