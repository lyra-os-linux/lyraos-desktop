#!/bin/bash
# SHELL-01 live-session regression, run as root inside a disposable Lyra VM.
# The host (shell01-vm.py) serves this directory over HTTP at $LYRA_HOST and
# reads every line written to the virtio port org.lyraos.UpgradeEvidence.
#
#   shell01-guest.sh baseline   SUSE shell: identity, audio, deterministic test
#   shell01-guest.sh plan       dry-run the exact PackageMigration zypper selection
#   shell01-guest.sh install    verify and install the staging RPMs, restart GDM
#   shell01-guest.sh audio      current sinks/cards/default and a tone
#   shell01-guest.sh watch N    log shell PID/cards every second for N seconds
#   shell01-guest.sh verify     patched shell: identity, audio, deterministic test
set -uo pipefail

HOST=${LYRA_HOST:-http://10.0.2.2:8765}
PORT=/dev/virtio-ports/org.lyraos.UpgradeEvidence
WORK=/var/tmp/shell01
mkdir -p "$WORK"

emit() { # emit <key> <value...>: one JSON line per observation
	python3 -c 'import json,sys; print(json.dumps({"phase": sys.argv[1], "key": sys.argv[2], "value": sys.argv[3]}))' \
		"$PHASE" "$1" "${*:2}" | tee -a "$PORT" "$WORK/evidence.jsonl" >/dev/null
}

user=$(loginctl list-sessions --no-legend | awk '$3 != "gdm" && $3 != "" {print $3; exit}')
uid=$(id -u "$user" 2>/dev/null)
as_user() {
	runuser -u "$user" -- env XDG_RUNTIME_DIR=/run/user/$uid \
		DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus "$@"
}
shell_pid() { pgrep -u "$user" -x gnome-shell | head -1; }

fetch() { curl -sf -o "$WORK/$1" "$HOST/$1"; }

identity() {
	emit rpm "$(rpm -q --qf '%{NAME}-%{VERSION}-%{RELEASE} %{VENDOR}\n' gnome-shell gnome-shell-lang gnome-extensions gnome-shell-calendar 2>&1)"
	emit libgvc_sha256 "$(sha256sum /usr/lib64/gnome-shell/libgvc.so | cut -d' ' -f1)"
	pid=$(shell_pid)
	emit shell_pid "$pid"
	emit shell_libgvc_mapped "$(grep -c 'gnome-shell/libgvc.so' /proc/$pid/maps 2>/dev/null) $(grep -m1 'gnome-shell/libgvc.so' /proc/$pid/maps | awk '{print $6, $7}')"
	emit session "$(loginctl show-session "$(loginctl list-sessions --no-legend | awk -v u="$user" '$3 == u {print $1; exit}')" -p Type -p State -p Active 2>&1 | tr '\n' ' ')"
}

audio() {
	emit pactl_info "$(as_user pactl info 2>&1 | grep -E 'Server Name|Default Sink|Default Source' | tr '\n' ';')"
	emit cards "$(as_user pactl list cards short 2>&1 | tr '\n' ';')"
	emit sinks "$(as_user pactl list sinks short 2>&1 | tr '\n' ';')"
	python3 -c 'import math,struct,wave
w=wave.open("/var/tmp/shell01/tone.wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
w.writeframes(b"".join(struct.pack("<h", int(8000*math.sin(2*math.pi*440*i/48000))) for i in range(48000)))'
	chmod 644 "$WORK/tone.wav"
	emit play "$(as_user timeout 10 pw-play "$WORK/tone.wav" 2>&1; echo "exit=$?")"
	emit volume_set "$(as_user pactl set-sink-volume @DEFAULT_SINK@ 40% 2>&1; as_user pactl get-sink-volume @DEFAULT_SINK@ 2>&1 | head -1)"
}

deterministic() { # expected: 139 with the SUSE libgvc, 0 + SURVIVED when fixed
	fetch zero-profile-card.so && fetch gvc-test.js || { emit deterministic "fetch failed"; return; }
	out=$(as_user env GI_TYPELIB_PATH=/usr/lib64/gnome-shell LD_LIBRARY_PATH=/usr/lib64/gnome-shell \
		LD_PRELOAD=$WORK/zero-profile-card.so \
		timeout 20 gjs "$WORK/gvc-test.js" 2>&1)
	rc=$?
	emit deterministic "exit=$rc $(echo "$out" | tr '\n' ';')"
}

crashes() {
	emit coredumps "$(coredumpctl list --no-legend --no-pager 2>&1 | grep -E 'gnome-shell|gjs' | tr '\n' ';')"
	emit shell_journal_errors "$(journalctl -b --no-pager -q -t gnome-shell -p err 2>&1 | tail -20 | tr '\n' ';')"
}

PHASE=${1:?phase}
case "$PHASE" in
baseline | verify)
	identity
	audio
	deterministic
	crashes
	emit done ok
	;;
install)
	fetch SHA256SUMS || { emit install "SHA256SUMS fetch failed"; exit 1; }
	set -- $(awk '{print $2}' "$WORK/SHA256SUMS")
	for f in "$@"; do fetch "$f" || { emit install "fetch $f failed"; exit 1; }; done
	(cd "$WORK" && sha256sum -c SHA256SUMS) >"$WORK/sums.log" 2>&1
	emit sha256 "$(tr '\n' ';' <"$WORK/sums.log")"
	grep -q FAILED "$WORK/sums.log" && { emit install "hash mismatch"; exit 1; }
	# Only the subpackages the image already has; exact files, no repository.
	rpms=()
	for name in gnome-shell gnome-shell-lang gnome-extensions gnome-shell-calendar gnome-shell-devel; do
		rpm -q "$name" >/dev/null 2>&1 && rpms+=("$WORK/$(ls "$WORK" | grep -E "^$name-48\.8-.*\.rpm$")")
	done
	emit install_plan "${rpms[*]##*/}"
	emit rpm_signature "$(rpm -K "${rpms[@]}" 2>&1 | tr '\n' ';')"
	out=$(rpm -Uvh "${rpms[@]}" 2>&1); rc=$?
	emit install "$(echo "$out" | tail -8 | tr '\n' ';') exit=$rc"
	out=$(rpm -V gnome-shell 2>&1); rc=$?
	emit rpm_verify "$(echo "$out" | tr '\n' ';') exit=$rc"
	emit restart "systemctl restart display-manager"
	systemctl restart display-manager
	;;
audio)
	audio
	emit shell_pid "$(shell_pid)"
	emit done ok
	;;
plan)
	# The exact selection PackageMigration uses, as a dry run: the solver must
	# change only the installed gnome-shell subpackages and nothing else.
	alias=lyra-shell-staging
	zypper -q removerepo "$alias" >/dev/null 2>&1
	emit addrepo "$(zypper -n addrepo -p 99 -n "$alias" https://download.opensuse.org/repositories/home:/rodrigosbrito:/lyra:/staging/openSUSE_Leap_16.1/ "$alias" 2>&1 | tail -2 | tr '\n' ';')"
	emit refresh "$(zypper -n --gpg-auto-import-keys refresh -r "$alias" 2>&1 | tail -3 | tr '\n' ';')"
	emit repo_key "$(rpm -q gpg-pubkey --qf '%{VERSION}-%{RELEASE} %{SUMMARY}\n' | grep -i rodrigosbrito)"
	rel=48.8-160100.2.1.lyra1.160100.1
	sel=()
	for pair in gnome-shell.x86_64 gnome-shell-lang.noarch gnome-extensions.x86_64 gnome-shell-calendar.x86_64 gnome-shell-devel.x86_64; do
		rpm -q "${pair%.*}" >/dev/null 2>&1 && sel+=("$pair=$rel")
	done
	emit selection "${sel[*]}"
	out=$(zypper -n --xmlout install --dry-run --name --from "$alias" --no-recommends -- "${sel[@]}" 2>&1); rc=$?
	echo "$out" >"$WORK/plan.xml"
	emit plan "exit=$rc $(echo "$out" | grep -oE '<solvable [^>]*>' | tr '\n' ';')"
	out=$(zypper -n install --dry-run --name --from "$alias" --no-recommends -- "${sel[@]}" 2>&1); rc=$?
	emit plan_text "exit=$rc $(echo "$out" | tail -25 | tr '\n' ';')"
	zypper -q removerepo "$alias" >/dev/null 2>&1
	emit done ok
	;;
watch)
	seconds=${2:-60}
	last=""
	for _ in $(seq "$seconds"); do
		pid=$(shell_pid)
		cards=$(as_user pactl list cards short 2>/dev/null | awk '{print $2}' | tr '\n' ',')
		now="$pid|$cards"
		[ "$now" != "$last" ] && emit sample "pid=$pid cards=$cards"
		last=$now
		sleep 1
	done
	crashes
	emit done ok
	;;
*) echo "unknown phase $PHASE" >&2; exit 2 ;;
esac
