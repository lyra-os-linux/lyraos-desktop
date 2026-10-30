#!/usr/bin/env bash
# Build and qualify the signed Lyra OS Desktop 16.1 RC 3 publication bundle.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
export LYRA_EXPECTED_VERSION="16.1-rc.3"
export LYRA_RELEASE_LABEL="Desktop RC 3"
export LYRA_COMMAND_NAME="$0"
exec "$SCRIPT_DIR/build-desktop-alpha6.sh" "$@"
