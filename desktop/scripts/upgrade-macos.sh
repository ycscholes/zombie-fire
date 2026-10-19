#!/usr/bin/env bash
set -euo pipefail

# 升级入口固定按“检查身份、拒绝运行进程、构建签名包、原子安装”顺序执行。
DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DESKTOP_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS 应用只能在 macOS 上升级。" >&2
  exit 2
fi
source "$DESKTOP_ROOT/scripts/macos-signing-common.sh"
require_signing_identity >/dev/null

if ! command -v npm >/dev/null || ! command -v python3 >/dev/null; then
  echo "升级需要 Node.js/npm 与 Python 3。" >&2
  exit 2
fi

python3 "$DESKTOP_ROOT/scripts/install-macos.py" --check-running
npm run build:app
python3 "$DESKTOP_ROOT/scripts/install-macos.py" "$DESKTOP_ROOT/release/向僵尸开炮日常助手.app"
