#!/bin/sh
# Wartet auf das Telefon im Fastboot und faehrt dann den Write-Zyklus selbst.
#
# Anlass in der Nacht auf 2026-11-03: v0ak bootet, die Userdata-Wurzel ist rw und
# haltbar, aber die Uebergabe war stumm - das neue Root brachte kein Gadget und
# kein telnetd mit (switch_root haengt das configfs ab), also war der Mac blind.
# Neues Userdata-Bild traegt beides. Sobald das Telefon wieder da ist, soll es
# nicht auf einen Menschen warten muessen: Begleitdateien prueft der Zyklus selbst,
# und vor jedem Partitions-Write legt er die Sicherung gegen sha256-lokal.txt frei.
#
# Aufruf:  sh warte-und-schreibe.sh              (Standard: 40 Minuten Frist)
#          FRIST_RUNDEN=60 sh warte-und-schreibe.sh
set -u
FB=/Users/gregor/Library/Android/sdk/platform-tools/fastboot
BILD=${BILD:-/Users/gregor/hermes-workspace/images}
HIER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FRIST_RUNDEN=${FRIST_RUNDEN:-240}      # 240 Runden a 10 s = 40 Minuten

r=1
while [ "$r" -le "$FRIST_RUNDEN" ]; do
    liste=$($FB devices 2>/dev/null)
    if [ -n "$liste" ]; then
        echo "telefon im fastboot nach $((r * 10))s: $liste"
        break
    fi
    sleep 10
    r=$((r + 1))
done
if [ "$r" -gt "$FRIST_RUNDEN" ]; then
    echo "nach $((FRIST_RUNDEN * 10))s kein telefon im fastboot - nichts geschrieben"
    exit 1
fi

cd "$HIER" || exit 1
echo "--- Write-Zyklus: userdata (neues Bild) und boot_a (v0ak) ---"
# Kein Rohrleitung-Exit: der Zyklus laeuft in eine Datei, die Leitung am Ende
# waere der dritte Auftritt derselben Falle (tail/grep meldet seinen eigenen Exit).
LOG=${LOG:-/tmp/warte-und-schreibe.log}
BOOTIMG=$BILD/fl-v0ak/firstlight.img FRIST=420 sh schreibe-v0ai.sh >"$LOG" 2>&1
zy=$?
grep -v Terminated "$LOG" | tail -40
echo "--- Write-Zyklus Exit $zy (volles Protokoll: $LOG) ---"
exit "$zy"
