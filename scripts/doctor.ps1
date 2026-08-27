[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

Write-Output 'ArchaeoAI environment check'
Write-Output "PowerShell: $($PSVersionTable.PSVersion)"

$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    Write-Warning 'Python is not on PATH. Install Python 3.12+ before running the data pipeline.'
} else {
    & $python.Source --version
}

$gpu = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($null -eq $gpu) {
    Write-Warning 'nvidia-smi was not found; GPU availability is unverified.'
} else {
    & $gpu.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader
}

$git = Get-Command git -ErrorAction SilentlyContinue
if ($null -eq $git) {
    Write-Warning 'Git is not on PATH.'
} else {
    & $git.Source --version
}
