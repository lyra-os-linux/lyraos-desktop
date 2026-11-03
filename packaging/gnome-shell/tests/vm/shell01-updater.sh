#!/bin/bash
# SHELL-01 PackageMigration lifecycle helpers, run as root inside a disposable
# installed Lyra VM. Observations go to the virtio port as JSON lines.
#
#   shell01-updater.sh setup URL   testing channel + manifest base URL, serial journal
#   shell01-updater.sh state NAME  packages, Updater state, snapshots, crashes
#   shell01-updater.sh statesubvol own subvolume for /var/lib/lyra-upgrade (fix candidate)
#   shell01-updater.sh installvolume  install the candidate 0.2.10 boot migration
#   shell01-updater.sh volumecheck    result of that migration after boot
#   shell01-updater.sh fault       rollback fixture: enable a unit that fails at boot
#   shell01-updater.sh investigate boot/package timeline of the operation
#   shell01-updater.sh fetchcheck  repeat the Updater manifest fetch step by step
set -uo pipefail

PORT=/dev/virtio-ports/org.lyraos.UpgradeEvidence
WORK=/var/tmp/shell01
mkdir -p "$WORK"
PHASE=${2:-${1:?phase}}

emit() {
	python3 -c 'import json,sys; print(json.dumps({"phase": sys.argv[1], "key": sys.argv[2], "value": sys.argv[3]}))' \
		"$PHASE" "$1" "${*:2}" | tee -a "$PORT" "$WORK/evidence.jsonl" >/dev/null
}

case "$1" in
setup)
	url=${2:?manifest base URL}
	PHASE=setup
	mkdir -p /run/systemd/journald.conf.d
	printf '[Journal]\nForwardToConsole=yes\nTTYPath=/dev/ttyS0\nMaxLevelConsole=info\n' >/run/systemd/journald.conf.d/50-shell01-serial.conf
	systemctl restart systemd-journald
	emit channel_before "$(cat /etc/lyra-upgrade/channel 2>&1)"
	echo testing >/etc/lyra-upgrade/channel
	# Exactly one line without a trailing newline: the Updater rejects value != trim(value).
	printf '%s' "$url" >/etc/lyra-upgrade/testing-manifest-base-url
	emit channel "$(cat /etc/lyra-upgrade/channel) $(cat /etc/lyra-upgrade/testing-manifest-base-url)"
	emit done ok
	;;
state)
	emit identity "$(tr '\n' ';' </usr/lib/lyra-os/product-release)"
	emit rpm "$(rpm -q --qf '%{NAME}-%{VERSION}-%{RELEASE} %{VENDOR}\n' gnome-shell gnome-shell-lang gnome-extensions gnome-shell-calendar lyra-upgrade 2>&1 | tr '\n' ';')"
	emit libgvc_sha256 "$(sha256sum /usr/lib64/gnome-shell/libgvc.so | cut -d' ' -f1)"
	emit repos "$(zypper -q lr -u 2>&1 | tail -n +3 | awk -F'|' '{gsub(/ /,"",$2); print $2}' | tr '\n' ',')"
	emit repos_sha256 "$(cat /etc/zypp/repos.d/*.repo | sha256sum | cut -d' ' -f1)"
	emit sequence "$(cat /var/lib/lyra-upgrade/last-manifest-sequence 2>&1)"
	emit updater_state "$(find /var/lib/lyra-upgrade -maxdepth 3 -type f -newer /etc/machine-id -printf '%P ' 2>&1)"
	for f in /var/lib/lyra-upgrade/operations/*/state.json; do
		[ -f "$f" ] && emit operation "$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({k: d.get(k) for k in ("operation_id","sequence","operation","state","snapshot_number","recovery","last_completed_step","error_code","boot_verification","manifest_sha256","updated_at")}))' "$f" 2>&1)"
	done
	emit snapper "$(snapper --no-dbus list 2>&1 | tail -6 | tr '\n' ';')"
	emit default_subvolume "$(btrfs subvolume get-default / 2>&1)"
	emit failed_units "$(systemctl --failed --no-legend 2>&1 | tr '\n' ';')"
	emit coredumps "$(coredumpctl list --no-legend --no-pager 2>&1 | tr '\n' ';')"
	emit shell "$(pgrep -a -x gnome-shell | tr '\n' ';')"
	emit done ok
	;;
fault)
	# Rollback fixture: a unit that fails at boot, created after the migration
	# snapshot, so the post-boot verifier must report NeedsRecovery and the
	# snapshot rollback must remove it.
	PHASE=fault
	emit ready "$(python3 -c 'import json,glob; print([json.load(open(p))["state"] for p in glob.glob("/var/lib/lyra-upgrade/operations/*/state.json")])' 2>&1)"
	cat >/etc/systemd/system/shell01-fault.service <<'UNIT'
[Unit]
Description=SHELL-01 rollback fixture (always fails)

[Service]
Type=oneshot
ExecStart=/usr/bin/false

[Install]
WantedBy=multi-user.target
UNIT
	systemctl daemon-reload
	emit enable "$(systemctl enable shell01-fault.service 2>&1 | tr '\n' ';')"
	emit done ok
	;;
investigate)
	# Timeline of a PackageMigration: when packages changed and in which boot.
	PHASE=investigate
	op=$(ls -d /var/lib/lyra-upgrade/operations/*/ 2>/dev/null | head -1)
	emit boots "$(journalctl --list-boots --no-pager 2>&1 | tr '\n' ';')"
	emit reboots "$(last -x reboot shutdown 2>&1 | head -8 | tr '\n' ';')"
	emit rpm_installtime "$(rpm -q --qf '%{NAME} %{INSTALLTIME:date}\n' gnome-shell gnome-shell-lang gnome-extensions | tr '\n' ';')"
	emit zypp_history "$(grep -E '\|(install|remove|command)\|' /var/log/zypp/history | tail -8 | cut -c1-220 | tr '\n' ';')"
	emit snapper_full "$(snapper --no-dbus list --columns number,type,pre-number,date,cleanup,description,userdata 2>&1 | tail -6 | tr '\n' ';')"
	emit state_json "$(cat "$op/state.json" 2>&1)"
	emit op_files "$(ls -la --time-style=+%FT%T "$op" 2>&1 | tail -n +2 | awk '{print $6, $7}' | tr '\n' ';')"
	for f in "$op"/events*.jsonl "$op"/*.events "$op"/events.json; do
		[ -f "$f" ] && emit "events:${f##*/}" "$(cut -c1-200 "$f" | tr '\n' ';')"
	done
	for b in -1 0; do
		emit "journal_b$b" "$(journalctl -b "$b" --no-pager -o short-iso -u lyra-upgrade-offline.service -u lyra-upgrade-verify.service -u system-update.target -u system-update-pre.target -u 'lyra-upgrade*' 2>&1 | grep -v lyra-upgrade-query | tail -40 | cut -c1-220 | tr '\n' ';')"
	done
	emit target_b1 "$(journalctl -b -1 --no-pager -o short-iso 2>&1 | grep -E 'Reached target|system-update|offline|zypper|Rebooting|reboot' | tail -25 | cut -c1-200 | tr '\n' ';')"
	emit query_warnings "$(journalctl -b --no-pager -o short-iso -p warning -u 'lyra-upgrade-query@*' 2>&1 | tail -12 | cut -c1-220 | tr '\n' ';')"
	emit service_log "$(journalctl -b --no-pager -o short-iso 2>&1 | grep -E 'lyra-upgrade-service|pkexec' | tail -12 | cut -c1-220 | tr '\n' ';')"
	emit system_update_link "$(ls -la /system-update 2>&1)"
	emit done ok
	;;
statesubvol)
	# Candidate fix: keep Updater recovery records in their own subvolume,
	# mounted like the installer's other /@/... subvolumes.
	PHASE=statesubvol
	if [ -e /var/lib/lyra-upgrade ] && [ -n "$(ls -A /var/lib/lyra-upgrade 2>/dev/null)" ]; then
		emit refused "/var/lib/lyra-upgrade is not empty"; exit 1
	fi
	rmdir /var/lib/lyra-upgrade 2>/dev/null
	emit create "$(btrfs subvolume create /var/lib/lyra-upgrade 2>&1)"
	chmod 0700 /var/lib/lyra-upgrade
	uuid=$(findmnt -no UUID /)
	opts=$(awk '$2 == "/var/log" {print $4}' /etc/fstab | sed 's|subvol=[^,]*|subvol=/@/var/lib/lyra-upgrade|')
	echo "UUID=$uuid /var/lib/lyra-upgrade btrfs $opts 0 0" >>/etc/fstab
	systemctl daemon-reload
	emit mount "$(mount /var/lib/lyra-upgrade 2>&1; findmnt -no SOURCE,OPTIONS /var/lib/lyra-upgrade)"
	emit ids "root=$(btrfs inspect-internal rootid /) state=$(btrfs inspect-internal rootid /var/lib/lyra-upgrade)"
	emit done ok
	;;
installvolume)
	# Install the candidate Updater 0.2.10 boot migration from the host, as
	# the RPM would, without changing anything else; it runs at next boot.
	PHASE=installvolume
	base=${2:-http://10.0.2.2:8766}
	curl -sf -o /usr/libexec/lyra-upgrade-state-volume "$base/lyra-upgrade-state-volume" &&
		curl -sf -o /etc/systemd/system/lyra-upgrade-state-volume.service "$base/lyra-upgrade-state-volume.service" ||
		{ emit install "fetch failed"; exit 1; }
	chmod 0755 /usr/libexec/lyra-upgrade-state-volume
	emit sha256 "$(sha256sum /usr/libexec/lyra-upgrade-state-volume /etc/systemd/system/lyra-upgrade-state-volume.service | tr '\n' ';')"
	systemctl daemon-reload
	emit enable "$(systemctl enable lyra-upgrade-state-volume.service 2>&1 | tr '\n' ';')"
	emit sequence_before "$(cat /var/lib/lyra-upgrade/last-manifest-sequence 2>&1)"
	emit done ok
	;;
volumecheck)
	PHASE=volumecheck
	emit unit "$(systemctl show lyra-upgrade-state-volume.service -p ActiveState -p Result -p ConditionResult -p ExecMainStatus 2>&1 | tr '\n' ' ')"
	emit journal "$(journalctl -b --no-pager -o cat -u lyra-upgrade-state-volume.service 2>&1 | tail -6 | tr '\n' ';')"
	emit mount "$(findmnt -no SOURCE /var/lib/lyra-upgrade 2>&1)"
	emit ids "root=$(btrfs inspect-internal rootid /) state=$(btrfs inspect-internal rootid /var/lib/lyra-upgrade 2>&1)"
	emit fstab "$(grep lyra-upgrade /etc/fstab 2>&1)"
	emit sequence "$(cat /var/lib/lyra-upgrade/last-manifest-sequence 2>&1)"
	emit operations "$(ls /var/lib/lyra-upgrade/operations 2>&1 | tr '\n' ' ')"
	emit kept "$(mkdir -p /run/lv && mount -o subvolid=5 UUID=$(findmnt -no UUID /) /run/lv && ls -a /run/lv/@/var/lib | grep lyra-upgrade | tr '\n' ' '; umount /run/lv)"
	emit failed_units "$(systemctl --failed --no-legend 2>&1 | tr '\n' ';')"
	emit done ok
	;;
layout)
	# Where the Updater keeps recovery records relative to the root snapshot.
	PHASE=layout
	emit subvolumes "$(btrfs subvolume list / 2>&1 | awk '{print $2, $NF}' | tr '\n' ';')"
	emit root_subvol_id "$(btrfs inspect-internal rootid / 2>&1)"
	emit state_subvol_id "$(btrfs inspect-internal rootid /var/lib/lyra-upgrade 2>&1)"
	emit var_lib_subvol_id "$(btrfs inspect-internal rootid /var/lib 2>&1)"
	emit in_snapshot3 "$(ls -d /.snapshots/3/snapshot/var/lib/lyra-upgrade 2>&1)"
	emit fstab "$(grep -v '^#' /etc/fstab | tr '\n' ';')"
	emit done ok
	;;
fetchcheck)
	# Repeat the Updater's manifest fetch steps (manifest_fetch.rs) one by one.
	PHASE=fetchcheck
	base=$(cat /etc/lyra-upgrade/testing-manifest-base-url)
	emit url_bytes "$(od -c /etc/lyra-upgrade/testing-manifest-base-url | tail -3 | tr '\n' ' ')"
	emit date_utc "$(date -u +%FT%TZ)"
	dl() { curl --fail --silent --show-error --location --max-redirs 3 --proto =https --proto-redir =https \
		--tlsv1.2 --max-filesize 1048576 --connect-timeout 10 --max-time 60 -o "$2" "$1" 2>&1; echo "exit=$?"; }
	emit manifest_download "$(dl "${base}releases-v1.json" "$WORK/m.json")"
	emit signature_download "$(dl "${base}releases-v1.json.asc" "$WORK/m.asc")"
	emit sha256 "$(sha256sum "$WORK/m.json" "$WORK/m.asc" | tr '\n' ';')"
	emit gpgv "$(env -i PATH=/usr/bin:/bin LC_ALL=C gpgv --keyring /usr/share/lyra-upgrade/release-signing-key.gpg -- "$WORK/m.asc" "$WORK/m.json" 2>&1 | tr '\n' ';') exit=$?"
	python3 - "$WORK/m.json" <<'PY' | while IFS='|' read -r alias fpr url; do
import json, sys
for r in json.load(open(sys.argv[1]))["repositories"]:
    print("|".join((r["alias"], r["signing_key_fingerprint"], r["signing_key_url"])))
PY
		out=$(dl "$url" "$WORK/key-$alias")
		got=$(gpg --batch --show-keys --with-colons "$WORK/key-$alias" 2>/dev/null | awk -F: '/^fpr/{print $10; exit}')
		emit "key:$alias" "$out $([ "$got" = "$fpr" ] && echo match || echo "mismatch got=$got")"
	done
	emit done ok
	;;
*) echo "unknown command $1" >&2; exit 2 ;;
esac
