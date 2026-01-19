#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$REPO_ROOT/.venv"

python3 -m venv "$VENV_PATH"

"$VENV_PATH/bin/python" -m pip install --upgrade pip

if [[ -f "$REPO_ROOT/requirements.txt" ]]; then
  "$VENV_PATH/bin/pip" install -r "$REPO_ROOT/requirements.txt"
fi

if [[ -f "$REPO_ROOT/requirements-dev.txt" ]]; then
  "$VENV_PATH/bin/pip" install -r "$REPO_ROOT/requirements-dev.txt"
fi

echo "Environment ready. Activate with: source $VENV_PATH/bin/activate"
