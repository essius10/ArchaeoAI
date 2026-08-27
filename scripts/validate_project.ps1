[CmdletBinding()]
param(
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
$required = @(
    'README.md',
    'pyproject.toml',
    'configs/e001.example.toml',
    'data/README.md',
    'data/manifests/example-dataset.toml',
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
    'scripts/doctor.ps1',
    'src/archaeoai/__init__.py',
    'src/archaeoai/config.py',
    'src/archaeoai/paths.py',
    'src/archaeoai/data/manifest.py',
    'tests/test_config.py',
    'tests/test_manifest.py',
    'tests/test_package.py',
    'tests/test_paths.py'
)

$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing) {
    throw "Missing required research artifacts: $($missing -join ', ')"
}

if ((Get-Content -Raw 'README.md') -notmatch 'geographically disjoint holdout') {
    throw 'README must state the geographic-holdout principle.'
}

$projectConfig = Get-Content -Raw 'pyproject.toml'
if ($projectConfig -notmatch 'requires-python\s*=\s*">=3\.12,<3\.15"') {
    throw 'pyproject.toml must support Python >=3.12,<3.15.'
}

$exampleManifest = Get-Content -Raw 'data/manifests/example-dataset.toml'
if ($exampleManifest -notmatch 'status\s*=\s*"template"' -or $exampleManifest -notmatch 'example\.invalid') {
    throw 'The example dataset manifest must remain explicitly fictional and in template status.'
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
