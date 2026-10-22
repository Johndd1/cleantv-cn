#!/usr/bin/env bash
# Recorded installation. Never disables system apps or uninstalls an existing launcher.
# TV=<ip> APK_FILE=/absolute/path/app.apk bash tools/install.sh --preview
# TV=<ip> APK_FILE=/absolute/path/app.apk bash tools/install.sh --launcher-only
# TV=<ip> APK_FILE=/absolute/path/app.apk bash tools/install.sh [guard]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLAVOR=standard
if [ "${1:-}" = guard ] || [ "${1:-}" = standard ]; then FLAVOR="$1"; shift; fi
if [ "${KEEP_ADB:-0}" = 1 ]; then
  echo "KEEP_ADB=1 is not supported by this installer. It will not enable persistent debugging." >&2
  exit 2
fi
if [ "${BUILD:-0}" = 1 ] && [ -z "${APK_FILE:-}" ]; then
  case "$FLAVOR" in standard) TASK=assembleStandardRelease ;; guard) TASK=assembleGuardRelease ;; esac
  (cd "$ROOT" && ./gradlew "$TASK")
  export APK_FILE="$ROOT/app/build/outputs/apk/$FLAVOR/release/app-$FLAVOR-release.apk"
fi
exec python3 "$ROOT/tools/device.py" install --flavor "$FLAVOR" "$@"
