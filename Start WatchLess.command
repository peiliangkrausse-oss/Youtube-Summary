#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"
.venv/bin/python desktop_app.py
