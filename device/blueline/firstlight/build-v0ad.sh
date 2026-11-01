#!/bin/sh
# v0ad: Umbau von v0ac. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund, gemessen (evidence/ro-kausalitaet-2026-11-01.md, 19:40-19:41 am
# laufenden Geraet): unsere eigene storage_guard setzt /dev/sda und jede
# Partition auf read-only; `blockdev --setrw /dev/sda11` allein wirkt nicht —
# die Partition meldet danach weiterhin ro=1, und dd schreibt "Operation not
# permitted", 0 Bytes. Erst als die PLATTE rw war, schrieb dd (rc=0, Marker
# zurueckgelesen). logflush drehte bisher nur die Partition und versteckte den
# Fehlertext hinter 2>/dev/null, therefore hat seit dem ersten Bau dieser
# Guard kein einziges Bild auf boot_a geschrieben.
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle), dazu
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh (sh -n und bash -n auf die
# wirklich herausgeloeste Init); der Umbau selbst prueft Titel, Platten-Fix,
# Gadget-Spionage, Zahlenspur, Round-trip und Modulbestand.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ac/firstlight.img" ] || { echo "v0ac-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ac/new.cpio" ] || { echo "v0ac-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0ad"
docker run --rm \
  -v "$IMGD/fl-v0ac":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0ad":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0ad-umbau.py /q/new.cpio /r/new.cpio
# Der Reihenfolge-Pruefer laeuft auf dem gepatchten Archiv, bevor daraus ein
# Bild wird: ein Beweis vor seinem Setzer ist ein Defekt, den keine
# Anwesenheitspruefung sieht.
python3 /om/pruefe-binde-reihenfolge.py /r/new.cpio
chmod 644 /r/new.cpio
python3 /om/kernel-blob-from-image.py /q/firstlight.img /r/kernel-blob
gzip -n -9 -c /r/new.cpio > /r/ramdisk.gz
python3 /om/pack-v0.py \
  --kernel /r/kernel-blob --ramdisk /r/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /r/firstlight.img 2>&1 | tail -2
python3 /om/verify-v0q.py /r/firstlight.img
# Syntaxpruefung auf der Init, die WIRKLICH herausgeloest ist.
FL=/om sh /om/pruefe-init-syntax.sh /r/new.cpio
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0ad fertig: $IMGD/fl-v0ad/firstlight.img"
