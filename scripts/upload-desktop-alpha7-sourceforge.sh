#!/usr/bin/env bash
# Compatibility entry point for the GNOME Alpha 7 SourceForge uploader.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
exec "$SCRIPT_DIR/upload-gnome-alpha7-sourceforge.sh" "$@"
