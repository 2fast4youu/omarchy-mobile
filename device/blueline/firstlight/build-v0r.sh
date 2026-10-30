#!/bin/sh
# v0r: v0q's Bild, Init um zwei Stuecke geaendert (patch-v0r.py), sonst nichts.
#
# 1. UDC-Wartesleife (30 s) statt Einmal-Lesen — das Orakel zeigt die Referenz
#    erst bei 1,708 s Kernelzeit am Controller lesen (dmesg: HOST-MAC-Bindung
#    1,734 s). V0q las einmal und verwarf das Gadget fuer den ganzen Boot.
# 2. Debug-Shell (busybox telnetd -l /bin/sh, Port 23) — die Referenz ist nur
#    messbar, weil sie eine verkauft.
#
# Pruefungen nach dem Bauen, alle am FERTIGEN Bild: verify-v0q.py (28 Punkte,
# Modulpfad + Referenz-Gadgetblock mit Zeilenanfang-Ankern), dann die zwei
# neuen Blöcke, dann bash -n auf die herausgelöste Init.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
[ -f "$IMGD/fl-v0q/firstlight.img" ] || { echo "v0q-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0q/new.cpio" ] || { echo "v0q-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0r"
docker run --rm \
  -v "$IMGD/fl-v0q":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0r":/r \
  alpine:edge sh -euc '
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/patch-v0r.py /q/new.cpio /r/new.cpio
chmod 644 /r/new.cpio
python3 /om/kernel-blob-from-image.py /q/firstlight.img /r/kernel-blob
gzip -n -9 -c /r/new.cpio > /r/ramdisk.gz
python3 /om/pack-v0.py \
  --kernel /r/kernel-blob --ramdisk /r/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /r/firstlight.img 2>&1 | tail -2
python3 /om/verify-v0q.py /r/firstlight.img
python3 /om/verify-v0r.py /r/firstlight.img
# Der Heredoc traegt keine Dollarzeichen, ash expandiert darin nichts; der
# Rest steht als verify-v0r.py-Datei (siehe dessen Kopf).
python3 - <<EXTRACT
import gzip, importlib.util, struct, os
spec = importlib.util.spec_from_file_location("newc", "/om/newc.py")
newc = importlib.util.module_from_spec(spec); spec.loader.exec_module(newc)
d = open("/r/firstlight.img","rb").read()
page = 4096
ks = struct.unpack_from("<I", d, 8)[0]
rd = page + ((ks + page - 1)//page)*page
open("/tmp/v0r-in.cpio","wb").write(gzip.decompress(d[rd:rd+struct.unpack_from("<I", d, 16)[0]]))
ent = {e["name"]: e for e in newc.read_cpio("/tmp/v0r-in.cpio")}
open("/tmp/init-v0r.sh","w").write(ent["init"]["content"].decode())
EXTRACT
bash -n /tmp/init-v0r.sh && echo "bash -n: Init syntaxfehlerfrei"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0r fertig: $IMGD/fl-v0r/firstlight.img"
