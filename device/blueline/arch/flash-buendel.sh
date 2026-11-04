#!/bin/sh
# Flash in EINER Fastboot-Sitzung: boot_a + userdata, Slot setzen, Zaehler
# lesen, neu starten. Jeder boot_a-Write fuellt slot-retry-count auf 3 auf;
# ueberzaehlige Reboots verbrauchen ihn (nach drei Starts ohne Erfolgsmarke
# faellt ABOOT auf Fastboot). Deshalb alles in einem Lauf.
set -eu
BOOT=${BOOT:-$HOME/hermes-workspace/images/fl-v0ba/firstlight.img}
USERDATA=${USERDATA:-$HOME/hermes-workspace/images/arch-userdata/rootfs-vorlauf.sparse.img}
FB=${FB:-$HOME/Library/Android/sdk/platform-tools/fastboot}
echo "boot:     $BOOT"
echo "userdata: $USERDATA"
"$FB" getvar current-slot 2>&1 | tail -1
"$FB" flash boot_a "$BOOT"
"$FB" flash userdata "$USERDATA"
"$FB" --set-active=a
"$FB" getvar slot-retry-count:a 2>&1 | tail -1
"$FB" reboot
