#!/usr/bin/env bash
set -euo pipefail

DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DESKTOP_ROOT/scripts/macos-signing-common.sh"

# 比较升级前后的 app、worker 与输入 helper 身份；DR 必须由稳定证书而非 cdhash 绑定。
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "designated requirement 只能在 macOS 上读取。" >&2
  exit 2
fi
if [[ "$#" -ne 2 ]]; then
  echo "用法：$0 <旧版.app> <新版.app>" >&2
  exit 2
fi
OLD_APP="$1"
NEW_APP="$2"
for APP in "$OLD_APP" "$NEW_APP"; do
  if [[ ! -d "$APP/Contents" ]]; then
    echo "找不到 .app 包：$APP" >&2
    exit 2
  fi
  /usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
done

compare_component() {
  local label="$1" old_path="$2" new_path="$3" old_requirement new_requirement
  old_requirement="$(designated_requirement "$old_path")"
  new_requirement="$(designated_requirement "$new_path")"
  if [[ "$old_requirement" != "$new_requirement" ]]; then
    echo "签名身份发生变化：$label" >&2
    echo "旧版 DR：$old_requirement" >&2
    echo "新版 DR：$new_requirement" >&2
    return 1
  fi
  echo "DR 一致：$label"
}

compare_component app "$OLD_APP" "$NEW_APP"

OLD_WORKER_DIR="$OLD_APP/Contents/MacOS"
NEW_WORKER_DIR="$NEW_APP/Contents/MacOS"
WORKER_COUNT=0
for NEW_WORKER in "$NEW_WORKER_DIR"/zombie-fire-worker*; do
  [[ -f "$NEW_WORKER" ]] || continue
  WORKER_NAME="${NEW_WORKER##*/}"
  OLD_WORKER="$OLD_WORKER_DIR/$WORKER_NAME"
  if [[ ! -f "$OLD_WORKER" ]]; then
    echo "旧版缺少 worker：$WORKER_NAME" >&2
    exit 1
  fi
  compare_component "worker/$WORKER_NAME" "$OLD_WORKER" "$NEW_WORKER"
  WORKER_COUNT=$((WORKER_COUNT + 1))
done
if [[ "$WORKER_COUNT" -eq 0 ]]; then
  echo "新版 .app 缺少 zombie-fire-worker sidecar。" >&2
  exit 1
fi

OLD_HELPER="$OLD_APP/Contents/Resources/resources/bin/zombie_cgclick"
NEW_HELPER="$NEW_APP/Contents/Resources/resources/bin/zombie_cgclick"
if [[ ! -f "$OLD_HELPER" || ! -f "$NEW_HELPER" ]]; then
  echo "旧版或新版 .app 缺少 zombie_cgclick helper。" >&2
  exit 1
fi
compare_component helper "$OLD_HELPER" "$NEW_HELPER"
