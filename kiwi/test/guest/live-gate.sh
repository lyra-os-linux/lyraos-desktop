#!/bin/bash
# Collect the live-session, firmware, repository and installer evidence of a
# Lyra OS live session inside the QEMU test VM and stream it to the host
# through the virtio port org.lyraos.UpgradeEvidence (written by
# kiwi/test/build-and-run-vm.sh to vm/upgrade-guest-evidence.jsonl). The host
# assembles the gate files with kiwi/test/gate-evidence.py.
#
# Usage (as liveuser in the live session; sudo is passwordless there):
#   live-gate.sh all                 live-session online+offline, firmware, repositories, identity, journal
#   live-gate.sh live-session        only the online lyra-live-smoke run
#   live-gate.sh installer           after the Lyra Installer finished: its result JSON, logs and lsblk
#   live-gate.sh <section> ...       any of the sections below, in order
# Options:
#   --acknowledge-journal=ISSUE      passed to lyra-live-smoke for reviewed journal entries
#   --skip-offline                   do not toggle networking off for the offline run
set -uo pipefail

PORT="${LYRA_EVIDENCE_PORT:-/dev/virtio-ports/org.lyraos.UpgradeEvidence}"
WORK_DIR="${LYRA_GATE_DIR:-/tmp/lyra-live-gate}"
ACK=""
SKIP_OFFLINE=0
SECTIONS=()
for argument in "$@"; do
  case "$argument" in
    --acknowledge-journal=*) ACK="${argument#*=}" ;;
    --skip-offline) SKIP_OFFLINE=1 ;;
    all) SECTIONS+=(live-session live-session-offline firmware repositories identity journal-crit) ;;
    live-session|live-session-offline|firmware|repositories|identity|journal-crit|installer) SECTIONS+=("$argument") ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done
if [ "${#SECTIONS[@]}" -eq 0 ]; then
  echo "usage: live-gate.sh all|live-session|live-session-offline|firmware|repositories|identity|journal-crit|installer [--acknowledge-journal=ISSUE] [--skip-offline]" >&2
  exit 2
fi
if [ ! -c "$PORT" ]; then
  echo "evidence port is unavailable: $PORT (is this the QEMU test VM?)" >&2
  exit 1
fi
mkdir -p "$WORK_DIR"

stream() {
  # stream SECTION COMMAND... : run the command, stream stdout+stderr between markers
  local section="$1"; shift
  local stamp status
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    echo "### BEGIN live-gate $section $stamp user=$(id -un) kernel=$(uname -r)"
    "$@" 2>&1
    status=$?
    echo "### END live-gate $section exit=$status"
    echo "$status" > "$WORK_DIR/.last-exit"
  } | sudo tee -a "$PORT"
  return "$(cat "$WORK_DIR/.last-exit")"
}

smoke_online() {
  local args=(--output "$WORK_DIR/live-session-result.json")
  [ -n "$ACK" ] && args+=(--acknowledge-journal "$ACK")
  lyra-live-smoke "${args[@]}" >/dev/null; local status=$?
  cat "$WORK_DIR/live-session-result.json"
  return "$status"
}
smoke_offline() {
  if [ "$SKIP_OFFLINE" -eq 1 ]; then echo '{"skipped": "offline run disabled by --skip-offline"}'; return 0; fi
  sudo nmcli networking off; sleep 3
  local args=(--expect-offline --output "$WORK_DIR/live-session-offline-result.json")
  [ -n "$ACK" ] && args+=(--acknowledge-journal "$ACK")
  lyra-live-smoke "${args[@]}" >/dev/null; local status=$?
  sudo nmcli networking on
  cat "$WORK_DIR/live-session-offline-result.json"
  return "$status"
}
firmware() {
  echo "## mokutil"; mokutil --sb-state 2>&1
  echo "## efi"; ls /sys/firmware/efi 2>&1 | head -3
  echo "## cmdline"; cat /proc/cmdline
}
repositories() {
  echo "## zypper lr -u"; zypper --non-interactive lr -u 2>&1
  echo "## lyra packages"; rpm -q lyra-release lyra-installer sheliak lyra-upgrade lyra-vms lyra-welcome 2>&1
}
identity() { cat /etc/os-release; echo "## lyra release"; cat /usr/lib/lyra-os/release 2>&1; }
journal_crit() { journalctl -b -p 3 --no-pager 2>&1; }
installer() {
  local result="$HOME/lyra-installer-result.json"
  echo "## home"; ls -l "$HOME"/lyra-installer-* 2>&1
  echo "## installer-result"
  if [ -s "$result" ]; then cat "$result"; else echo "MISSING: $result"; return 1; fi
  echo "## installer-logs"; sudo ls -la /var/log/lyra-installer* /run/lyra-installer 2>&1
  echo "## lsblk"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS 2>&1
}

FINAL=0
for section in "${SECTIONS[@]}"; do
  case "$section" in
    live-session) stream live-session smoke_online || FINAL=1 ;;
    live-session-offline) stream live-session-offline smoke_offline || FINAL=1 ;;
    firmware) stream firmware firmware || FINAL=1 ;;
    repositories) stream repositories repositories || FINAL=1 ;;
    identity) stream identity identity || FINAL=1 ;;
    journal-crit) stream journal-crit journal_crit || FINAL=1 ;;
    installer) stream installer installer || FINAL=1 ;;
  esac
done
exit "$FINAL"
