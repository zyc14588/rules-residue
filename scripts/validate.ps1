$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3.11 .\tools\run_acceptance.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
