#!/bin/sh
# v0y: das v0x-Bild, zwei Zeilen anders. Gebaut im Container, wie alle Bilder hier.
#
# Grund, gemessen: die Herzschlagzeile von v0x liest
#   modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)
# Die innere Substitution ist unquotiert. Findet sie nichts, bekommt cat kein
# Argument und liest die Standardeingabe - bei PID 1 die Konsole, die Init
# umleitet sie nirgends (gemessen: 0 Fundstellen fuer '< /dev/null', 'exec <',
# '0<'). Pty-Versuch auf dem Rechner: 'VOR dem cat' kommt, 'NACH dem cat' kommt
# in drei Sekunden nicht. Dieselbe Schleife fuettert den Watchdog; steht der
# Druck still, steht die Fuetterung still. Der Hänger feuert ausgerechnet im
# Fehlerfall (kein mode-Knoten, weil dwc3 nie durchgekommen ist) - in dem Zweig,
# den wir ablesen wollen.
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle), verify-v0y.py (Zeilendiff
# gegen v0x: genau zwei verschiedene Zeilen, alle Messfelder und v0x-Beweise
# unveraendert), pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh (sh -n und
# bash -n auf die wirklich herausgeloeste Init).
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0x/firstlight.img" ] || { echo "v0x-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0x/new.cpio" ] || { echo "v0x-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0y"
docker run --rm \
  -v "$IMGD/fl-v0x":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0y":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0y-umbau.py /q/new.cpio /r/new.cpio
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
V0X=/q/firstlight.img python3 /om/verify-v0y.py /r/firstlight.img
# Syntaxpruefung auf der Init, die WIRKLICH herausgeloest ist.
FL=/om sh /om/pruefe-init-syntax.sh /r/new.cpio
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0y fertig: $IMGD/fl-v0y/firstlight.img"
