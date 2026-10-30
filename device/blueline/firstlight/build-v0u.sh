#!/bin/sh
# v0u: v0ts Bild, Binden ist messbar, blinde Lesungen raus (patch-v0u.py).
#
# Warum: v0t meldet 'state=not attached' am Controller und eine leere
# gebunden=-Zeile - ohne Beweis, ob das Binden durchkam. Ausserdem lesen drei
# Zeilen den Knoten bDeviceState, den dieser Kernel nicht hat (im v0t-Bild 4 mal
# in 3 Zeilen, gemessen): ein leeres Ausgabefeld ist dann Dunkelheit, kein Wert.
#
# Pruefungen nach dem Bauen, alle am FERTIGEN Bild: verify-v0q.py (28 Punkte,
# Produktzahl aus dem Panel-Titel), verify-v0u.py (eigene Beweismale, inklusive
# der Abwesenheit von bDeviceState), bash -n auf die herausgeloeste Init. Der
# Trockenlauf (patch-v0u.py direkt) war vorher durchgelaufen; die
# POSIX-Syntaxpruefung in der Box auch.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
[ -f "$IMGD/fl-v0t/firstlight.img" ] || { echo "v0t-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0t/new.cpio" ] || { echo "v0t-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0u"
docker run --rm \
  -v "$IMGD/fl-v0t":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0u":/r \
  alpine:edge sh -euc '
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/patch-v0u.py /q/new.cpio /r/new.cpio
chmod 644 /r/new.cpio
python3 /om/kernel-blob-from-image.py /q/firstlight.img /r/kernel-blob
gzip -n -9 -c /r/new.cpio > /r/ramdisk.gz
python3 /om/pack-v0.py \
  --kernel /r/kernel-blob --ramdisk /r/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /r/firstlight.img 2>&1 | tail -2
python3 /om/verify-v0q.py /r/firstlight.img
# Die Beweismale stehen als verify-v0u.py-Datei, nicht als Heredoc: ash (der
# Shell der Box) kennt die bash-Escapeform backslash-quote nicht, und eine
# Markierung mit Dollarzeichen wre dort bei set -u ein Abbruch. Der Heredoc
# unten traegt wieder keine Dollarzeichen, wie im v0s-Rezept.
python3 /om/verify-v0u.py /r/firstlight.img
python3 - <<EXTRACT
import gzip, struct, importlib.util
spec = importlib.util.spec_from_file_location("newc", "/om/newc.py")
newc = importlib.util.module_from_spec(spec); spec.loader.exec_module(newc)
d = open("/r/firstlight.img", "rb").read()
page = 4096
ks = struct.unpack_from("<I", d, 8)[0]
rd = page + ((ks + page - 1) // page) * page
open("/tmp/v0u-in.cpio", "wb").write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
ent = {e["name"]: e for e in newc.read_cpio("/tmp/v0u-in.cpio")}
open("/tmp/init-v0u.sh", "w").write(ent["init"]["content"].decode())
EXTRACT
bash -n /tmp/init-v0u.sh && echo "bash -n: Init syntaxfehlerfrei"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0u fertig: $IMGD/fl-v0u/firstlight.img"
