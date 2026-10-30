#!/bin/sh
# v0o: der erste echte First Light mit NCM.
#
# Zwei selbstgebaute Blindheiten, beendet:
# 1) Zeile 36 des Inits (v0h-Injektion) war `touch /etc/omamobile-nogadget`
#    — seit v0h lief JEDER Build mit Gadget-Bindung AUS. Das durchgehende
#    NCM-Dunkel auf dem Host war unsere eigene Schaltzeile, nicht das Phone.
# 2) v0n hat gemessen: ABOOT ehrt RESTART2 "bootloader" nicht (471 s, kein
#    Fastboot, Grund lief ins Leere). Der Sofort-Crash-Pfad muss weg —
#    erster Licht soll bleiben, nicht neu starten.
# Sonst unveraendert: Watchdog-Fuetterer, Pstore-Spiegel, Statusblock alle
# 20 s, g1-Gadget (NCM+ACM) an der Referenz-Position, ramoops im DTB.
set -eo pipefail
docker run --rm \
  -v "$IMGD/fl-v0o":/o \
  -v "$IMGD/fl-v0n":/n \
  -v "$IMGD/fl-v0k":/k \
  -v /Users/gregor/hermes-workspace/omarchy-mobile:/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  alpine:edge sh -euc '
apk add --no-cache python3 gzip >/dev/null 2>&1
python3 - /n/new.cpio <<'"'"'PY'"'"'
import sys
sys.path.insert(0, "/om/device/blueline/firstlight")
import newc
es = newc.read_cpio(sys.argv[1])
init = [e for e in es if e["name"] == "init"][0]
t = init["content"].decode("utf-8")
assert t.count("touch /etc/omamobile-nogadget 2>/dev/null\n") == 1, "no-gadget-Schalter nicht gefunden"
t = t.replace("touch /etc/omamobile-nogadget 2>/dev/null\n", "")
start = t.index("        /bin/restart2 bootloader")
stop = t.index("echo c > /proc/sysrq-trigger 2>/dev/null") + len("echo c > /proc/sysrq-trigger 2>/dev/null")
alt = t[start:stop]
neu = (
    "        mark \"restart2-Grund ignoriert (v0n gemessen): erster Licht bleibt\"\n"
    "        /bin/restart2 bootloader 2>/dev/null\n"
    "        mark \"restart2 zurueck: $? — Init laeuft weiter\""
)
t = t[:start] + neu + t[stop:]
init["content"] = t.encode("utf-8")
assert "omamobile-nogadget" not in t.replace("if [ ! -e /etc/omamobile-nogadget ]; then", ""), "Schalter noch im Init"
assert "if [ ! -e /etc/omamobile-nogadget ]; then" in t, "Gadget-Guard fehlt — Gadget wuerde blind eingebunden"
blob = newc.emit(es)
open("/tmp/rt.cpio", "wb").write(blob)
names = [e["name"] for e in newc.read_cpio("/tmp/rt.cpio")]
assert names[-1] == "TRAILER!!!" and "bin/restart2" in names, names[-3:]
open("/o/new.cpio", "wb").write(blob)
print("Archiv %d Eintraege: no-gadget raus, restart2-Zweig ohne Crash" % len(names))
PY
gzip -n -9 -c /o/new.cpio > /o/ramdisk.gz
python3 /om/device/blueline/firstlight/pack-v0.py \
  --kernel /k/kernel-blob --ramdisk /o/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /o/firstlight.img 2>&1 | tail -2
python3 - <<'"'"'PY'"'"'
import sys, gzip, struct
sys.path.insert(0, "/om/device/blueline/firstlight")
import newc
d = open("/o/firstlight.img", "rb").read()
ks = struct.unpack_from("<I", d, 8)[0]
rs = struct.unpack_from("<I", d, 16)[0]
rd = 4096 + ((ks + 4095) // 4096) * 4096
assert d[rd:rd + 3] == b"\x1f\x8b\x08", "ramdisk nicht seitenbuendig"
open("/tmp/f.cpio", "wb").write(gzip.decompress(d[rd:rd + rs]))
nm = {e["name"]: e for e in newc.read_cpio("/tmp/f.cpio")}
init = nm["init"]["content"].decode("utf-8")
assert "touch /etc/omamobile-nogadget" not in init, "Schalter noch im fertigen Bild"
assert "if [ ! -e /etc/omamobile-nogadget ]; then" in init, "Gadget-Guard fehlt"
assert "restart2-Grund ignoriert" in init, "bleiben-Zweig fehlt"
assert "echo c > /proc/sysrq-trigger" not in init.split("restart2 zurueck")[1][:600], "Crash-Pfad noch scharf"
assert "etc/omamobile-panic-probe" not in nm, "Sonde wieder da"
cmd = d[64:576].split(b"\x00")[0].decode()
assert "panic=60" in cmd and "nowatchdog" not in cmd, cmd
print("v0o GEGENGELESEN: Gadget an, restart2 ohne Crash, Sonde aus, watchdog an, %d B" % len(d))
PY
sha256sum /o/firstlight.img
'
