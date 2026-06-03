$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root
$env:STEPIK_AGENT_MOCK_LLM = "1"
python -m pytest tests/ -v
