#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_PLIST="$REPO_DIR/automation/com.local.ipotracker.plist"
TARGET_PLIST="$HOME/Library/LaunchAgents/com.local.ipotracker.plist"

UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" ]]; then
	echo "uv is not installed or not in PATH. Install uv first."
	exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

sed -e "s|__REPO_PATH__|$REPO_DIR|g" -e "s|__UV_BIN__|$UV_BIN|g" "$SOURCE_PLIST" > "$TARGET_PLIST"

launchctl unload "$TARGET_PLIST" 2>/dev/null || true
launchctl load "$TARGET_PLIST"

echo "Installed launch agent: $TARGET_PLIST"
echo "Using uv: $UV_BIN"
echo "It will run at login and every 6 hours when your laptop is on."
