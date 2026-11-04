#!/bin/sh
# Flasht die Arch-ROM auf userdata (boot_a bleibt v0an). Setzt vor dem
# Neustart den Slot-Zaehler zurueck, sonst faellt ABOOT nach drei Fehlstarts
# auf Fastboot zurueck.
set -eu
FB=${FB:-$HOME/Library/Android/sdk/platform-tools/fastboot}
IMG=${1:-$HOME/hermes-workspace/images/arch-userdata/rootfs-vorlauf.sparse.img}
[ -f "$IMG" ] || { echo "nicht ok - $IMG fehlt"; exit 1; }
[ -n "$($FB devices 2>/dev/null)" ] || { echo "nicht ok - kein Geraet im Fastboot"; exit 1; }
shasum -a 256 "$IMG" | cut -d' ' -f1
$FB flash userdata "$IMG"
$FB --set-active=a
$FB getvar slot-retry-count:a 2>&1 | head -1
$FB reboot
echo "geflasht; SSH in ~35 s: ssh -i ~/.ssh/omamobile_blueline root@172.16.42.1"
