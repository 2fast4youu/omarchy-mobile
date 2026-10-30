#!/bin/sh
# v0t: v0s's Bild, eine Herzschlagzeile mehr (patch-v0t.py), sonst nichts.
#
# Warum: v0s liest nur bDeviceState; belegt ist an einer Datei aber nur der
# Knoten state (evidence/reference-live-vor-v0r-2026-10-30.txt Zeile 46). Ohne
# beide Knoten im Ausgang ist 'die Datei fehlt' von 'der Wert ist anders' nicht
# zu trennen, und das Panel ist unser einziger Kanal.
#
# Pruefungen nach dem Bauen, alle am FERTIGEN Bild: verify-v0q.py (28 Punkte,
# Produktzahl wird aus dem Panel-Titel abgeleitet), dann die v0t-eigenen
# Beweismale, dann bash -n auf die herausgeloeste Init. Der Trockenlauf
# (patch-v0t.py direkt) war vor diesem Bau durchgelaufen.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
[ -f "$IMGD/fl-v0s/firstlight.img" ] || { echo "v0s-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0s/new.cpio" ] || { echo "v0s-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0t"
docker run --rm \
  -v "$IMGD/fl-v0s":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0t":/r \
  alpine:edge sh -euc '
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/patch-v0t.py /q/new.cpio /r/new.cpio
chmod 644 /r/new.cpio
python3 /om/kernel-blob-from-image.py /q/firstlight.img /r/kernel-blob
gzip -n -9 -c /r/new.cpio > /r/ramdisk.gz
python3 /om/pack-v0.py \
  --kernel /r/kernel-blob --ramdisk /r/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /r/firstlight.img 2>&1 | tail -2
python3 /om/verify-v0q.py /r/firstlight.img
# Die Beweismale stehen als verify-v0t.py-Datei, nicht als Heredoc: ash (der
# Shell der Box) kennt die bash-Escapeform backslash-quote nicht, und eine
# Markierung mit Dollarzeichen wre dort bei set -u ein Abbruch. Der Heredoc unten
# traegt wieder keine Dollarzeichen, wie im v0s-Rezept.
python3 /om/verify-v0t.py /r/firstlight.img
python3 - <<EXTRACT
import gzip, struct, importlib.util
spec = importlib.util.spec_from_file_location("newc", "/om/newc.py")
newc = importlib.util.module_from_spec(spec); spec.loader.exec_module(newc)
d = open("/r/firstlight.img", "rb").read()
page = 4096
ks = struct.unpack_from("<I", d, 8)[0]
rd = page + ((ks + page - 1) // page) * page
open("/tmp/v0t-in.cpio", "wb").write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
ent = {e["name"]: e for e in newc.read_cpio("/tmp/v0t-in.cpio")}
open("/tmp/init-v0t.sh", "w").write(ent["init"]["content"].decode())
EXTRACT
bash -n /tmp/init-v0t.sh && echo "bash -n: Init syntaxfehlerfrei"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0t fertig: $IMGD/fl-v0t/firstlight.img"
