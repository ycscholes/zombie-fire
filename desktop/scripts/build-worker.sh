#!/usr/bin/env bash
set -euo pipefail

# 将 worker 与 Python runtime 打成独立 sidecar，并按 Tauri 目标三元组命名。
DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$DESKTOP_ROOT/.." && pwd)"
VENV_PYTHON="$DESKTOP_ROOT/.venv/bin/python"
SIDECAR_DIR="$DESKTOP_ROOT/src-tauri/binaries"
SIDECAR_RAW="$SIDECAR_DIR/zombie-fire-worker"
HELPER="$DESKTOP_ROOT/src-tauri/resources/bin/zombie_cgclick"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS sidecar 当前只支持在 macOS 主机构建。" >&2
  exit 2
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "缺少构建虚拟环境；先运行 python3 -m venv desktop/.venv 并安装 requirements-build.txt。" >&2
  exit 2
fi
if [[ ! -x "$HELPER" ]]; then
  "$VENV_PYTHON" "$DESKTOP_ROOT/scripts/build-helper.py"
fi

mkdir -p "$SIDECAR_DIR" "$DESKTOP_ROOT/build/pyinstaller"
rm -f "$SIDECAR_RAW"
"$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name zombie-fire-worker \
  --distpath "$SIDECAR_DIR" \
  --workpath "$DESKTOP_ROOT/build/pyinstaller/work" \
  --specpath "$DESKTOP_ROOT/build/pyinstaller" \
  --paths "$REPOSITORY_ROOT" \
  --collect-submodules scripts.zombie_tasks \
  --add-data "$HELPER:resources/bin" \
  "$REPOSITORY_ROOT/scripts/desktop_worker.py"

RUST_HOST="$(rustc -vV | sed -n 's/^host: //p')"
if [[ -z "$RUST_HOST" ]]; then
  echo "无法识别 Rust 构建目标；请先安装对应的 stable toolchain。" >&2
  exit 2
fi
PYTHON_ARCH="$("$VENV_PYTHON" -c 'import platform; print(platform.machine())')"
case "$PYTHON_ARCH" in
  arm64|aarch64) PYTHON_ARCH="aarch64" ;;
  amd64|x64) PYTHON_ARCH="x86_64" ;;
esac
if [[ "$RUST_HOST" != "$PYTHON_ARCH-apple-darwin" ]]; then
  echo "Rust 目标 $RUST_HOST 与 Python 架构 $PYTHON_ARCH 不一致；请使用同架构工具链和构建环境。" >&2
  exit 2
fi
mv "$SIDECAR_RAW" "$SIDECAR_DIR/zombie-fire-worker-$RUST_HOST"
chmod +x "$SIDECAR_DIR/zombie-fire-worker-$RUST_HOST"
echo "Built $SIDECAR_DIR/zombie-fire-worker-$RUST_HOST"
