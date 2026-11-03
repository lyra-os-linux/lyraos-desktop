#!/bin/sh
# Deterministic SHELL-01 regression: inject a card with zero profiles and a
# NULL active profile into Gvc.MixerControl, as pipewire-pulse did at login.
# Usage: run.sh <pulse-include-dir> <dir-containing-libgvc.so>
# Needs a running PulseAudio/pipewire-pulse server, gcc and gjs. A crashing
# libgvc exits 139; a fixed one prints SURVIVED and exits 0.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
include=$1
libdir=$2
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
gcc -shared -fPIC -O1 -Wall -I "$include" -o "$work/shim.so" \
    "$here/zero-profile-card.c" -ldl /usr/lib64/libpulse.so.0
GI_TYPELIB_PATH=/usr/lib64/gnome-shell LD_LIBRARY_PATH=$libdir \
    LD_PRELOAD=$work/shim.so gjs "$here/gvc-test.js"
