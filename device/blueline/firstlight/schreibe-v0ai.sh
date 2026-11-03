#!/bin/sh
# Write-Zyklus fuer v0ai, mit Wachhueter ueber jedem Write und mit der
# Backup-Gegenprobe vor JEDEM Partitions-Write (Gregors Regel vom 31.10.:
# "künftig vor jedem Partitions-Write die Backup-Datei auf Größe und sha256
# prüfen, bevor du flasht").
#
# Was sich seit v0ah geaendert hat (gemessen, nicht gemeint):
#   offset= ist in BYTE — v0ai mountet 1048576, nicht 1024 (arm64-Container, das
#   mount aus dem ausgelieferten Archiv, util-linux 2.41.6).
#   Kein 2>/dev/null an den Mounts; der Wortlaut geht in die Marke.
#   Die Uebertragung ist klein: rootfs-vorlauf.sparse.img traegt echte Loecher
#   (117 441 332 B, eine Sitzung) statt 1 GiB in fuenf Sitzungen.
#
# Fuer die Marker-Messung (Punkt 3 des Check-ins) wird UDATEI auf
# marker-4mib.sparse.img gesetzt. Das ist zugleich der sauberste Link-Test: 4 MiB,
# ein Sack, keine Loecher — jedes Feld zwischen 0 und 4 MiB wird wirklich
# geschrieben. Sind MK4096/MK8192 nach dem naechsten Boot weg, kann das nur ABOOT
# gewesen sein; bleiben sie, war der erste Write von 17:01 die Quelle (fastboots
# eigene Umrechnung liess genau dort Locher) und die Vorlauf-These ist widerlegt.
set -eu
FB=${FB:-/Users/gregor/Library/Android/sdk/platform-tools/fastboot}
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
BILD=${BILD:-/Users/gregor/hermes-workspace/images}
BACKUP=${BACKUP:-/Users/gregor/hermes-workspace/backups/blueline-2026-11-01}
UDATEI=${UDATEI:-$BILD/userdata-alpine/rootfs-vorlauf.sparse.img}
BOOTIMG=${BOOTIMG:-$BILD/fl-v0ai/firstlight.img}
LOG=$FL/evidence/vor-userdata/satz-vor-dem-write.txt
FRIST=${FRIST:-900}

schreib() {
    # schreib PARTITION DATEI [SICHERUNG]: ein Write mit Frist. Ueber der Frist
    # wird abgebrochen und der Zyklus endet mit Grund, statt weiterzulaufen —
    # ein haengender Write darf kein Fenster auffressen (gemessen 17:2x). Der
    # Unterlauf bekommt keinen Standardausgang: sein schlafendes Kind erbt den
    # Ausgang des Vaters, und eine Rohrleitung hinter diesem Skript bliebe offen
    # (gemessen: ein Prueflauf hing 180 s genau daran).
    partei=$1; datei=$2; sicherung=${3:-}
    if [ -n "$sicherung" ]; then
        # Gregors Regel, hart eingebaut: Groesse und sha256 der Sicherung vor dem
        # Write, und bei Abbruch kein Weiterlaufen. Die Summenliste liegt bei den
        # Sicherungen selbst (sha256-lokal.txt), nicht im Kopf.
        groesse=$(ls -l "$sicherung" | awk '{print $5}')
        echt=$(shasum -a 256 "$sicherung" | cut -d' ' -f1)
        soll=$(grep " $(basename "$sicherung")\$" "$BACKUP/sha256-lokal.txt" | cut -d' ' -f1)
        if [ -n "$soll" ] && [ "$echt" = "$soll" ]; then
            echo "    Sicherung $partei: $groesse B, sha256 $echt — stimmt mit sha256-lokal.txt"
        else
            echo "    ABBRUCH: Sicherung $partei ist $groesse B, sha256 $echt; erwartet $soll"
            return 1
        fi
    fi
    ( sleep "$FRIST"; pkill -f "fastboot flash $partei" 2>/dev/null ) </dev/null \
        >/dev/null 2>&1 &
    waechter=$!
    # Kein Rohrleitung-Exit: 'flash … | tail -3' meldet tails Ausgang, nicht den
    # von fastboot, und ein abgebrochener Write gilt als gelungen (dieselbe Falle
    # wie beim '… | tail' der Bauern). Der Ausgang kommt aus einer Datei.
    aus=$LOG.schreib-$partei.txt
    if $FB flash "$partei" "$datei" >"$aus" 2>&1; then rc=0; else rc=$?; fi
    kill "$waechter" 2>/dev/null || true
    tail -3 "$aus"
    if [ "$rc" -ne 0 ]; then
        echo "FEHLER: Write auf $partei endete mit Ausgang $rc (Volles Protokoll: $aus)"
        return 1
    fi
    if ! grep -q OKAY "$aus"; then
        echo "FEHLER: Write auf $partei meldete kein OKAY (Volles Protokoll: $aus)"
        return 1
    fi
}

mkdir -p "$(dirname "$LOG")"
{
  echo "--- Satz vor dem Write, Write-Zyklus v0ai, $(date '+%Y-%m-%d %H:%M'),"
  echo "    Frist $FRIST s."
  echo "    userdata traegt weiterhin keine Nutzerdaten: Superblock null, mount -o ro"
  echo "    meldet 'wrong fs type', Gerat entsperrt (getvar unlocked: yes). Belegt am"
  echo "    2026-11-02, 16:15 in evidence/vor-userdata/, und ein 51-GiB-Backup gibt es"
  echo "    nicht — darum diese Zeilen vor jedem Write."
  echo "    userdata-Inhalt: $(basename "$UDATEI") ($(ls -l "$UDATEI" | awk '{print $5}') B)."
  echo "    boot_a-Inhalt:   $(basename "$BOOTIMG") ($(ls -l "$BOOTIMG" | awk '{print $5}') B)."
  echo "    Rueckweg: images/fl-v0af/firstlight.img mit Power+Leiser; Slot b unangetastet."
  echo "    Sicherung boot_a: kalibrier-boot_a.bin, 67108864 B, sha256 0478f8dbe456a587…"
  echo "    Sicherung boot_a: kalibrier-boot_a.bin, 67108864 B, sha256 0478f8dbe456a587…"
} >> "$LOG"

echo "--- Gegenprobe der Begleitdateien vor dem ersten Write"
( cd "$(dirname "$UDATEI")" && shasum -a 256 -c "$(basename "$UDATEI").sha256" )
[ -f "$BOOTIMG.sha256" ] && ( cd "$(dirname "$BOOTIMG")" \
    && shasum -a 256 -c "$(basename "$BOOTIMG").sha256" ) || echo "    (keine Begleitdatei fuer die Bootdatei)"
$FB devices
echo "--- Write 1: userdata"
schreib userdata "$UDATEI"
echo "--- Write 2: boot_a"
schreib boot_a "$BOOTIMG" "$BACKUP/kalibrier-boot_a.bin"
echo "--- Slot a aktivieren und starten"
$FB --set-active=a
$FB reboot
echo "WRITE-ZYKLUS FERTIG"
