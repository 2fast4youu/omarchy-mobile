#!/bin/sh
# v0ae: Umbau von v0ad. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund, gemessen (evidence/boot-a-beutel-2026-11-01.md, der erste Steps.log
# eines eigenen Kernels): das Bild enthaelt sechs Moduldateien, aber die
# Ordnereintraege darunter fehlen (usr/lib ist da, usr/lib/modules und alles
# darunter fehlt). Der Initramfs-Entpacker des Kernels legt fehlende
# Elternordner nicht an, also fehlten im laufenden System alle sechs Module:
# insmod FEHLER 254, kein libcomposite, configfs-Mount fehlgeschlagen,
# 'usb_gadget not found in configfs', und jede Bind-Runde meldete
# "can't create .../g1/UDC: nonexistent directory" — das war der Text am Panel.
#
# v0ae setzt die sieben Ordnereintraege vor die erste .ko-Datei und prueft
# danach fuer JEDEN Dateieintrag, dass sein Elternordner im Archiv steht —
# die Eigenschaft, die der Kernel beim Entpacken verlangt, und die bisher
# keine Pruefung sah (die Modulpruefung fand die Dateien im Archiv, der Kernel
# baute ohne sie).
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle),
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh, dazu der Umbau selbst.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ad/firstlight.img" ] || { echo "v0ad-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ad/new.cpio" ] || { echo "v0ad-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0ae"
docker run --rm \
  -v "$IMGD/fl-v0ad":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0ae":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0ae-umbau.py /q/new.cpio /r/new.cpio
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
FL=/om sh /om/pruefe-init-syntax.sh /r/new.cpio
# Die Entpackbarkeitspruefung laeuft ein zweites Mal, auf dem Archiv, das
# wirklich im Bild steckt: der Umbau prueft seine eigene Liste, hier zaehlt
# nur der Round-trip durch gzip und pack-v0.
python3 -c "
import gzip,struct,sys
sys.path.insert(0,\"/om\")
import newc
d=open(\"/r/firstlight.img\",\"rb\").read(); page=4096
ks=struct.unpack_from(\"<I\",d,8)[0]; rs=struct.unpack_from(\"<I\",d,16)[0]
rd=page+((ks+page-1)//page)*page
ent=gzip.decompress(d[rd:rd+rs])
open(\"/r/aus-bild.cpio\",\"wb\").write(ent)
es=newc.read_cpio(\"/r/aus-bild.cpio\")
import stat
namen={e[\"name\"] for e in es}|{e[\"name\"][2:] for e in es}
fehl=[e[\"name\"] for e in es if e[\"name\"]!=\"TRAILER!!!\" and not stat.S_ISDIR(e[\"meta\"][\"mode\"]) and \"/\" in e[\"name\"] and e[\"name\"].rsplit(\"/\",1)[0] not in namen]
ko=[e for e in es if e[\"name\"].endswith(\".ko\")]
print(\"Bild-Ramdisk: %d Eintraege, %d Module, Dateien ohne Elternordner: %d %s\" % (len(es),len(ko),len(fehl),fehl[:3]))
assert len(ko)==6 and not fehl, \"das ausgelieferte Bild verliert Module\"
"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0ae fertig: $IMGD/fl-v0ae/firstlight.img"
