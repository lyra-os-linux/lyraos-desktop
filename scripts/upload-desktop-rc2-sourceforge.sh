#!/usr/bin/env bash
# Validate and publish the signed Desktop 16.1 RC 2 bundle to SourceForge.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export LYRA_EXPECTED_VERSION="16.1-rc.2"
export LYRA_RELEASE_LABEL="Desktop RC 2"
export LYRA_RELEASE_SLUG="rc2"
export LYRA_RELEASE_LAYOUT="${LYRA_RELEASE_LAYOUT:-release-first}"
export LYRA_COMMAND_NAME="$0"
exec "$SCRIPT_DIR/upload-desktop-alpha6-sourceforge.sh" "$@"
