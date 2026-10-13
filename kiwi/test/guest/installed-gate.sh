#!/bin/bash
# Collect the first-boot and UEFI Secure Boot evidence of an installed Lyra OS
# inside the QEMU test VM and stream it to the host through the virtio port
# org.lyraos.UpgradeEvidence (vm/upgrade-guest-evidence.jsonl on the host).
# The host assembles the gate files with kiwi/test/gate-evidence.py.
#
# Usage (as the installed account; sudo asks for its password once):
#   installed-gate.sh all                       first-boot, uefi-secure-boot, journal-crit, packages, palette, locale, users
#   installed-gate.sh first-boot                only lyra-system-smoke first-boot
#   installed-gate.sh <section> ...             any of the sections, in order
# Options:
#   --acknowledge-journal=ISSUE                 passed to lyra-system-smoke first-boot
set -uo pipefail

PORT="${LYRA_EVIDENCE_PORT:-/dev/virtio-ports/org.lyraos.UpgradeEvidence}"
WORK_DIR="${LYRA_GATE_DIR:-/var/tmp/lyra-installed-gate}"
ACK=""
SECTIONS=()
for argument in "$@"; do
  case "$argument" in
    --acknowledge-journal=*) ACK="${argument#*=}" ;;
    all) SECTIONS+=(first-boot uefi-secure-boot journal-crit packages palette locale users) ;;
    first-boot|uefi-secure-boot|journal-crit|packages|palette|locale|users) SECTIONS+=("$argument") ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done
if [ "${#SECTIONS[@]}" -eq 0 ]; then
  echo "usage: installed-gate.sh all|first-boot|uefi-secure-boot|journal-crit|packages|palette|locale|users [--acknowledge-journal=ISSUE]" >&2
  exit 2
fi
if [ ! -c "$PORT" ]; then
  echo "evidence port is unavailable: $PORT (is this the QEMU test VM?)" >&2
  exit 1
fi
# lyra-system-smoke first-boot uses the cached sudo credential for read-only
# privileged access; cache it once up front so no check fails on a prompt.
sudo -v || exit 1
mkdir -p "$WORK_DIR"

stream() {
  local section="$1"; shift
  local stamp status
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    echo "### BEGIN installed-gate $section $stamp user=$(id -un) kernel=$(uname -r) boot=$(cat /proc/sys/kernel/random/boot_id)"
    "$@" 2>&1
    status=$?
    echo "### END installed-gate $section exit=$status"
    echo "$status" > "$WORK_DIR/.last-exit"
  } | sudo tee -a "$PORT"
  return "$(cat "$WORK_DIR/.last-exit")"
}

first_boot() {
  local args=(first-boot --output "$WORK_DIR/first-boot-result.json")
  [ -n "$ACK" ] && args+=(--acknowledge-journal "$ACK")
  lyra-system-smoke "${args[@]}" >/dev/null; local status=$?
  cat "$WORK_DIR/first-boot-result.json"
  return "$status"
}
secure_boot() {
  lyra-system-smoke secure-boot --output "$WORK_DIR/uefi-secure-boot-result.json" >/dev/null; local status=$?
  cat "$WORK_DIR/uefi-secure-boot-result.json"
  return "$status"
}
journal_crit() { sudo journalctl -b -p 3 --no-pager 2>&1; }
packages() {
  echo "## must be absent on the installed system"; rpm -q lyra-installer 2>&1
  echo "## lyra packages"; rpm -q lyra-release sheliak lyra-upgrade lyra-vms lyra-welcome 2>&1
  echo "## snapper"; sudo snapper --no-dbus list 2>&1 | tail -5
}
palette() {
  ls -la "$HOME/.config/lyra-native-colors.default-applied" "$HOME/.config/gtk-4.0" 2>&1
  gsettings get org.gnome.desktop.interface gtk-theme 2>&1
  gsettings get org.gnome.desktop.interface color-scheme 2>&1
  gsettings get org.gnome.shell.extensions.user-theme name 2>&1
  gnome-extensions list --enabled 2>&1
}
locale_info() { localectl status 2>&1; cat /etc/locale.conf 2>&1; }
users() { getent passwd | awk -F: '$3 >= 1000 && $3 < 65534'; echo "## liveuser must be absent"; getent passwd liveuser || echo "liveuser absent"; }

FINAL=0
for section in "${SECTIONS[@]}"; do
  case "$section" in
    first-boot) stream first-boot first_boot || FINAL=1 ;;
    uefi-secure-boot) stream uefi-secure-boot secure_boot || FINAL=1 ;;
    journal-crit) stream journal-crit journal_crit || FINAL=1 ;;
    packages) stream packages packages || FINAL=1 ;;
    palette) stream palette palette || FINAL=1 ;;
    locale) stream locale locale_info || FINAL=1 ;;
    users) stream users users || FINAL=1 ;;
  esac
done
exit "$FINAL"
