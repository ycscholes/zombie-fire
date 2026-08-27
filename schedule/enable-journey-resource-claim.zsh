#!/bin/zsh

set -euo pipefail

readonly LABEL="com.paul.zombie-fire.journey-resource-claim"
readonly PLIST="/Users/paul/Library/LaunchAgents/com.paul.zombie-fire.journey-resource-claim.plist"
readonly DOMAIN="gui/$(id -u)"

if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  print "定时任务已开启：$LABEL"
  exit 0
fi

launchctl bootstrap "$DOMAIN" "$PLIST"
print "已开启定时任务：$LABEL"
print "任务仍按原计划每 6 小时执行；本脚本不会立即执行任务。"
