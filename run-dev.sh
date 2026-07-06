#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing local Python environment."
  echo "Run: python3 -m venv .venv"
  echo "Then: .venv/bin/pip install -r requirements.txt"
  exit 1
fi

MODE="${1:-help}"
STYLE_BERT_ROOT="${WATCHLESS_LOCAL_VOICE_REPO:-$HOME/Style-Bert-VITS2}"
STYLE_BERT_PYTHON="${STYLE_BERT_ROOT}/.venv/bin/python"
STYLE_BERT_ASSETS="${WATCHLESS_LOCAL_VOICE_ASSETS_ROOT:-$STYLE_BERT_ROOT/model_assets}"
LOCAL_VOICE_HOST="${WATCHLESS_LOCAL_VOICE_HOST:-127.0.0.1}"
LOCAL_VOICE_PORT="${WATCHLESS_LOCAL_VOICE_PORT:-5000}"

case "$MODE" in
  browser)
    echo "Starting WatchLess in browser mode at http://127.0.0.1:5055"
    .venv/bin/python - <<'PY'
from watchless_app.app import create_app
app = create_app()
app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)
PY
    ;;
  app)
    echo "Starting WatchLess desktop app from source"
    .venv/bin/python desktop_app.py
    ;;
  app-watch)
    echo "Starting WatchLess desktop app from source with auto-restart on file save"
    .venv/bin/python dev_app_runner.py
    ;;
  voice)
    if [ ! -x "$STYLE_BERT_PYTHON" ]; then
      echo "Missing Style-Bert Python environment at $STYLE_BERT_PYTHON"
      echo "Expected repo: $STYLE_BERT_ROOT"
      echo "Set WATCHLESS_LOCAL_VOICE_REPO if your Style-Bert-VITS2 folder lives somewhere else."
      exit 1
    fi
    echo "Starting WatchLess local voice server at http://${LOCAL_VOICE_HOST}:${LOCAL_VOICE_PORT}"
    echo "Using Style-Bert repo: $STYLE_BERT_ROOT"
    echo "Using model assets: $STYLE_BERT_ASSETS"
    "$STYLE_BERT_PYTHON" watchless_app/local_voice_server.py \
      --style-bert-dir "$STYLE_BERT_ROOT" \
      --assets-root "$STYLE_BERT_ASSETS" \
      --host "$LOCAL_VOICE_HOST" \
      --port "$LOCAL_VOICE_PORT" \
      --device cpu
    ;;
  build)
    echo "Building local unsigned app bundle in dist/"
    ./publish.sh --unsigned-local
    ;;
  help|--help|-h)
    echo "Usage: ./run-dev.sh [browser|app|app-watch|voice|build]"
    echo ""
    echo "browser  Run the app locally in your web browser"
    echo "app      Run the desktop app directly from source once"
    echo "app-watch Run the desktop app from source and restart it after file saves"
    echo "voice    Run the local Style-Bert voice server for WatchLess narration"
    echo "build    Rebuild the packaged app in dist/"
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: ./run-dev.sh [browser|app|app-watch|voice|build]"
    exit 1
    ;;
esac
