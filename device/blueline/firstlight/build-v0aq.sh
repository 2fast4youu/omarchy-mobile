#!/bin/sh
# v0ap: Umbau von v0an (Firmware ins Initramfs). Grund im Kopf von baue-v0an-umbau.py (logflush
# schliesst die Platte direkt vor switch_root; die erste WRITE von
# comm switch_root trifft sie zu - vier Bootes, alle bei 29.2 s).
# Pruefungen am fertigen Bild: dieselbe Kette wie bei v0am.

set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ap/new.cpio" ] || { echo "v0ak-Archiv fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ap/firstlight.img" ] || { echo "v0ak-Bild fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0aq"
docker run --rm \
  -v "$IMGD/fl-v0ap":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0aq":/r \
  -v "$HOME/hermes-workspace/firmware":/fw:ro \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0aq-umbau.py /q/new.cpio /r/new.cpio
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
for fw in (\"a630_sqe.fw\",\"a630_gmu.bin\",\"a630_zap.mbn\"):
    assert any(e[\"name\"].endswith(\"lib/firmware/qcom/\"+fw) for e in es), \"Firmware fehlt: \"+fw
assert \"Halteschleife\" in init, \"die Halteschleife ist im ausgelieferten Bild nicht da\"
assert \"first-light v0aq\" in init, \"der Panel-Titel ist nicht umgestellt\"
assert \"userdata rw\" in init and \"switch_root /ud /init\" in init, \"v0ak fehlt im ausgelieferten Bild\"
assert \"UDSTART=16547840\" in init, \"die Sektorzahl der Suche fehlt\"
assert \"offset=1048576\" in init, \"der Vorlauf-Mount fehlt\"
assert \"v0ak freigabe\" in init, \"die Partitionsfreigabe fehlt im ausgelieferten Bild\"
assert init.count(\"v0al runde frueh raus\") == 2, \"der Fruehausstieg steht nicht genau zweimal (Log + kmsg)\"
assert init.count(\"step: v0al runde frueh raus\") == 1, \"die Schritt-Log-Zeile fehlt\"
assert \"state=configured nach \$zs Runde(n)\" in init, \"die Fruehausstieg-Marke nennt die Runde nicht\"
assert \"        akt=\\\"v0al runde\" in init, \"die Rundenzeile schreibt ihren Stand nicht\"
assert init.count(\"> /run/uddev\") == 1, \"die /run-Ausnahme der Wache fehlt\"
assert init.count(\"cat /run/uddev\") == 1, \"die Wache liest /run nicht\"
assert init.count(\"cat /tmp/uddev\") == 1, \"der /tmp-Rueckfall der Wache fehlt\"
assert not any(z.startswith(chr(32)*8+chr(34)+\"akt=\") for z in init.splitlines()), \"die nackte akt=-Zeile steht noch da\"
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
echo "bau v0am fertig: $IMGD/fl-v0an/firstlight.img"
