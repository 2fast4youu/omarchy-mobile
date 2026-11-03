#!/bin/sh
# v0al: Umbau von v0ak. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund (am laufenden v0ak-Boot gemessen, 2026-11-03 15:34, Wurzel #21): der
# switch_root kam bei Uptime 169 s, davon 160 s Warten auf die USB-Runde:
#   [167s] step: warten beendet nach 160s, runde  fertig
#   [169s] step: v0ak uebergabe: switch_root /ud /init
# Der UDC stand ab 7 s auf state=configured; die Runde lief trotzdem achtmal
# 15 s weiter. v0al prueft den Zustand vor dem sleep und bricht ab, wenn der
# Host schon enumeriert hat. Der Fall des spaeten UDC bleibt unveraendert.
#
# Dazu der Schreibfehler derselben Runde: die Zeile "akt=v0z runde ..." war ein
# nacktes Anfuehrungszeichen-Kommando (kein `akt=`), lief als Befehl ins Leere
# und liess jede Rundenzeile mit `step:  |` beginnen. Sie heisst jetzt akt="...".
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle),
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh, Module und Elternordner
# ein zweites Mal aus dem ausgelieferten Bild heraus, und die v0al-Zeilen selbst.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ak/new.cpio" ] || { echo "v0ak-Archiv fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ak/firstlight.img" ] || { echo "v0ak-Bild fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0al"
docker run --rm \
  -v "$IMGD/fl-v0ak":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0al":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0al-umbau.py /q/new.cpio /r/new.cpio
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
assert \"first-light v0al\" in init, \"der Panel-Titel ist nicht umgestellt\"
assert \"userdata rw\" in init and \"switch_root /ud /init\" in init, \"v0ak fehlt im ausgelieferten Bild\"
assert \"UDSTART=16547840\" in init, \"die Sektorzahl der Suche fehlt\"
assert \"offset=1048576\" in init, \"der Vorlauf-Mount fehlt\"
assert \"v0ak freigabe\" in init, \"die Partitionsfreigabe fehlt im ausgelieferten Bild\"
assert init.count(\"v0al runde frueh raus\") == 2, \"der Fruehausstieg steht nicht genau zweimal (Log + kmsg)\"
assert init.count(\"step: v0al runde frueh raus\") == 1, \"die Schritt-Log-Zeile fehlt\"
assert \"state=configured nach \$zs Runde(n)\" in init, \"die Fruehausstieg-Marke nennt die Runde nicht\"
assert \"        akt=\\\"v0al runde\" in init, \"die Rundenzeile schreibt ihren Stand nicht\"
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
echo "bau v0al fertig: $IMGD/fl-v0al/firstlight.img"
