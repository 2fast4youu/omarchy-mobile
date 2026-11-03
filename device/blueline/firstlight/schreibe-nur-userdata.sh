#!/bin/sh
# Nur userdata schreiben: boot_a traegt jetzt v0al (switch_root bei 29 s) und
# darf nicht mehr mit v0ak ueberschrieben werden. Bildsumme wird gegen ihre
# Begleitdatei gemessen, bevor irgendetwas geschrieben wird.
set -u
FB=${FB:-/Users/gregor/Library/Android/sdk/platform-tools/fastboot}
BILD=${BILD:-/Users/gregor/hermes-workspace/images/userdata-alpine}
DATEI=$BILD/rootfs-vorlauf.sparse.img
LOG=${LOG:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/evidence/userdata-write-$(date +%H%M)-wurzel22-fix.txt}
{
  echo "=== userdata-Schreibvorgang (nur userdata, boot_a bleibt v0al) $(date '+%F %T')"
  for v in current-slot slot-retry-count:a slot-retry-count:b slot-unbootable:a slot-unbootable:b; do
    printf '%-22s ' "$v"; $FB getvar "$v" 2>&1 | grep -Ev '^(OKAY|finished|Warning)' | head -1
  done
  gemessen=$(shasum -a 256 "$DATEI" | cut -d' ' -f1)
  notiert=$(cut -d' ' -f1 "$DATEI.sha256")
  echo "Bild $DATEI"
  echo "  Groesse $(stat -f %z "$DATEI") B"
  echo "  gemessen $gemessen"
  echo "  notiert  $notiert"
  if [ "$gemessen" != "$notiert" ]; then echo "NICHT GESCHRIEBEN: Summe weicht von der Begleitdatei ab"; exit 1; fi
  echo "  $FB devices: $($FB devices 2>&1 | tr -d '\n')"
  echo "--- flash userdata $(date '+%T')"
  $FB flash userdata "$DATEI" 2>&1
  zy=$?
  echo "flash userdata Ausgang $zy um $(date '+%T')"
  [ "$zy" -eq 0 ] || { echo "NICHT GESCHRIEBEN"; exit 1; }
  for v in current-slot slot-retry-count:a slot-unbootable:a; do
    printf '%-22s ' "$v"; $FB getvar "$v" 2>&1 | grep -Ev '^(OKAY|finished|Warning)' | head -1
  done
  echo "--- Slot a aktivieren und starten $(date '+%T')"
  $FB --set-active=a 2>&1 | tail -2
  $FB reboot 2>&1 | tail -1
  echo "Neustart kommandiert $(date '+%T')"
} 2>&1 | tee "$LOG"
