#!/usr/bin/env bash
set -euo pipefail

# Build a standalone executable using PyInstaller
# Requires: Python, PySide6, PyInstaller
# Output: dist/mypaint (single-file executable)

set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv_build"

echo "==> Creating virtual environment..."
uv venv "$VENV"
source "$VENV/bin/activate"

echo "==> Installing PyInstaller and PySide6..."
uv pip install --quiet pyinstaller PySide6 2>&1 | tail -1

echo "==> Building standalone executable..."
pyinstaller \
    --onefile \
    --noconsole \
    --name mypaint \
    --collect-submodules mypaint \
    main.py

echo ""
echo "==> Done! Executable at: dist/mypaint"
echo "    Run with: ./dist/mypaint"
