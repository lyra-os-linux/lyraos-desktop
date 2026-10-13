#!/bin/bash
# Run one phase of the Lyra update/rollback exercise inside the installed test
# VM and stream its JSON report to the host through the QEMU virtio port
# (org.lyraos.UpgradeEvidence, written by kiwi/test/build-and-run-vm.sh to
# vm/upgrade-guest-evidence.jsonl). The host then assembles the gate evidence
# with kiwi/test/rollback-evidence.py.
#
# Usage (as root, inside the installed VM):
#   rollback-gate.sh baseline
#   rollback-gate.sh update --reboot
#   rollback-gate.sh verify-updated
#   rollback-gate.sh prepare-rollback --reboot
#   rollback-gate.sh verify-rollback
#
# Phases are the ones of lyra-update-smoke; the workflow state stays on the
# ESP (/boot/efi/EFI/Lyra/update-smoke-state.json) so it survives the
# rollback. --reboot reboots after the report has been streamed; it is only
# meaningful after update and prepare-rollback.
set -euo pipefail

PORT="${LYRA_EVIDENCE_PORT:-/dev/virtio-ports/org.lyraos.UpgradeEvidence}"
WORK_DIR="${LYRA_ROLLBACK_GATE_DIR:-/var/tmp/lyra-rollback-gate}"
REBOOT=0
PHASE=""
EXTRA=()

for argument in "$@"; do
  case "$argument" in
    baseline|update|verify-updated|prepare-rollback|verify-rollback) PHASE="$argument" ;;
    --reboot) REBOOT=1 ;;
    --restart|--rollback-snapshot=*) EXTRA+=("$argument") ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done
if [ -z "$PHASE" ]; then
  echo "usage: rollback-gate.sh <baseline|update|verify-updated|prepare-rollback|verify-rollback> [--reboot] [--restart] [--rollback-snapshot=N]" >&2
  exit 2
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "run as root inside the installed VM (sudo)" >&2
  exit 1
fi
if [ ! -c "$PORT" ] || [ ! -w "$PORT" ]; then
  echo "evidence port is unavailable: $PORT (is this the QEMU test VM?)" >&2
  exit 1
fi
if ! command -v lyra-update-smoke >/dev/null 2>&1; then
  echo "lyra-update-smoke is not installed; this is not a Lyra OS installed system" >&2
  exit 1
fi

mkdir -p "$WORK_DIR"
REPORT="$WORK_DIR/$PHASE.json"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATUS=0
lyra-update-smoke "$PHASE" --output "$REPORT" "${EXTRA[@]}" || STATUS=$?

{
  echo "### BEGIN rollback-gate $PHASE $STAMP host=$(hostname) kernel=$(uname -r)"
  cat "$REPORT"
  echo "### END rollback-gate $PHASE exit=$STATUS"
} | tee -a "$PORT"

if [ "$REBOOT" -eq 1 ] && [ "$STATUS" -eq 0 ]; then
  echo "--- rebooting for the next phase ---"
  systemctl reboot
elif [ "$REBOOT" -eq 1 ]; then
  echo "--- phase failed; not rebooting ---" >&2
fi
exit "$STATUS"
