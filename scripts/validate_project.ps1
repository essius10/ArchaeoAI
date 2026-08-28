[CmdletBinding()]
param(
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$required = @(
    'README.md',
    'CONTRIBUTING.md',
    'SECURITY.md',
    'CITATION.cff',
    'pyproject.toml',
    '.github/ISSUE_TEMPLATE/bug_report.yml',
    '.github/ISSUE_TEMPLATE/research_methodology.yml',
    '.github/ISSUE_TEMPLATE/reproducibility.yml',
    '.github/ISSUE_TEMPLATE/documentation.yml',
    'configs/e001.example.toml',
    'data/README.md',
    'data/manifests/example-dataset.toml',
    'docs/environment-audit.md',
    'docs/e001-feasibility-audit.md',
    'docs/e001-phase-2a5-curation-gate.md',
    'docs/research-charter.md',
    'docs/literature-novelty-audit.md',
    'docs/licensing-and-attribution.md',
    'docs/dataset-decision-record.md',
    'docs/research-questions.md',
    'docs/roadmap.md',
    'docs/decision-log.md',
    'docs/project-quality-bar.md',
    'docs/claims-register.md',
    'research-log/README.md',
    'experiments/E001_geographic_baseline.md',
    'scripts/doctor.ps1',
    'scripts/audit_nhle_bowl_barrows.py',
    'scripts/curate_e001_labels.py',
    'src/archaeoai/__init__.py',
    'src/archaeoai/config.py',
    'src/archaeoai/paths.py',
    'src/archaeoai/nhle_audit.py',
    'src/archaeoai/curation.py',
    'src/archaeoai/terrain_metadata.py',
    'src/archaeoai/data/manifest.py',
    'tests/test_config.py',
    'tests/test_manifest.py',
    'tests/test_package.py',
    'tests/test_paths.py',
    'tests/test_nhle_audit.py',
    'tests/test_curation.py',
    'tests/test_terrain_metadata.py',
    'outputs/feasibility/bowl_barrow_summary.json',
    'outputs/feasibility/bowl_barrow_counts.csv',
    'outputs/feasibility/bowl_barrow_manual_sample.csv',
    'outputs/feasibility/e001_curation_summary.json',
    'outputs/feasibility/e001_curated_records.csv',
    'outputs/feasibility/e001_group_counts.csv',
    'outputs/feasibility/e001_provenance_summary.csv',
    'outputs/feasibility/e001_second_review_queue.csv'
)

$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    throw "Missing required research artifacts: $($missing -join ', ')"
}

$readme = Get-Content -Raw 'README.md'
if ($readme -notmatch 'geographically (?:disjoint|separated) holdouts?') {
    throw 'README must state the geographic-holdout principle.'
}
if (
    $readme -notmatch 'No model has been trained' -or
    $readme -notmatch 'has not discovered archaeological sites' -or
    $readme -notmatch '261' -or
    $readme -notmatch '12'
) {
    throw 'README must preserve the verified Phase 2A.5 status and explicit no-claim boundary.'
}

$citation = Get-Content -Raw 'CITATION.cff'
if (
    $citation -notmatch 'cff-version:\s*1\.2\.0' -or
    $citation -notmatch 'repository-code:\s*"https://github\.com/essius10/ArchaeoAI"' -or
    $citation -match '(?m)^\s*(?:doi|license):'
) {
    throw 'CITATION.cff must use verified repository metadata without a DOI or licence claim.'
}

$licensingAudit = Get-Content -Raw 'docs/licensing-and-attribution.md'
if (
    $licensingAudit -notmatch 'does \*\*not\*\* currently have a repository-wide licence' -or
    $licensingAudit -notmatch 'Open Government Licence v3\.0'
) {
    throw 'The licensing audit must preserve the current no-licence status and OGL boundary.'
}

$projectConfig = Get-Content -Raw 'pyproject.toml'
if ($projectConfig -notmatch 'requires-python\s*=\s*">=3\.12,<3\.15"') {
    throw 'pyproject.toml must support Python >=3.12,<3.15.'
}

$exampleManifest = Get-Content -Raw 'data/manifests/example-dataset.toml'
if ($exampleManifest -notmatch 'status\s*=\s*"template"' -or $exampleManifest -notmatch 'example\.invalid') {
    throw 'The example dataset manifest must remain explicitly fictional and in template status.'
}

$auditSummary = Get-Content -Raw 'outputs/feasibility/bowl_barrow_summary.json' | ConvertFrom-Json
if (
    $auditSummary.privacy.stored_coordinates -ne $false -or
    $auditSummary.privacy.stored_geometry -ne $false -or
    $auditSummary.counts.total_scheduled_monument_records_examined -le 0
) {
    throw 'The Phase 2A summary must be coordinate-free and contain a verified source count.'
}
$aggregateHeaders = (Get-Content 'outputs/feasibility/bowl_barrow_counts.csv' -TotalCount 1)
$manualHeaders = (Get-Content 'outputs/feasibility/bowl_barrow_manual_sample.csv' -TotalCount 1)
if ($aggregateHeaders -match 'Easting|Northing|NGR' -or $manualHeaders -match 'Easting|Northing|NGR') {
    throw 'Tracked Phase 2A CSV outputs must not contain exact-coordinate fields.'
}
$auditCounts = $auditSummary.counts
if (
    $auditCounts.broad_barrow_candidates -ne (
        $auditCounts.probable_bowl_candidates +
        $auditCounts.clear_title_exclusions +
        $auditCounts.manual_review_required
    )
) {
    throw 'Phase 2A triage counts must partition all broad barrow candidates.'
}
$aggregateRows = Import-Csv 'outputs/feasibility/bowl_barrow_counts.csv'
$aggregateProbable = ($aggregateRows | Measure-Object -Property probable_bowl_candidates -Sum).Sum
$aggregateExcluded = ($aggregateRows | Measure-Object -Property clear_title_exclusions -Sum).Sum
$aggregateManual = ($aggregateRows | Measure-Object -Property manual_review_required -Sum).Sum
if (
    $aggregateProbable -ne $auditCounts.probable_bowl_candidates -or
    $aggregateExcluded -ne $auditCounts.clear_title_exclusions -or
    $aggregateManual -ne $auditCounts.manual_review_required
) {
    throw 'Phase 2A aggregate CSV counts must match the JSON summary.'
}
$manualRows = Import-Csv 'outputs/feasibility/bowl_barrow_manual_sample.csv'
$manualIds = @($manualRows.list_entry | Sort-Object)
$sampleIds = @($auditSummary.manual_sample.record_ids | ForEach-Object { "$_" } | Sort-Object)
if ($manualRows.Count -ne $sampleIds.Count -or (Compare-Object $manualIds $sampleIds)) {
    throw 'The manual-review artifact must match the deterministic sample in the JSON summary.'
}

$curationSummary = Get-Content -Raw 'outputs/feasibility/e001_curation_summary.json' | ConvertFrom-Json
$curationCounts = $curationSummary.counts
$curationRows = @(Import-Csv 'outputs/feasibility/e001_curated_records.csv')
if (
    $curationSummary.privacy.stored_coordinates -ne $false -or
    $curationSummary.privacy.stored_geometry -ne $false -or
    $curationRows.Count -ne $curationCounts.records_reviewed
) {
    throw 'The Phase 2A.5 curation output must be complete and coordinate-free.'
}
$statusTotal = (
    $curationCounts.accepted +
    $curationCounts.rejected +
    $curationCounts.uncertain +
    $curationCounts.needs_geometry_review +
    $curationCounts.needs_terrain_review
)
if ($statusTotal -ne $curationCounts.records_reviewed) {
    throw 'Phase 2A.5 review statuses must partition the reviewed queue.'
}
$acceptedRows = @($curationRows | Where-Object { $_.review_status -eq 'accepted' })
if ($acceptedRows.Count -ne $curationCounts.accepted) {
    throw 'Tracked accepted rows must match the Phase 2A.5 summary.'
}
$invalidAccepted = @(
    $acceptedRows | Where-Object {
        $_.bowl_barrow_identity -ne 'yes' -or
        $_.single_monument -ne 'yes' -or
        $_.upstanding_earthwork -ne 'yes' -or
        $_.geometry_qa -ne 'pass' -or
        $_.terrain_coverage -ne 'pass' -or
        $_.terrain_provenance -ne 'pass'
    }
)
if ($invalidAccepted.Count -ne 0) {
    throw 'Every accepted E001 record must pass all six evidence and QA gates.'
}
$trackedCurationHeaders = Get-Content 'outputs/feasibility/e001_curated_records.csv' -TotalCount 1
$curationHeaderFields = @($trackedCurationHeaders -split ',')
if ($curationHeaderFields -match '^(Easting|Northing|NGR|Latitude|Longitude|Geometry|Polygon|BBox)$') {
    throw 'Tracked Phase 2A.5 outputs must not contain exact-coordinate or geometry fields.'
}
$privateIgnoreCheck = & git check-ignore 'data/private/e001-private-sentinel.json'
if ($LASTEXITCODE -ne 0 -or -not $privateIgnoreCheck) {
    throw 'data/private must remain ignored by Git.'
}

$projectRootPath = (Resolve-Path '.').Path
$venvPythonPath = Join-Path $projectRootPath '.venv\Scripts\python.exe'
if ($PythonPath) {
    $pythonExecutable = (Resolve-Path $PythonPath).Path
} elseif (Test-Path $venvPythonPath) {
    $pythonExecutable = (Resolve-Path $venvPythonPath).Path
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw 'Python was not found. Create .venv before validating Phase 1.'
    }
    $pythonExecutable = $pythonCommand.Source
}

$runtimeCheck = & $pythonExecutable -c 'import sys; assert sys.implementation.name == "cpython" and (3, 12) <= sys.version_info[:2] < (3, 15); print(f"CPython {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
if ($LASTEXITCODE -ne 0) {
    throw 'Python must be a working CPython >=3.12,<3.15 runtime.'
}

$phaseOneCheck = & $pythonExecutable -c 'from pathlib import Path; from archaeoai.config import load_experiment_config; from archaeoai.data.manifest import load_dataset_manifest; root = Path.cwd(); load_experiment_config(root / "configs" / "e001.example.toml"); load_dataset_manifest(root / "data" / "manifests" / "example-dataset.toml"); print("configuration and manifest valid")'
if ($LASTEXITCODE -ne 0) {
    throw 'Phase 1 configuration or manifest validation failed.'
}

Write-Output "Validation passed: $($required.Count) required artifacts; $runtimeCheck; $phaseOneCheck."
