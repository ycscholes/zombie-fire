#!/bin/zsh

set -euo pipefail

readonly LABEL="com.paul.zombie-fire.journey-resource-claim"
readonly DOMAIN="gui/$(id -u)"

if ! launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  print "定时任务已关闭：$LABEL"
  exit 0
fi

launchctl bootout "$DOMAIN/$LABEL"
print "已关闭定时任务：$LABEL"
