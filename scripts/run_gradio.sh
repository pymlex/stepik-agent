#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] || cp .env.example .env
python main.py
