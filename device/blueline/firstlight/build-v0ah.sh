#!/bin/sh
# v0ah: Umbau von v0ag. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund (gemessen 2026-11-02, 17:0x): v0ag findet userdata und will mounten, aber
# ABOOT legt seinen GPT-Bereich bei jedem Start wieder hin — der Kopf liegt bei
# 4096, die Saetze ab 8192, und genau da will ext4 seine Gruppenbeschreiber lesen.
# Darum traegt das Bild jetzt 1 MiB Vorlauf und der Mount bekommt offset=1024.
# (Ursprung 15:31: M1.5 — die Wurzel soll von der
# userdata-Partition kommen, nicht mehr nur aus der Ramdisk. Vorerst belegt:
# die Partition traegt kein Dateisystem und keine Nutzerdaten (Superblock null,
# mount -o ro meldet 'wrong fs type', entsperrt). Das Bild mit Vorlauf (1 MiB + 1 GiB) mit Alpine
# arm64 minirootfs und eigener Wurzel-Init liegt in images/userdata-alpine/,
# rootfs-vorlauf.sparse.img — sha256 in der Begleitdatei, gemessen vor jedem Write.
# sha256 in der Begleitdatei, gemessen vor jedem Write.
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle),
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh, Module und Elternordner
# ein zweites Mal aus dem ausgelieferten Bild heraus, und die v0ag-Zeilen selbst.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ag/new.cpio" ] || { echo "v0ag-Archiv fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ag/firstlight.img" ] || { echo "v0ag-Bild fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0ah"
docker run --rm \
  -v "$IMGD/fl-v0ag":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0ah":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0ah-umbau.py /q/new.cpio /r/new.cpio
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
# Dieselbe Pruefung ein zweites Mal, auf dem Archiv, das wirklich im Bild steckt.
python3 -c "
import gzip,struct,sys,stat
sys.path.insert(0,\"/om\")
import newc
d=open(\"/r/firstlight.img\",\"rb\").read(); page=4096
ks=struct.unpack_from(\"<I\",d,8)[0]; rs=struct.unpack_from(\"<I\",d,16)[0]
rd=page+((ks+page-1)//page)*page
ent=gzip.decompress(d[rd:rd+rs])
open(\"/r/aus-bild.cpio\",\"wb\").write(ent)
es=newc.read_cpio(\"/r/aus-bild.cpio\")
init=next(e[\"content\"].decode() for e in es if e[\"name\"]==\"init\")
namen={e[\"name\"] for e in es}|{e[\"name\"][2:] for e in es}
fehl=[e[\"name\"] for e in es if e[\"name\"]!=\"TRAILER!!!\" and not stat.S_ISDIR(e[\"meta\"][\"mode\"]) and \"/\" in e[\"name\"] and e[\"name\"].rsplit(\"/\",1)[0] not in namen]
ko=[e for e in es if e[\"name\"].endswith(\".ko\")]
print(\"Bild-Ramdisk: %d Eintraege, %d Module, Dateien ohne Elternordner: %d\" % (len(es),len(ko),len(fehl)))
assert len(ko)==6 and not fehl, \"das ausgelieferte Bild verliert Module\"
assert \"Halteschleife\" in init, \"die Halteschleife ist im ausgelieferten Bild nicht da\"
assert \"first-light v0ah\" in init, \"der Panel-Titel ist nicht umgestellt\"
assert \"userdata rw\" in init and \"switch_root /ud /init\" in init, \"v0ag fehlt im ausgelieferten Bild\"
assert \"UDSTART=16547840\" in init, \"die Sektorzahl der Suche fehlt\"
assert \"offset=1024\" in init, \"der Vorlauf-Mount fehlt\"
assert \"sbin/switch_root\" in namen or \"switch_root\" in namen, \"switch_root fehlt im Bild\"
q=chr(39)
blind=[]
for z in init.splitlines():
    if z.startswith(\"mark \"+q):
        erster=z[5:].split(q)[0]
        if (chr(36)+chr(40)) in erster:
            blind.append(z)
print(\"Marks mit Messung in einfachen Anfuehrungszeichen: %d\" % len(blind))
assert not blind, \"es gibt immer noch blinde Marks\"
"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0ah fertig: $IMGD/fl-v0ah/firstlight.img"
