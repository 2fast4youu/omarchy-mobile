#!/bin/sh
# v0v: v0us Bild, plus der weiche Verbindungspflicht am Controller (patch-v0v.py).
#
# Warum, gemessen: v0t meldete 'state=not attached' bei leerem gebunden=-Feld,
# und ein Controller, der nicht verbindet, zeigt dem Host nichts - zwei
# Messlaeufe, 0 Beobachtungen in je 302 s. Am Kernel-Binary (44 498 944 Byte
# entpackt) stehen soft_connect 3 Fundstellen, bDeviceState 0 Fundstellen: der eine Knopf
# existiert, der andere nicht. v0v drueckt den, der existiert, und schreibt
# Rueckgabewert und Zustandswertung in den Herzschlag.
#
# Pruefungen nach dem Bauen, alle am FERTIGEN Bild: verify-v0q.py (28 Punkte,
# Produktzahl aus dem Panel-Titel), verify-v0v.py (eigene Beweismale, inklusive
# der Abwesenheit von bDeviceState), bash -n auf die herausgeloeste Init.
# Trockenlauf und POSIX-Syntaxpruefung waren vor diesem Bau durchgelaufen.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
[ -f "$IMGD/fl-v0u/firstlight.img" ] || { echo "v0u-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0u/new.cpio" ] || { echo "v0u-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0v"
docker run --rm \
  -v "$IMGD/fl-v0u":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0v":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/patch-v0v.py /q/new.cpio /r/new.cpio
# Der Reihenfolge-Pruefung laeuft auf dem patched Archiv, bevor daraus ein
# Bild wird: ein Beweis vor seinem Setzer ist ein Defekt, den kein
# Anwesenheits-Test sieht.
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
# Die Beweismale stehen als verify-v0v.py-Datei, nicht als Heredoc: ash (die
# Shell der Box) kennt die bash-Escapeform backslash-quote nicht, und eine
# Markierung mit Dollarzeichen wre dort bei set -u ein Abbruch. Der Heredoc
# unten traegt wieder keine Dollarzeichen, wie im v0s-Rezept.
python3 /om/verify-v0v.py /r/firstlight.img
python3 - <<EXTRACT
import gzip, struct, importlib.util
spec = importlib.util.spec_from_file_location("newc", "/om/newc.py")
newc = importlib.util.module_from_spec(spec); spec.loader.exec_module(newc)
d = open("/r/firstlight.img", "rb").read()
page = 4096
ks = struct.unpack_from("<I", d, 8)[0]
rd = page + ((ks + page - 1) // page) * page
open("/tmp/v0v-in.cpio", "wb").write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
ent = {e["name"]: e for e in newc.read_cpio("/tmp/v0v-in.cpio")}
open("/tmp/init-v0v.sh", "w").write(ent["init"]["content"].decode())
EXTRACT
bash -n /tmp/init-v0v.sh && echo "bash -n: Init syntaxfehlerfrei"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0v fertig: $IMGD/fl-v0v/firstlight.img"
