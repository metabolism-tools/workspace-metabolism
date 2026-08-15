#!/usr/bin/env bash
# Template: register workspace-metabolism cron jobs (Linux/macOS).
#
# Replace the {{PLACEHOLDERS}} before running:
#   {{WM_CMD}}     - how to invoke the tool, e.g. /usr/bin/python3 -m workspace_metabolism  (or: wm)
#   {{ROOT}}       - absolute path of the workspace to govern
#   {{REGISTRY}}   - absolute path of the policy registry (JSON)
#   {{STATE_DIR}}  - absolute path of the state directory
#   {{USER}}       - unprivileged user to run the jobs (do NOT use root)
#
# Usage:
#   sudo bash register_cron.template.sh
#   sudo bash register_cron.template.sh unregister
set -euo pipefail

WM="{{WM_CMD}}"
ROOT="{{ROOT}}"
REG="{{REGISTRY}}"
STATE="{{STATE_DIR}}"
USER_NAME="{{USER}}"
LOG="$STATE/cron.log"

if [ "${1:-}" = "unregister" ]; then
    crontab -u "$USER_NAME" -l 2>/dev/null | grep -v "workspace_metabolism" | crontab -u "$USER_NAME" - || true
    echo "cron jobs unregistered."
    exit 0
fi

mkdir -p "$STATE"

AUDIT_LINE="30 20 * * * cd $ROOT && $WM audit --auto --registry $REG --state-dir $STATE >> $LOG 2>&1"
CLEAN_LINE="0 10 * * 6 cd $ROOT && $WM clean --grades G4 --yes --auto --registry $REG --state-dir $STATE >> $LOG 2>&1"
PURGE_LINE="0 10 1 * * cd $ROOT && $WM purge --older-than 30 --yes --auto --state-dir $STATE >> $LOG 2>&1"

TMP="$(mktemp)"
crontab -u "$USER_NAME" -l 2>/dev/null | grep -v "workspace_metabolism" > "$TMP" || true
printf '%s\n%s\n%s\n' "$AUDIT_LINE" "$CLEAN_LINE" "$PURGE_LINE" >> "$TMP"
crontab -u "$USER_NAME" "$TMP"
rm -f "$TMP"

echo "cron jobs registered for user $USER_NAME:"
crontab -u "$USER_NAME" -l | grep "workspace_metabolism"
