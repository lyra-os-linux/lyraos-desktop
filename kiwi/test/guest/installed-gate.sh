#!/bin/bash
# Collect the first-boot and UEFI Secure Boot evidence of an installed Lyra OS
# inside the QEMU test VM and stream it to the host through the virtio port
# org.lyraos.UpgradeEvidence (vm/upgrade-guest-evidence.jsonl on the host).
# The host assembles the gate files with kiwi/test/gate-evidence.py.
#
# Usage (as the installed account; sudo asks for its password once):
#   installed-gate.sh all                       first-boot, uefi-secure-boot, journal-crit, packages, palette, locale, users, sudo-policy, parental
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
    all) SECTIONS+=(first-boot uefi-secure-boot journal-crit packages palette locale users sudo-policy parental) ;;
    first-boot|uefi-secure-boot|journal-crit|packages|palette|locale|users|sudo-policy|parental) SECTIONS+=("$argument") ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done
if [ "${#SECTIONS[@]}" -eq 0 ]; then
  echo "usage: installed-gate.sh all|first-boot|uefi-secure-boot|journal-crit|packages|palette|locale|users|sudo-policy|parental [--acknowledge-journal=ISSUE]" >&2
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
# Only wheel may sudo with its own password. A temporary account outside
# wheel tries sudo with its own password and must be refused.
sudo_policy() {
  local probe=lyra-gate-sudo-probe password status=0
  echo "## policy"; rpm -q sudo-policy-wheel-auth-self || status=1
  echo "## global !targetpw (must be absent)"
  sudo grep -rsnE '^Defaults[[:space:]]+!targetpw' /etc/sudoers /etc/sudoers.d /usr/etc/sudoers /usr/etc/sudoers.d && status=1
  password="$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
  sudo useradd -M -s /bin/sh "$probe" && echo "$probe:$password" | sudo chpasswd || return 1
  echo "## account outside wheel, own password"
  if sudo -u "$probe" sh -c "printf '%s\\n' '$password' | sudo -S -k -p '' true" 2>&1; then
    echo "FAIL: $probe got root"; status=1
  else
    echo "refused"
  fi
  sudo userdel "$probe" || status=1
  return "$status"
}

# Basic parental controls (gate #9, docs/parental-controls-gate.md). A
# temporary supervised account is created through vegad, every restriction
# that can be checked without a graphical session is verified, and the
# account is removed. The graphical checks follow the manual list in the doc.
parental() {
  local child=lyra-gate-child password status=0 path filter
  local users=(busctl --system call org.lyraos.Vega1 /org/lyraos/Vega1 org.lyraos.Vega1.Users)
  fail() { echo "FAIL: $*"; status=1; }
  echo "## packages"
  rpm -q lyra-parental-controls malcontent-control sheliak vegad vega-gtk || status=1
  echo "## flatpak is not installed by default (enabled in Vega)"
  if rpm -q flatpak; then fail "flatpak installed"; else echo "absent"; fi
  password="$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
  echo "## supervised account created through vegad"
  sudo "${users[@]}" CreateUser sssasayb "$child" "Lyra Gate Child" "$password" 1 lyra-supervised 0 false || return 1
  id -nG "$child"
  id -nG "$child" | tr ' ' '\n' | grep -qx lyra-supervised || fail "not in lyra-supervised"
  echo "## malcontent hides the terminals and Vega"
  filter="$(sudo grep '^AppFilter=' "/var/lib/AccountsService/users/$child")"; echo "$filter"
  for path in /usr/bin/kgx /usr/bin/gnome-terminal /usr/bin/fish /usr/bin/vega-gtk; do
    grep -qF "'$path'" <<<"$filter" || fail "$path not hidden"
  done
  echo "## supervised account cannot become administrator"
  if sudo "${users[@]}" SetAdmin sb "$child" true 2>&1; then fail "SetAdmin accepted"; fi
  echo "## sudo with its own password is refused"
  if sudo -u "$child" sh -c "printf '%s\\n' '$password' | sudo -S -k -p '' true" 2>&1; then fail "sudo granted"; fi
  echo "## su to root is refused (root is locked)"
  if sudo -u "$child" sh -c "printf '%s\\n' '$password' | su -c true root" 2>&1; then fail "su granted"; fi
  echo "## SSH denies the group"
  sudo sshd -T 2>/dev/null | grep -Fx 'denygroups lyra-supervised' || fail "DenyGroups missing"
  echo "## TTY: /etc/pam.d/login is the vendor file plus pam_access"
  grep -c 'pam_access.so accessfile=/usr/share/lyra-parental-controls/access.conf' /etc/pam.d/login || fail "pam_access missing"
  grep -vF 'pam_access.so accessfile=/usr/share/lyra-parental-controls/access.conf' /etc/pam.d/login \
    | diff -u /usr/lib/pam.d/login - || fail "vendor login changed; refresh the copy"
  echo "## Alt+F2 locked only for the supervised account"
  [ "$(sudo -u "$child" /usr/lib/systemd/user-environment-generators/60-lyra-supervised)" = DCONF_PROFILE=lyra-supervised ] || fail "generator"
  [ -z "$(/usr/lib/systemd/user-environment-generators/60-lyra-supervised)" ] || fail "generator applies to the administrator"
  [ "$(sudo -u "$child" env DCONF_PROFILE=lyra-supervised gsettings get org.gnome.desktop.lockdown disable-command-line)" = true ] || fail "Alt+F2 not locked"
  [ "$(sudo -u "$child" env DCONF_PROFILE=lyra-supervised gsettings writable org.gnome.desktop.lockdown disable-command-line)" = false ] || fail "Alt+F2 lock writable"
  echo "## Settings can read the rules (polkit read rule)"
  test -f /usr/share/polkit-1/rules.d/52-lyra-parental-read.rules || fail "read rule missing"
  echo "## temporary account removed"
  sudo "${users[@]}" RemoveUser s "$child" || status=1
  return "$status"
}

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
    sudo-policy) stream sudo-policy sudo_policy || FINAL=1 ;;
    parental) stream parental parental || FINAL=1 ;;
  esac
done
exit "$FINAL"
