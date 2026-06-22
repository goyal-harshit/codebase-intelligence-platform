#!/usr/bin/env bash
# One-command launcher (macOS/Linux). No third-party packages required.
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Python 3 not found."; exit 1; }
( sleep 3; (command -v xdg-open && xdg-open http://127.0.0.1:8500) || (command -v open && open http://127.0.0.1:8500) ) >/dev/null 2>&1 &
echo "Codebase Intelligence UI -> http://127.0.0.1:8500  (Ctrl+C to stop)"
python3 scripts/serve.py --port 8500 --host 127.0.0.1 --root "$(pwd)"
