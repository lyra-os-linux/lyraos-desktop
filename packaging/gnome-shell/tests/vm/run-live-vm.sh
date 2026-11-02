#!/bin/bash
# Boot a Lyra live ISO headless for the SHELL-01 regression.
# Usage: run-live-vm.sh ISO WORKDIR
#   WORKDIR/serve is published at http://10.0.2.2:8765 for the guest,
#   WORKDIR/qmp.sock controls the VM (see qmp.py), and the guest's virtio
#   port org.lyraos.UpgradeEvidence is appended to WORKDIR/evidence.jsonl.
# The VM has an Intel HDA codec and an xhci bus for usb-audio hotplug; no
# disk is attached, so nothing outside WORKDIR is written.
set -euo pipefail
iso=$(readlink -f "$1")
work=$(readlink -f "$2")
cd "$work"
cp /usr/share/qemu/ovmf-x86_64-4m-vars.bin vars.bin
python3 -m http.server 8765 --bind 127.0.0.1 --directory serve >http.log 2>&1 &
http=$!
trap 'kill $http 2>/dev/null' EXIT
qemu-system-x86_64 \
	-name lyra-shell01 -machine q35,accel=kvm -cpu host -smp 4 -m 8192 \
	-drive if=pflash,format=raw,readonly=on,file=/usr/share/qemu/ovmf-x86_64-4m-code.bin \
	-drive if=pflash,format=raw,file=vars.bin \
	-drive media=cdrom,readonly=on,file="$iso" \
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
