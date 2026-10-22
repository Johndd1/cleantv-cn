#!/usr/bin/env bash
# Restore this TV from its original record. No record means no guessed settings.
# TV=<ip> bash tools/restore.sh [--preview] [--uninstall]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tools/device.py" restore "$@"
