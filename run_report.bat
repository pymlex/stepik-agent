@echo off
cd /d "%~dp0"
if not exist .env copy .env.example .env
python scripts\generate_report.py
pause
