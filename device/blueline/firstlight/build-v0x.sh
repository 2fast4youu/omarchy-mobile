#!/bin/sh
# v0x: v0ws Bild, plus die SUCHESpur zum weichen Verbindungsknopf (patch-v0x.py).
#
# Warum, gemessen: v0w drueckte /sys/kernel/debug/usb/$u/soft_connect, ohne den
# Pfad je beobachtet zu haben. Am Kernel-Binary (44 498 944 Byte entpackt) stehen
# soft_connect 3 Fundstellen, und alle drei sind Namen in der Kallsyms-Tafel;
# CONFIG_IKCONFIG=n liefert keine eingebettete Config, also ist die Knoten-
# erstellung zur Laufzeit aus dem Bild nicht beweisbar. Ein Bild, das einen
# nicht nachgewiesenen Knoten drueckt, meldt 'kein Knopf' wie 'Knopf ohne
# Wirkung'. v0x sucht den Knoten im haengten Zaehlkanal, meldet die gefundene
# Zahl und die Pfade im Herzschlag, und drueckt nur, wenn die Datei beschreibbar
# ist (test -w, sein Rueckgabewert scrca= steht in jeder Beweiszeile).
#
# Pruefungen nach dem Bauen, alle am FERTIGEN Bild: verify-v0q.py, verify-v0x.py
# (Reihenfolge: Suche vor Annahme, Test vor beiden Writes, geschlossene
# Double-Quotes), und pruefe-init-syntax.sh (sh -n und bash -n auf die wirklich
# herausgeloeste Init). Der Trockenlauf war vor diesem Bau durchgelaufen.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0w/firstlight.img" ] || { echo "v0w-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0w/new.cpio" ] || { echo "v0w-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0x"
docker run --rm \
  -v "$IMGD/fl-v0w":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0x":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0x-umbau.py /q/new.cpio /r/new.cpio
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
python3 /om/verify-v0x.py /r/firstlight.img
# Syntaxpruefung auf der Init, die WIRKLICH herausgeloest ist. Zwei fruehere
# Laeufe hatten ein ganzes cpio-Archiv als Shell-Skript geprueft und dabei
# /etc/protocols als Fehlerquelle gemeldet.
FL=/om sh /om/pruefe-init-syntax.sh /r/new.cpio
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0x fertig: $IMGD/fl-v0x/firstlight.img"
