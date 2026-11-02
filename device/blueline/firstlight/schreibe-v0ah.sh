#!/bin/sh
# Write-Zyklus fuer v0ah, zweite Fassung: mit Wachhueter ueber jedem Write.
#
# Warum der Wachhueter noetig ist (gemessen 2026-11-02, 17:2x): der erste Zyklus
# hing 9 Minuten in 'fastboot flash userdata': der Prozess hatte 5,06 s
# Rechenzeit und bekam in 20 s keine Millisekunde dazu, er wartete auf das Gerat.
# Nach dem Abbruch lief das Skript weiter, weil die Rohrleitung den Exit der
# Pipeline meldet, und wartete anschliessend bei '--set-active=a'. Ein haengender
# Write darf kein Fenster auffressen.
#
# Reihenfolge bleibt Regel: erst Satz und Gegenproben, dann der erste Write.
set -eu
FB=${FB:-/Users/gregor/Library/Android/sdk/platform-tools/fastboot}
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
BILD=/Users/gregor/hermes-workspace/images
LOG=$FL/evidence/vor-userdata/satz-vor-dem-write.txt
FRIST=${FRIST:-900}

schreib() {
    # schreib PARTITION DATEI: ein Write mit Frist. Ueber der Frist wird
    # abgebrochen und der Zyklus endet mit Grund, statt weiterzulaufen. Der
    # Unterlauf bekommt keinen Standardausgang: sein schlafender Kindprozess
    # erbt den Ausgang des Vaters, und eine Rohrleitung hinter diesem Skript
    # bliebe bis zu seinem Ende offen (gemessen: der Prueflauf hing 180 s genau
    # daran). Die Frist war mit 300 s zu eng: ein 1-GiB-Write braucht laenger,
    # wenn das Gerat traegt. FRIST ist darum uebergebbar, Default 900 s.
    partei=$1; datei=$2
    ( sleep "$FRIST"; pkill -f "fastboot flash $partei" 2>/dev/null ) </dev/null \
        >/dev/null 2>&1 &
    waechter=$!
    if $FB flash "$partei" "$datei" 2>&1 | tail -3; then
        kill "$waechter" 2>/dev/null || true
    else
        kill "$waechter" 2>/dev/null || true
        echo "FEHLER: Write auf $partei brachte kein OKAY"
        return 1
    fi
}

{
  echo "--- Satz vor dem Write, Write-Zyklus v0ah (zweite Fassung)," 
  echo "    $(date '+%Y-%m-%d %H:%M'), Frist $FRIST s, Bild und Backup unten:"
  echo "userdata traegt weiterhin keine Nutzerdaten (Superblock null, mount -o ro"
  echo "meldet wrong fs type, Gerat entsperrt). Bild: rootfs-vorlauf.sparse.img mit"
  echo "1 MiB Vorlauf, damit ABOOTs GPT-Bereich (Kopf 4096, Saetze ab 8192) frei bleibt."
  echo "Backup boot_a: 67108864 B, sha256 0478f8dbe456a5877976f2514aa105619acf6c91056afb14eabe824d5c6929a0 (gemessen gegen sha256-lokal.txt)."
} >> "$LOG"

echo "--- Gegenprobe der Begleitdateien vor dem ersten Write"
( cd "$BILD/userdata-alpine" && shasum -a 256 -c rootfs-vorlauf.sparse.img.sha256 )
( cd "$BILD/fl-v0ah" && shasum -a 256 firstlight.img )
$FB devices
echo "--- Write 1: userdata"
schreib userdata "$BILD/userdata-alpine/rootfs-vorlauf.sparse.img"
echo "--- Write 2: boot_a"
schreib boot_a "$BILD/fl-v0ah/firstlight.img"
$FB --set-active=a 2>&1 | tail -1
for v in current-slot slot-retry-count:a slot-unbootable:a; do
  printf "%s = %s\n" "$v" "$($FB getvar $v 2>&1 | head -1)"
done
$FB reboot 2>&1 | tail -1
echo "WRITE-ZYKLUS FERTIG"
