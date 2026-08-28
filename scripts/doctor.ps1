[CmdletBinding()]
param(
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRootPath = (Resolve-Path (Join-Path $scriptDirectory '..')).Path
$venvPythonPath = Join-Path $projectRootPath '.venv\Scripts\python.exe'

if (-not (Test-Path (Join-Path $projectRootPath 'pyproject.toml'))) {
    throw "Not an ArchaeoAI project directory: $projectRootPath"
}

if ($PythonPath) {
    $pythonExecutable = (Resolve-Path $PythonPath).Path
} elseif (Test-Path $venvPythonPath) {
    $pythonExecutable = (Resolve-Path $venvPythonPath).Path
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw 'Python was not found. ArchaeoAI requires CPython >=3.12,<3.15.'
    }
    $pythonExecutable = $pythonCommand.Source
}

$runtimeJson = & $pythonExecutable -c 'import json, sys; print(json.dumps({"executable": sys.executable, "implementation": sys.implementation.name, "version": list(sys.version_info[:3])}))'
if ($LASTEXITCODE -ne 0) {
    throw "Python command failed: $pythonExecutable"
}
$runtime = $runtimeJson | ConvertFrom-Json
$runtimeVersion = $runtime.version
if (
    $runtime.implementation -ne 'cpython' -or
    $runtimeVersion[0] -ne 3 -or
    $runtimeVersion[1] -lt 12 -or
    $runtimeVersion[1] -ge 15
) {
    throw "Unsupported Python runtime: $($runtime.implementation) $($runtimeVersion -join '.')"
}

$packageVersion = & $pythonExecutable -c 'import archaeoai; print(archaeoai.__version__)'
if ($LASTEXITCODE -ne 0) {
    throw 'The archaeoai package is not importable. Install with: python -m pip install -e ".[dev]"'
}
$pytestVersion = & $pythonExecutable -m pytest --version
if ($LASTEXITCODE -ne 0) {
    throw 'pytest is unavailable in the selected Python environment.'
}
$ruffVersion = & $pythonExecutable -m ruff --version
if ($LASTEXITCODE -ne 0) {
    throw 'Ruff is unavailable in the selected Python environment.'
}
$geospatialJson = & $pythonExecutable -c 'import json, numpy, pyproj, rasterio; print(json.dumps({"numpy": numpy.__version__, "rasterio": rasterio.__version__, "gdal": rasterio.__gdal_version__, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str, "epsg27700": pyproj.CRS.from_epsg(27700).name}))'
if ($LASTEXITCODE -ne 0) {
    throw 'The Phase 2B geospatial runtime is unavailable.'
}
$geospatial = $geospatialJson | ConvertFrom-Json

$gitCommand = Get-Command git -ErrorAction SilentlyContinue
if ($null -eq $gitCommand) {
    throw 'Git is not on PATH.'
}
$gitVersion = & $gitCommand.Source --version
$gitStatus = & $gitCommand.Source -C $projectRootPath status --short --branch
if ($LASTEXITCODE -ne 0) {
    throw 'Git could not inspect the ArchaeoAI repository.'
}

Write-Output 'ArchaeoAI environment check: PASS'
Write-Output "Project root: $projectRootPath"
Write-Output "PowerShell: $($PSVersionTable.PSVersion)"
Write-Output "Python: CPython $($runtimeVersion -join '.')"
Write-Output "Python executable: $($runtime.executable)"
Write-Output "ArchaeoAI package: $packageVersion"
Write-Output "pytest: $pytestVersion"
Write-Output "Ruff: $ruffVersion"
Write-Output "NumPy: $($geospatial.numpy)"
Write-Output "Rasterio/GDAL: $($geospatial.rasterio) / $($geospatial.gdal)"
Write-Output "PyProj/PROJ: $($geospatial.pyproj) / $($geospatial.proj)"
Write-Output "CRS smoke test: EPSG:27700 = $($geospatial.epsg27700)"
Write-Output "Git: $gitVersion"
Write-Output "Git status: $($gitStatus -join ' | ')"

$gpuCommand = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($null -eq $gpuCommand) {
    Write-Output 'GPU: nvidia-smi not found (optional during Phase 2B)'
} else {
    $gpuSummary = & $gpuCommand.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader
    Write-Output "GPU: $gpuSummary (optional during Phase 2B)"
}
