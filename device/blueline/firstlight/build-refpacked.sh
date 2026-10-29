#!/bin/sh
# Bild A: die Bisektionsstufe von der guten Seite.
#
# Inhalt 1:1 aus der Distro-Referenz (Kernel+DTB-Blob, zstd-Ramdisk, eingebettete
# cmdline), gepackt ausschliesslich mit unserem pack-v0.py. Wenn A am Bus
# erscheint (Gerät nach ~16 s, NCM nach ~21 s, Telnet 23 = Debug-Shell), ist das
# Packing unschuldig und v0r (eigene Init + Warteschleife + Shell) ist die einzige
# verbleibende Veraenderung. Wenn A schweigt, ist es unser Header - trotz des
# Nachweises, dass page_size@40=0 und die Sektionslage dem Referenzbild gleichen.
#
# Bewiesen wird das nach dem Bauen, nicht am Telefon: Kernel- und Ramdisk-Sektion
# Byte fuer Byte gegen das Referenzbild, Headerfelder Feld fuer Feld aufgelistet.
# Der id[]- und name[]-Vergleich steht offen, weil fastboot beim Flashen den
# Super-Identifier selbst setzt; andernfalls ist die Ausgabe als unvollstaendig
# zu lesen.
set -eu
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
OUT=/private/tmp/fl-refpacked
mkdir -p "$OUT"
docker run --rm \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  -v "$FL":/om:ro \
  -v "$OUT":/a \
  alpine:edge sh -euc '
apk add --no-cache python3 zstd diffutils >/dev/null 2>&1
python3 /om/unpack-bootimg.py /ref/boot.img /a/extract
# Die eingebettete cmdline laeuft bis zum NUL hinter cmdline@64; die
# Kopfstruktur der v2 kennt kein eigenes Groessenfeld, also so:
CMDLINE=$(python3 -c "
d=open(\"/ref/boot.img\",\"rb\").read()
print(d[64:576].split(b\"\0\")[0].decode())")
echo "cmdline (${#CMDLINE} Zeichen): $CMDLINE"
python3 /om/pack-v0.py \
  --kernel /a/extract/kernel --ramdisk /a/extract/ramdisk \
  --cmdline "$CMDLINE" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /a/firstlight.img
python3 /om/unpack-bootimg.py /a/firstlight.img
python3 - <<PY
import struct
a = open("/a/firstlight.img","rb").read()
r = open("/ref/boot.img","rb").read()
def sec(d, base, size):  # Sektionsanfang, Laenge
    return d[base:base+size]
# Koepfe Feld fuer Feld
names = [("kernel_size",8),("kernel_addr",12),("ramdisk_size",16),("ramdisk_addr",20),
         ("second_size",24),("tags_size",32),("tags_addr",36),("page_size",40),("os_version",44)]
same, diff = [], []
for n, off in names:
    va, vr = struct.unpack_from("<I",a,off)[0], struct.unpack_from("<I",r,off)[0]
    (same if va==vr else diff).append("%s: A=%d ref=%d" % (n, va, vr))
print("Kopf gleich:", ", ".join(same))
print("Kopf unterschiedlich:", "; ".join(diff) or "keins")
ca = a[64:576].split(b"\0")[0]; cr = r[64:576].split(b"\0")[0]
assert ca == cr, "cmdline nicht identisch"
print("cmdline identisch (%d Zeichen)" % len(ca))
# Sektionen: Kernel exakt kernel_size Bytes ab dem jeweiligen Sektionsanfang
ka = sec(a, 4096, struct.unpack_from("<I",a,8)[0])
kr = sec(r, 4096, struct.unpack_from("<I",r,8)[0])
assert ka == kr, "Kernel-Sektion (inkl. DTB) nicht bytegleich"
print("kernel+dtb bytegleich: %d Bytes" % len(ka))
rsa, rsr = struct.unpack_from("<I",a,16)[0], struct.unpack_from("<I",r,16)[0]
ra = sec(a, 4096 + -(-struct.unpack_from("<I",a,8)[0]//4096)*4096, rsa)
rr = sec(r, 16158720, rsr)
assert ra == rr, "Ramdisk-Sektion nicht bytegleich"
print("ramdisk bytegleich: %d Bytes" % len(ra))
print("DATEIEN A: firstlight.img %d B, Referenz %d B" % (len(a), len(r)))
PY
sha256sum /a/firstlight.img'
echo "bau A fertig: $OUT/firstlight.img"
