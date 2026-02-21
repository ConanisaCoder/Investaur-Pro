#!/bin/bash
# Run INVESTAUR PRO — creates venv if needed
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -q
fi

.venv/bin/python main.py
