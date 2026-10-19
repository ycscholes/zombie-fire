#!/usr/bin/env bash
set -euo pipefail

# 一次性生成 macOS 点击 helper、Python sidecar、Web 资源与 .app 包。
DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DESKTOP_ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "首版 .app 必须在 macOS 上构建。" >&2
  exit 2
fi
# 在安装 Node、Rust 与 Python 构建依赖前校验稳定身份，避免无签名配置时耗时构建。
source "$DESKTOP_ROOT/scripts/macos-signing-common.sh"
require_signing_identity >/dev/null
if ! command -v python3 >/dev/null; then
  echo "构建需要 Python 3，以检查当前自动化进程。" >&2
  exit 2
fi
python3 "$DESKTOP_ROOT/scripts/install-macos.py" --check-running
# 兼容通过 rustup 安装但尚未加入交互 shell PATH 的本机 stable 工具链。
if [[ -x "$HOME/.cargo/bin/rustc" && -x "$HOME/.cargo/bin/cargo" ]]; then
  export PATH="$HOME/.cargo/bin:$PATH"
fi
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo "请安装 Node.js 22 与 npm。" >&2
  exit 2
fi
NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
if [[ "$NODE_MAJOR" != "22" ]]; then
  echo "桌面构建锁定 Node.js 22，当前版本为 $(node --version)。" >&2
  exit 2
fi
if ! command -v rustc >/dev/null || ! command -v cargo >/dev/null; then
  echo "请安装 Rust stable 并将 cargo bin 目录加入 PATH。" >&2
  exit 2
fi
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

npm ci
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python "$DESKTOP_ROOT/scripts/build-helper.py"
bash "$DESKTOP_ROOT/scripts/build-worker.sh"
npm run test:release-config
npm run test:ui-model
npm run self-test
npm run tauri -- build --bundles app

# 将可交付的应用副本放到稳定目录，避免清理 Cargo target 时丢失。
APP_SOURCE="$DESKTOP_ROOT/src-tauri/target/release/bundle/macos/向僵尸开炮日常助手.app"
APP_RELEASE_DIR="$DESKTOP_ROOT/release"
mkdir -p "$APP_RELEASE_DIR"
ditto "$APP_SOURCE" "$APP_RELEASE_DIR/向僵尸开炮日常助手.app"
bash "$DESKTOP_ROOT/scripts/sign-macos.sh" "$APP_RELEASE_DIR/向僵尸开炮日常助手.app"
echo "构建完成：$APP_RELEASE_DIR/向僵尸开炮日常助手.app"
