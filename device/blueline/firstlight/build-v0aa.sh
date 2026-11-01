#!/bin/sh
# v0aa: Umbau von v0z, Ziel boot_a. Bauen im Container, wie alle Bilder hier.
#
# Grund, gemessen (2026-11-01): das geladene v0z-endet in einem Endlosparken
# (while :; do sleep 60; done) und wird nie fertig; der Lesekanal logflush
# (Beweislast nach 63 MiB auf boot_a, seek=504) lief darum nur einmal fraeuh
# und nie am Ende. 'fastboot fetch' kann das Geraet nicht (gemessen), also
# liest die Referenz boot_a spaeter ueber Telnet. Der Selbst-Rueckweg
# reboot(2) RESTART2 'bootloader' ist an der laufenden Referenz belegt
# (Fastboot in 7 s, kein Retry verbraucht); busybox-'reboot bootloader'
# kann das nicht, und nacktes 'reboot'liess das Geraet 16:38 ganz verschwinden.
# boot_b + dtbo_b (Referenz + Factory-dtbo) bleibt der Rettungsweg und wird
# von diesem Bild nirgends geschrieben.
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle),
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh (sh -n und bash -n auf
# die wirklich herausgeloeste Init); der Umbau selbst prueft Titel,
# Schleifen-Differenz, restart2-Round-Trip und Modulbestand.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0z/firstlight.img" ] || { echo "v0z-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0z/new.cpio" ] || { echo "v0z-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0aa"
docker run --rm \
  -v "$IMGD/fl-v0z":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0aa":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0aa-umbau.py /q/new.cpio /r/new.cpio
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
echo "bau v0aa fertig: $IMGD/fl-v0aa/firstlight.img"
