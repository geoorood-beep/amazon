#!/bin/zsh
set -e

OPERATOR_ROOT="$(cd "$(dirname "$0")" && pwd)"
OPERATOR_FRONTEND="$OPERATOR_ROOT/operator_console"
OPERATOR_PYTHON="$OPERATOR_ROOT/.venv/bin/python"

if [[ ! -x "$OPERATOR_PYTHON" ]]; then
  python3 -m venv "$OPERATOR_ROOT/.venv"
  "$OPERATOR_ROOT/.venv/bin/pip" install -r "$OPERATOR_ROOT/requirements.txt"
fi

if [[ ! -d "$OPERATOR_FRONTEND/node_modules" ]]; then
  cd "$OPERATOR_FRONTEND"
  npm install
fi

cd "$OPERATOR_FRONTEND"
npm run build

"$OPERATOR_PYTHON" "$OPERATOR_ROOT/scripts/run_operator_console_backend.py" &
OPERATOR_BACKEND_PID=$!

npm run start &
OPERATOR_FRONTEND_PID=$!

cleanup_operator_console() {
  kill "$OPERATOR_BACKEND_PID" "$OPERATOR_FRONTEND_PID" 2>/dev/null || true
}
trap cleanup_operator_console EXIT INT TERM

sleep 2
open "http://localhost:3000/"

echo "陆遥广告运营台已启动：http://localhost:3000/"
echo "关闭本窗口即可停止。"
wait
