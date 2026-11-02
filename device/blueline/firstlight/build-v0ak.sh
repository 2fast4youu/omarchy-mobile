#!/bin/sh
# v0ak: Umbau von v0aj. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund (am Geraet gemessen 23:2x): der Loop lag auf den richtigen 1 MiB, aber
# pass 1 der Wache hatte die Partition einzeln unter ro gelassen — ext4 starb an
'I/O error while writing superblock'. v0ak gibt auch die Partition frei., boot_b + dtbo_b bleiben die Referenz.
#
# Grund (gemessen 2026-11-02, 22:5x, arm64-Container, mit DEM mount aus dem
# ausgelieferten Archiv — util-linux 2.41.6): die Einheit von offset= ist BYTE.
# Ein Dateisystem bei 1 MiB im Blockgeraet haelt bei offset=1048576 (ERFOLG), bei
# 1024 und bei 2048 kommt 'bad superblock'. v0aj hatte offset=1024 gesetzt und
# damit 1 KiB statt 1 MiB gelesen. Dazu: kein 2>/dev/null mehr an den Mounts, der
# Fehlerwortlaut geht in die Marke.
#
# Ursprung (17:1x): v0ag findet userdata und will mounten, aber die Partition
# liefert bei 4096 'EFI PART' statt der Gruppenbeschreiber. Ob das ABOOT bei jedem
# Start so hinlegt oder der erste Write (fastboots eigene Umrechnung, die Locher
# liess) den alten Satz dort liesz, entscheidet die Marker-Messung
# (images/userdata-alpine/marker-4mib.sparse.img). Bis dahin bleibt der Vorlauf.
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
# ein zweites Mal aus dem ausgelieferten Bild heraus, und die v0aj-Zeilen selbst.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0aj/new.cpio" ] || { echo "v0aj-Archiv fehlt"; exit 1; }
[ -f "$IMGD/fl-v0aj/firstlight.img" ] || { echo "v0aj-Bild fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0ak"
docker run --rm \
  -v "$IMGD/fl-v0aj":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0ak":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0ak-umbau.py /q/new.cpio /r/new.cpio
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
assert \"first-light v0ak\" in init, \"der Panel-Titel ist nicht umgestellt\"
assert \"userdata rw\" in init and \"switch_root /ud /init\" in init, \"v0aj fehlt im ausgelieferten Bild\"
assert \"UDSTART=16547840\" in init, \"die Sektorzahl der Suche fehlt\"
assert \"offset=1048576\" in init, \"der Vorlauf-Mount fehlt\"
assert \"v0ak freigabe\" in init, \"die Partitionsfreigabe fehlt im ausgelieferten Bild\"
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
echo "bau v0ak fertig: $IMGD/fl-v0ak/firstlight.img"
