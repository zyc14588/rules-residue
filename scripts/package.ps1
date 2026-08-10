$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -3.11 .\tools\build_package.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
