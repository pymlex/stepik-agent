Set-Location (Split-Path -Parent $PSScriptRoot)
python scripts/run_e2e.py
exit $LASTEXITCODE
