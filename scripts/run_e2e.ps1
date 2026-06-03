$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root
python scripts/run_e2e.py
exit $LASTEXITCODE
