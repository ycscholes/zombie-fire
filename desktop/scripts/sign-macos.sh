#!/usr/bin/env bash
set -euo pipefail

DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DESKTOP_ROOT/scripts/macos-signing-common.sh"
APP_PATH="${1:-$DESKTOP_ROOT/release/向僵尸开炮日常助手.app}"
APP_IDENTIFIER="app.codex.zombiefire.daily"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS 应用只能在 macOS 上签名。" >&2
  exit 2
fi
if [[ ! -d "$APP_PATH/Contents" ]]; then
  echo "找不到 .app 包：$APP_PATH" >&2
  exit 2
fi

# 先确认固定身份，再按 helper、worker、app 的封装顺序签名并验证。
SIGNING_IDENTITY="$(require_signing_identity)"
HELPER="$APP_PATH/Contents/Resources/resources/bin/zombie_cgclick"
if [[ ! -f "$HELPER" ]]; then
  echo "应用包缺少 macOS 输入 helper：$HELPER" >&2
  exit 2
fi

WORKER_COUNT=0
for WORKER in "$APP_PATH/Contents/MacOS"/zombie-fire-worker*; do
  [[ -f "$WORKER" ]] || continue
  /usr/bin/codesign --force --sign "$SIGNING_IDENTITY" --identifier "$APP_IDENTIFIER.worker" "$WORKER"
  /usr/bin/codesign --verify --strict --verbose=2 "$WORKER"
  designated_requirement "$WORKER" >/dev/null
  WORKER_COUNT=$((WORKER_COUNT + 1))
done
if [[ "$WORKER_COUNT" -eq 0 ]]; then
  echo "应用包缺少 zombie-fire-worker sidecar。" >&2
  exit 2
fi

/usr/bin/codesign --force --sign "$SIGNING_IDENTITY" --identifier "$APP_IDENTIFIER.helper" "$HELPER"
/usr/bin/codesign --verify --strict --verbose=2 "$HELPER"
designated_requirement "$HELPER" >/dev/null
/usr/bin/codesign --force --sign "$SIGNING_IDENTITY" --identifier "$APP_IDENTIFIER" "$APP_PATH"
/usr/bin/codesign --verify --deep --strict --verbose=2 "$APP_PATH"
designated_requirement "$APP_PATH" >/dev/null
echo "稳定本地签名及 strict 验证完成：$APP_PATH"
