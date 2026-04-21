#!/usr/bin/env bash
# Image Tools — 1-Click Launcher (Mac/Linux)
set -e
cd "$(dirname "$0")"

echo
echo "  Image Tools - Starting up..."
echo

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "  [ERROR] Python 3 is not installed."
  echo "  Install from https://python.org or 'brew install python' (Mac)"
  exit 1
fi

# Install dependencies (idempotent)
echo "  Installing dependencies (first run takes a few minutes)..."
python3 -m pip install -q -r requirements.txt

# Open browser after 2 seconds
( sleep 2 && (open http://localhost:5001 2>/dev/null || xdg-open http://localhost:5001 2>/dev/null) ) &

# Run server
echo
echo "  Server starting at http://localhost:5001"
echo "  Press Ctrl+C to stop."
echo
python3 web.py
