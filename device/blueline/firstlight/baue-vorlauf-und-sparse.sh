#!/bin/sh
# SPDX-License-Identifier: MIT
# Vorlauf-Bild und Sparse-Image aus dem gewachsenen rootfs.ext4, mit Nachweis.
#
# Warum ein Vorlauf: die userdata-Partition legt beim ersten Kontakt ein GPT ab
# (bei 4096 stand 'EFI PART' statt der Gruppenbeschreiber, gemessen 2026-11-02).
# Das Dateisystem sitzt deshalb bei 1 MiB im Blockgeraet, und der Initramfs-Init
# mountet es mit offset=1048576 - die Einheit von offset= ist BYTE, nicht Block
# (gemessen mit util-linux 2.41.6 aus dem ausgelieferten Archiv).
#
# Warum ein eigenes Sparse-Bild: `fastboot flash userdata rootfs.ext4` rechnet
# selbst um und laesst genau die Baelle 4096 und 8192 ungefroren. Das eigene Bild
# traegt jedes 4096-Byte-Baal als DATA, auch die Nullen (zusammengefasst zu
# 16-MiB-Brocken, weil ein Sack pro Block ABOOT festlaufen laesst).
#
# Geprueft wird die ganze Kette, nicht nur das Endstueck:
#   1. sha256 von rootfs.ext4 gegen seine Begleitdatei,
#   2. der Korper des Vorlaufbilds (alles nach dem 1-MiB-Kopf) bytegleich mit
#      rootfs.ext4 - das beweist zugleich, dass der Kopf genau 1 MiB ist,
#   3. baue-sparse.py liest den Strom zurueck und meldet die Summe des Rohbilds,
#   4. /init im Bild ist die Quelldatei, Wort fuer Wort (debugfs-Ruecklese).
#
# Gebrauch (im Container, arm64):
#   docker run --rm --platform linux/arm64/v8 -v <repo>/device/blueline/firstlight:/om:ro \
#     -v ~/hermes-workspace:/ws baue-und-pruefe alpine:edge sh /om/baue-vorlauf-und-sparse.sh
set -eu
BILD=${BILD:-/ws/images/userdata-alpine}
OM=${OM:-/om}
QUELLE=${QUELLE:-$OM/rootfs-init-fuer-ud.sh}
VORLAUF=$((1024 * 1024))
ROH="$BILD/rootfs.ext4"
VOR="$BILD/rootfs-vorlauf.ext4"
SPARSE="$BILD/rootfs-vorlauf.sparse.img"

apk add --no-cache e2fsprogs-extra coreutils python3 >/dev/null 2>&1 || true
[ -f "$ROH" ]    || { echo "nicht ok - $ROH fehlt (zuerst baue-userdata-image.sh)"; exit 1; }
[ -f "$QUELLE" ] || { echo "nicht ok - die /init-Quelle $QUELLE fehlt"; exit 1; }
[ -f "$OM/baue-sparse.py" ] || { echo "nicht ok - baue-sparse.py fehlt unter $OM"; exit 1; }
sh -n "$QUELLE" || { echo "nicht ok - die /init-Quelle parst nicht"; exit 1; }

# --- 1) Rohbild
summe_roh=$(sha256sum "$ROH" | cut -d' ' -f1)
if [ -f "$ROH.sha256" ]; then
  notiert=$(cut -d' ' -f1 "$ROH.sha256")
  [ "$notiert" = "$summe_roh" ] || { echo "nicht ok - Begleitdatei meldet $notiert, gemessen $summe_roh"; exit 1; }
fi
echo "ok - Rohbild $ROH $(stat -c %s "$ROH") B sha $summe_roh"

# --- 2) Vorlaufkopf davor setzen, Korper bleibt bytegleich
groesse=$(stat -c %s "$ROH")
ziel=$((groesse + VORLAUF))
rm -f "$VOR"
truncate -s "$ziel" "$VOR"
dd if="$ROH" of="$VOR" bs=1048576 seek=1 conv=notrunc status=none
[ "$(stat -c %s "$VOR")" = "$ziel" ] || { echo "nicht ok - Vorlaufbild ist $(stat -c %s "$VOR") B, erwartet $ziel B"; exit 1; }
korper=$(dd if="$VOR" bs=1048576 skip=1 status=none | sha256sum | cut -d' ' -f1)
[ "$korper" = "$summe_roh" ] || { echo "nicht ok - Korper des Vorlaufbilds ist $korper, Rohbild ist $summe_roh"; exit 1; }
summe_vor=$(sha256sum "$VOR" | cut -d' ' -f1)
( cd "$BILD" && sha256sum "${VOR##*/}" > "${VOR##*/}.sha256" )
echo "ok - Vorlaufbild $VOR $(stat -c %s "$VOR") B sha $summe_vor (Kopf 1 MiB, Korper bytegleich)"

# --- 3) Sparse, mit der Ruecklese-Probe des Bauers selbst
python3 "$OM/baue-sparse.py" "$VOR" "$SPARSE" || { echo "nicht ok - baue-sparse.py bricht ab"; exit 1; }
summe_sparse=$(sha256sum "$SPARSE" | cut -d' ' -f1)
( cd "$BILD" && sha256sum "${SPARSE##*/}" > "${SPARSE##*/}.sha256" )
echo "ok - Sparse $SPARSE $(stat -c %s "$SPARSE") B sha $summe_sparse"

# --- 4) der mitgeschriebene /init ist die Quelle
cd /tmp
rm -f /init-aus-bild
debugfs -R "dump /init /init-aus-bild" "$ROH" >/dev/null 2>&1
[ -f /init-aus-bild ] || { echo "nicht ok - debugfs gibt /init nicht heraus"; exit 1; }
summe_init=$(sha256sum /init-aus-bild | cut -d' ' -f1)
summe_quelle=$(sha256sum "$QUELLE" | cut -d' ' -f1)
if [ "$summe_init" = "$summe_quelle" ]; then
  echo "ok - /init im Bild = Quelle ($summe_init, $(stat -c %s /init-aus-bild) B)"
else
  echo "nicht ok - /init im Bild ist $summe_init ($(stat -c %s /init-aus-bild) B), Quelle ist $summe_quelle ($(stat -c %s "$QUELLE") B)"
  exit 1
fi
printf 'SHA256  %s  rootfs.ext4\nSHA256  %s  rootfs-vorlauf.ext4\nSHA256  %s  rootfs-vorlauf.sparse.img\nSHA256  %s  /init im Bild == Quelle\n' \
  "$summe_roh" "$summe_vor" "$summe_sparse" "$summe_init"
