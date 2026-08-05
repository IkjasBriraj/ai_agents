param(
    [switch]$SkipOllamaCheck
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

function Assert-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name was not found. $InstallHint"
    }
}

Assert-Command python "Install Python 3.10 or later and add it to PATH."
Assert-Command npm "Install Node.js 20 or later and add it to PATH."

if (-not $SkipOllamaCheck -and -not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Warning "Ollama was not found. The UI will start, but AI conversations will stay unavailable. Install Ollama or rerun with -SkipOllamaCheck."
}

if (-not (Test-Path (Join-Path $projectRoot 'frontend\\node_modules'))) {
    throw "Frontend dependencies are missing. Run 'npm install' from the frontend directory first."
}

Write-Host "Starting SeniorAgent backend at http://localhost:8000"
Start-Process -FilePath python -ArgumentList 'main.py' -WorkingDirectory (Join-Path $projectRoot 'backend')

Write-Host "Starting SeniorAgent frontend at http://localhost:5173"
Start-Process -FilePath npm.cmd -ArgumentList 'run', 'dev' -WorkingDirectory (Join-Path $projectRoot 'frontend')

Write-Host "Open http://localhost:5173 after both services finish starting."
