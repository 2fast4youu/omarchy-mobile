#!/bin/sh
# v0af: Umbau von v0ae. Ziel boot_a, boot_b + dtbo_b bleiben die Referenz.
#
# Grund (Besprechung 2026-11-01): der Selbst-Rueckweg ist eine Stoppuhr, die die
# Shell weg nimmt — sie war 20:13 und 20:45 jeweils ~340 s offen und wurde dann
# zurueckgeholt, mitten in der Arbeit. v0af kehrt erst nach fuenf Minuten
# Funkstille zurueck; /tmp/halt haelt unbegrenzt, Obergrenze 60 Minuten. Dazu
# die zwei Marks aus v0ad, die in einfachen Anfuehrungszeichen ihren Befehl
# statt ihrer Messung druckten, und der Panel-Titel auf v0af.
#
# Pruefungen am FERTIGEN Bild: verify-v0q.py (Bildhuelle),
# pruefe-binde-reihenfolge.py, pruefe-init-syntax.sh, Module und Elternordner
# ein zweites Mal aus dem ausgelieferten Bild heraus.
set -eu
IMGD=${IMGD:-/Users/gregor/hermes-workspace/images}   # langlebig; /private/tmp raeumt macOS
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
[ -f "$IMGD/fl-v0ae/firstlight.img" ] || { echo "v0ae-Bild fehlt"; exit 1; }
[ -f "$IMGD/fl-v0ae/new.cpio" ] || { echo "v0ae-Archiv fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0af"
docker run --rm \
  -v "$IMGD/fl-v0ae":/q:ro \
  -v "$IMGD/refmod":/m:ro \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$IMGD/fl-v0af":/r \
  alpine:edge sh -euc '
apk update >/dev/null 2>&1
apk add --no-cache python3 bash gzip >/dev/null 2>&1
python3 /om/baue-v0af-umbau.py /q/new.cpio /r/new.cpio
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
# Dieselbe Prüfung ein zweites Mal, auf dem Archiv, das wirklich im Bild steckt.
python3 -c "
import gzip,struct,sys,stat,re
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
assert \"first-light v0af\" in init, \"der Panel-Titel ist nicht umgestellt\"
# Eine Messung in einfachen Anfuehrungszeichen druckt ihren Befehl, nicht ihren
# Wert. gefunden wird eine Zeile, deren erster einfacher String — alles bis zum
# naechsten Hochkomma — schon eine Befehlsersetzung traegt. Absichtliche
# Verkettungen (erstes Hochkomma endet vor der Ersetzung) bleiben erlaubt.
# Keine Hochkommas in diesem Block: sie stünden im einfach zitierten Container-
# skript und wuerden es schliessen (gemessen: syntax error near unexpected token).
q=chr(39)
anfang=\"mark \"+q
blind=[]
for z in init.splitlines():
    if z.startswith(anfang):
        erster=z[len(anfang):].split(q)[0]
        if (chr(36)+chr(40)) in erster:
            blind.append(z)
print(\"Marks mit Messung in einfachen Anfuehrungszeichen: %d\" % len(blind))
for z in blind[:3]:
    print(\"  blind: \" + z[:80])
assert not blind, \"es gibt immer noch blinde Marks\"
"
sha256sum /r/firstlight.img /r/new.cpio'
echo "bau v0af fertig: $IMGD/fl-v0af/firstlight.img"
