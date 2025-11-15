param([string]$Python="python")
Write-Host "== Neuravia install (Windows) =="
$ErrorActionPreference="Stop"
& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -U pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev,web]"
Write-Host "OK. Utilisez: .\.venv\Scripts\python.exe -m neuravia --help"
