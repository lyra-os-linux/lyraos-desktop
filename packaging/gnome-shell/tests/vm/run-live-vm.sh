#!/bin/bash
# Boot a Lyra live ISO headless for the SHELL-01 regression.
# Usage: run-live-vm.sh ISO WORKDIR
#   WORKDIR/serve is published to the guest at http://10.0.2.2:PORT,
#   WORKDIR/qmp.sock controls the VM (see qmp.py), and the guest's virtio
#   port org.lyraos.UpgradeEvidence is appended to WORKDIR/evidence.jsonl.
# The VM has an Intel HDA codec and an xhci bus for usb-audio hotplug.
# Optional environment: LYRA_VM_DISK=FILE.qcow2 attaches an install disk
# (created at 32G if missing; ISO boots first until the disk is bootable),
# LYRA_VM_NO_ISO=1 boots only the disk, LYRA_VM_HTTP_PORT (default 8765).
# Nothing outside WORKDIR is written.
set -euo pipefail
iso=$(readlink -f "$1")
work=$(readlink -f "$2")
cd "$work"
port=${LYRA_VM_HTTP_PORT:-8765}
[ -f vars.bin ] || cp /usr/share/qemu/ovmf-x86_64-4m-vars.bin vars.bin
# Stable SMBIOS UUID: lyra-upgrade-probe requires /sys/class/dmi/id/product_uuid.
[ -f uuid ] || cat /proc/sys/kernel/random/uuid >uuid
media=()
if [ -n "${LYRA_VM_DISK:-}" ]; then
	[ -f "$LYRA_VM_DISK" ] || qemu-img create -q -f qcow2 "$LYRA_VM_DISK" 32G
	media+=(-drive if=virtio,format=qcow2,file="$LYRA_VM_DISK")
fi
[ -n "${LYRA_VM_NO_ISO:-}" ] || media+=(-drive media=cdrom,readonly=on,file="$iso")
python3 -m http.server "$port" --bind 127.0.0.1 --directory serve >http.log 2>&1 &
http=$!
trap 'kill $http 2>/dev/null' EXIT
qemu-system-x86_64 \
	-name "lyra-shell01-$port" -uuid "$(cat uuid)" -machine q35,accel=kvm -cpu host -smp 4 -m 8192 \
	-drive if=pflash,format=raw,readonly=on,file=/usr/share/qemu/ovmf-x86_64-4m-code.bin \
	-drive if=pflash,format=raw,file=vars.bin \
	"${media[@]}" \
	-qmp unix:"$work/qmp.sock",server=on,wait=off \
	-chardev file,id=evidence,path="$work/evidence.jsonl",append=on \
	-device virtio-serial-pci \
	-device virtserialport,chardev=evidence,name=org.lyraos.UpgradeEvidence \
	-audiodev none,id=snd0 \
	-device ich9-intel-hda -device hda-duplex,audiodev=snd0 \
	-device qemu-xhci,id=xhci -device usb-tablet,bus=xhci.0 \
	-netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
	-vga virtio -display none \
	-serial file:"$work/serial.log"
