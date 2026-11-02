#!/bin/sh
# Write-Zyklus fuer v0ah: erst die Aussage und die Gegenprobe, dann die Write.
# Rueckweg bleibt: boot_a enthaelt nach diesem Write v0ah, boot_b und dtbo_b die
# Referenz, und ein zurueckkehrendes Telefon landet im Fastboot.
set -eu
FB=/Users/gregor/Library/Android/sdk/platform-tools/fastboot
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
BILD=/Users/gregor/hermes-workspace/images
LOG=$FL/evidence/vor-userdata/satz-vor-dem-write.txt
{
  echo "Satz vor dem Write, $(date '+%Y-%m-%d %H:%M'):"
  echo "userdata traegt weiterhin keine Nutzerdaten (Superblock null, mount -o ro meldet"
  echo "wrong fs type, Gerat entsperrt); das Bild ist jetzt rootfs-vorlauf.sparse.img mit"
  echo "1 MiB Vorlauf, damit ABOOTs GPT-Bereich (Kopf 4096, Saetze ab 8192) frei bleibt."
  echo "Backup boot_a: 67108864 B, sha256 0478f8dbe456a5877976f2514aa105619acf6c91056afb14eabe824d5c6929a0 (gemessen gegen sha256-lokal.txt)."
} >> "$LOG"
echo "--- Write-Pruefung: Begleitdateien gegen die Dateien selbst"
( cd "$BILD/userdata-alpine" && shasum -a 256 -c rootfs-vorlauf.sparse.img.sha256 )
( cd "$BILD/fl-v0ah" && shasum -a 256 firstlight.img )
echo "--- Telefon zurueck ins Fastboot"
python3 "$FL/sende-befehl.py" "/usr/bin/restart2 bootloader" >/dev/null 2>&1 || true
sleep 10
$FB devices
echo "--- flash userdata (Vorlauf-Bild, dichtes Sparse)"
$FB flash userdata "$BILD/userdata-alpine/rootfs-vorlauf.sparse.img" 2>&1 | tail -3
echo "--- flash boot_a (v0ah)"
$FB flash boot_a "$BILD/fl-v0ah/firstlight.img" 2>&1 | tail -3
$FB --set-active=a 2>&1 | tail -1
for v in current-slot slot-retry-count:a slot-unbootable:a; do
  printf "%s = %s\n" "$v" "$($FB getvar $v 2>&1 | head -1)"
done
$FB reboot 2>&1 | tail -1
echo "WRITE-ZYKLUS FERTIG"
