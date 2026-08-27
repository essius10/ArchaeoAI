[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$required = @(
    'README.md',
    'docs/environment-audit.md',
    'docs/research-charter.md',
    'docs/literature-novelty-audit.md',
    'docs/dataset-decision-record.md',
    'docs/research-questions.md',
    'docs/roadmap.md',
    'docs/decision-log.md',
    'docs/project-quality-bar.md',
    'docs/claims-register.md',
    'research-log/README.md',
    'experiments/E001_geographic_baseline.md',
    'scripts/doctor.ps1'
)

$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    throw "Missing required research artifacts: $($missing -join ', ')"
}

if ((Get-Content -Raw 'README.md') -notmatch 'geographically disjoint holdout') {
    throw 'README must state the geographic-holdout principle.'
}

Write-Output "Validation passed: $($required.Count) required research artifacts are present."
