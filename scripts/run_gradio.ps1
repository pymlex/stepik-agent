$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
python main.py
