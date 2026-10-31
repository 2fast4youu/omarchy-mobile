#!/bin/sh
# v0z: das v0y-Bild, eingefuegt statt ersetzt. Bauen im Container, wie alle Bilder hier.
#
# Grund, gemessen (Panel-Ablesung vom 31.10. und Quelltext): der weiche
# Verbindungsknopf ist ein Sysfs-Attribut der UDC-Klasse
# (/sys/class/udc/<udc>/soft_connect, DEVICE_ATTR_WO, drivers/usb/gadget/udc/
# core.c:1784), nicht von debugfs; die Worte sind 'connect' und 'disconnect',
# ohne gebundenes Gadget antwortet der Handler mit -EOPNOTSUPP. Der Herzschlag
# meldete gadgetordner= und gebunden= leer, die Nachbind-Runde fand also nie ein
# Gadget, und die fruehen Marks dazu warener in /run/steps.log, die das Panel
# nie zeigt (es steht nur 'letzter Schritt:' da, eine Zeile, und die kommt aus
# dem dmesg-Block bei 42 s).
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle), verify-v0z.py
# (Zeilendiff gegen v0y: nur der Titel geaendert, der Rest eingefuegt, jede
# vorhandene Messung erhalten), pruefe-binde-reihenfolge.py,
# pruefe-init-syntax.sh (sh -n und bash -n auf die wirklich herausgeloeste Init).
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0y/firstlight.img" ] || { echo "v0y-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0y/new.cpio" ] || { echo "v0y-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0z"
docker run --rm \
  -v "$IMGD/fl-v0y":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0z":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0z-umbau.py /q/new.cpio /r/new.cpio
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
V0Y=/q/firstlight.img python3 /om/verify-v0z.py /r/firstlight.img
# Syntaxpruefung auf der Init, die WIRKLICH herausgeloest ist.
FL=/om sh /om/pruefe-init-syntax.sh /r/new.cpio
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0z fertig: $IMGD/fl-v0z/firstlight.img"
