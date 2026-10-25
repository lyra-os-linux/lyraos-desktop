#!/bin/bash
# Check that a PackageKit offline update coexists with lyra-upgrade-offline
# (UPD-01, lyraos-desktop-updater#22) on the installed test VM, and stream the
# report to the host through the QEMU virtio port (org.lyraos.UpgradeEvidence,
# written by kiwi/test/build-and-run-vm.sh to vm/upgrade-guest-evidence.jsonl).
#
# Usage (as root, inside the installed VM):
#   packagekit-gate.sh prepare --reboot   install fixture v1, stage v2 offline, reboot
#   packagekit-gate.sh verify             after PackageKit applied v2 and rebooted
#
# The fixture is an inert noarch RPM (lyra-offline-fixture, versions 1 and 2)
# served by the host next to this script. Its plaindir repository has gpgcheck
# disabled; that applies only to this disposable repository in the test VM,
# and verify removes both the repository and the package.
set -euo pipefail

PORT="${LYRA_EVIDENCE_PORT:-/dev/virtio-ports/org.lyraos.UpgradeEvidence}"
BASE_URL="${LYRA_GATE_URL:-http://10.0.2.2:8765}"
WORK_DIR="${LYRA_PACKAGEKIT_GATE_DIR:-/var/tmp/lyra-packagekit-gate}"
REPO_FILE=/etc/zypp/repos.d/lyra-pk-fixture.repo
FIXTURE=lyra-offline-fixture
UNIT=lyra-upgrade-offline.service
LYRA_OPERATIONS=/var/lib/lyra-upgrade/operations
PK_RESULT=/var/lib/PackageKit/offline-update-competed
REBOOT=0
PHASE=""

for argument in "$@"; do
  case "$argument" in
    prepare|verify) PHASE="$argument" ;;
    --reboot) REBOOT=1 ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done
if [ -z "$PHASE" ]; then
  echo "usage: packagekit-gate.sh <prepare|verify> [--reboot]" >&2
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
for tool in pkcon rpm zypper journalctl curl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is missing" >&2; exit 1; }
done
if [ ! -x /usr/libexec/lyra-upgrade-offline ]; then
  echo "lyra-upgrade-offline is not installed; this is not a Lyra OS installed system" >&2
  exit 1
fi

mkdir -p "$WORK_DIR/repo"
REPORT="$WORK_DIR/$PHASE.txt"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAILURES=0
: > "$REPORT"

note() { echo "$*" | tee -a "$REPORT"; }
check() {
  local name="$1"; shift
  if "$@" >>"$REPORT" 2>&1; then
    note "check $name: ok"
  else
    note "check $name: FAILED"
    FAILURES=$((FAILURES + 1))
  fi
}
operations_state() { [ -e "$LYRA_OPERATIONS" ] && echo present || echo absent; }

prepare() {
  note "lyra-upgrade: $(rpm -q lyra-upgrade)"
  note "PackageKit: $(rpm -q PackageKit)"
  note "lyra-operations-before: $(operations_state)"
  operations_state > "$WORK_DIR/operations-before"
  if [ -e /system-update ] || [ -L /system-update ]; then
    note "check no-pending-request: FAILED (/system-update already exists)"
    return 1
  fi
  for version in 1 2; do
    curl -fsSL "$BASE_URL/$FIXTURE-$version-1.noarch.rpm" -o "$WORK_DIR/repo/$FIXTURE-$version-1.noarch.rpm"
  done
  rpm -q "$FIXTURE" >/dev/null 2>&1 && rpm -e "$FIXTURE"
  check install-v1 rpm -i "$WORK_DIR/repo/$FIXTURE-1-1.noarch.rpm"
  # Only v2 stays in the repository, so PackageKit sees exactly one update.
  rm -f "$WORK_DIR/repo/$FIXTURE-1-1.noarch.rpm"
  printf '[lyra-pk-fixture]\nname=Disposable PackageKit gate fixture\nbaseurl=dir:%s/repo\ntype=plaindir\nenabled=1\nautorefresh=0\ngpgcheck=0\n' \
    "$WORK_DIR" > "$REPO_FILE"
  check zypper-refresh zypper --non-interactive refresh lyra-pk-fixture
  check pkcon-refresh pkcon refresh force
  check pkcon-download pkcon --noninteractive --allow-untrusted --only-download update "$FIXTURE"
  check pkcon-offline-trigger pkcon offline-trigger
  note "system-update: $(readlink /system-update || echo missing)"
  check marker-owned-by-packagekit bash -c 'readlink /system-update | grep -q PackageKit'
}

verify() {
  local boot_offline
  note "lyra-upgrade: $(rpm -q lyra-upgrade)"
  # PackageKit reboots once after applying the update, so the offline boot is
  # the previous one in the persistent journal.
  boot_offline="$(journalctl --list-boots --no-pager -q | tail -n 2 | head -n 1 | awk '{print $2}')"
  note "offline-boot: $boot_offline"
  journalctl -b "$boot_offline" -u "$UNIT" --no-pager -o short-iso > "$WORK_DIR/unit.log" 2>&1 || true
  cat "$WORK_DIR/unit.log" >> "$REPORT"
  check unit-ran grep -q 'Starting.*Apply a staged Lyra OS release upgrade\|Starting lyra-upgrade-offline' "$WORK_DIR/unit.log"
  check unit-not-failed bash -c "! grep -qiE 'Failed|status=[1-9]|No such file' '$WORK_DIR/unit.log'"
  check packagekit-result-exists test -f "$PK_RESULT"
  [ -f "$PK_RESULT" ] && cat "$PK_RESULT" >> "$REPORT"
  check packagekit-success grep -q '^Success=true' "$PK_RESULT"
  note "fixture: $(rpm -q --qf '%{VERSION}' "$FIXTURE" 2>&1)"
  check fixture-updated-to-v2 test "$(rpm -q --qf '%{VERSION}' "$FIXTURE")" = 2
  check marker-removed bash -c '! [ -e /system-update ] && ! [ -L /system-update ]'
  note "lyra-operations-after: $(operations_state)"
  check lyra-state-untouched test "$(operations_state)" = "$(cat "$WORK_DIR/operations-before" 2>/dev/null)"
  check no-failed-units bash -c '[ -z "$(systemctl --failed --no-legend --plain)" ]'
  rm -f "$REPO_FILE"
  rpm -e "$FIXTURE" >/dev/null 2>&1 || true
  note "cleanup: fixture repository and package removed"
}

STATUS=0
case "$PHASE" in
  prepare) prepare || STATUS=$? ;;
  verify) verify || STATUS=$? ;;
esac
[ "$FAILURES" -eq 0 ] || STATUS=1
note "result: $([ "$STATUS" -eq 0 ] && echo passed || echo failed)"

{
  echo "### BEGIN packagekit-gate $PHASE $STAMP host=$(uname -n) kernel=$(uname -r)"
  cat "$REPORT"
  echo "### END packagekit-gate $PHASE exit=$STATUS"
} > "$PORT"

if [ "$REBOOT" -eq 1 ] && [ "$STATUS" -eq 0 ]; then
  echo "--- rebooting into the PackageKit offline update ---"
  systemctl reboot
elif [ "$REBOOT" -eq 1 ]; then
  echo "--- phase failed; not rebooting ---" >&2
fi
exit "$STATUS"
