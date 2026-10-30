#!/bin/sh
# v0p: die Gadget-Sequenz 1:1 aus postmarketos-initramfs (root/init_functions.sh:
# setup_usb_network_configfs + setup_usb_acm_configfs + setup_usb_configfs_udc)
# statt unseres Eigenbaus.
#
# Was der Vergleich mit der Referenz (pmOS-Image, bootet bis zum Login) gegen
# unseren geflashten Block zeigt — drei Abweichungen, jede allein genug damit am
# Host kein NCM-Interface erscheint:
#   * Mountlage und Name: Referenz haengt configfs unter /sys/kernel/config
#     (dirname von $CONFIGFS) und nimmt das Gadget g1. Wir nahmen /config und
#     omamobile.
#   * VID/PID: Referenz 0x18D1/0xD001, wir 0x1d6b/0x0104.
#   * UDC-clear: setup_usb_configfs_udc schreibt erst ein leeres g1/UDC und dann
#     den Controller, im Quelltext gegen write error: Resource busy. Wir haben
#     direkt den Controller geschrieben, und weil alles nach 2>/dev/null ging,
#     waere ein belegter UDC lautlos verloren gewesen.
# NCM und ACM zusammen ist nicht erfunden: so steht es in der Log-Recovery der
# Referenz — Netzwerk mit skip_udc anlegen, ACM anhaengen, dann einmal der UDC.
#
# Kompression braucht kein modprobe: USB_LIBCOMPOSITE, USB_CONFIGFS*, USB_F_NCM,
# USB_F_ACM und USB_DWC3* sind im Kernel =y und das Ramdisk hat keine .ko.
# Geglaubt wird auch hier nur dem Zuruecklesen aus dem fertigen Bild.
set -eo pipefail
[ -f "$IMGD/fl-v0o/new.cpio" ] || { echo "v0o fehlt"; exit 1; }
[ -f "$IMGD/fl-v0k/kernel-blob" ] || { echo "Kernel-Blob fehlt"; exit 1; }
mkdir -p "$IMGD/fl-v0p"
docker run --rm \
  -v "$IMGD/fl-v0o":/p:ro \
  -v "$IMGD/fl-v0k":/k:ro \
  -v "$IMGD/fl-v0p":/q \
  -v /Users/gregor/hermes-workspace/omarchy-mobile:/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  alpine:edge sh -euc '
apk add --no-cache python3 gzip >/dev/null 2>&1
cp /p/new.cpio /q/new.cpio
chmod 644 /q/new.cpio
python3 - <<'"'"'PY'"'"'
import sys
sys.path.insert(0, "/om/device/blueline/firstlight")
import newc

GADGET = open("/om/device/blueline/firstlight/gadget-reference.sh").read()

es = newc.read_cpio("/q/new.cpio")
init = [e for e in es if e["name"] == "init"][0]
t = init["content"].decode("utf-8")

start = t.index("mark \x27usb gadget setup\x27")
end = t.index("mark \x27gadget bind skipped (--no-gadget instrument)\x27")
end = t.index("\nfi\n", end) + len("\nfi\n")
alt = t[start:end]
assert t.count(alt) == 1, "Span nicht eindeutig"
t = t[:start] + GADGET + t[end:]

# Panel-Statusblock auf die Referenzlage umhaengen
# Panelblock: die vier Zeilen, ein Foto soll den USB-Stand allein entscheiden.
STATUS = open("/om/device/blueline/firstlight/panel-status.sh").read().rstrip("\n")
zeilen = t.split("\n")
treffer = [j for j, z in enumerate(zeilen) if "gebunden=$(cat" in z or "letzter Schritt: $(tail" in z]
assert len(treffer) == 2 and treffer[1] == treffer[0] + 1, "Panelblock-Zeilen nicht zusammenhingend: %r" % treffer
zeilen[treffer[0]:treffer[1] + 1] = STATUS.split("\n")
t = "\n".join(zeilen)
assert "pid1=$(cat /proc/1/comm" in t and "dwc3 rolle=" in t, "Panelblock unvollstaendig"
# Panel-Text rein ASCII: ein Gedankenstrich aus der Baurezeptur landet als
# UTF-8-Mehrbytekette auf einem Panel ohne UTF-Konsole und wird dort Müll.
t = t.replace("\u2014", "-")
assert t.isascii(), "Init hat Nicht-ASCII-Bytes fuer das Panel"

# der alte Zweit-Mount unter /config: eine configfs-Lage, die Referenz-Lage
t = t.replace("mkdir -p /dev/pts /sys/fs/pstore /config", "mkdir -p /dev/pts /sys/fs/pstore")
t = t.replace("mount -t configfs configfs /config || mark \x27mount configfs FAILED\x27\n", "")
assert "configfs /config" not in t, "zweiter configfs-Mount bleibt stehen"
for must in ("/sys/kernel/config/usb_gadget", "echo 0x18D1", "echo 0xD001",
             "ncm.usb0", "rndis.usb0", "acm.GS0", "172.16.42.1"):
    assert must in t, "fehlt im Init: " + must
bad = [l.strip() for l in t.splitlines() if "cat /config/usb_gadget" in l or l.strip().startswith("g=/config/")]
assert not bad, "alte Gadget-Lage noch im Init: " + repr(bad[:2])
init["content"] = t.encode("utf-8")

blob = newc.emit(es)
open("/tmp/rt.cpio", "wb").write(blob)
names = [e["name"] for e in newc.read_cpio("/tmp/rt.cpio")]
assert names[-1] == "TRAILER!!!" and "bin/restart2" in names, names[-3:]
open("/q/new.cpio", "wb").write(blob)
print("Archiv %d Eintraege, Gadget-Block %d -> %d Zeichen" % (len(names), len(alt), len(GADGET)))
PY
gzip -n -9 -c /q/new.cpio > /q/ramdisk.gz
python3 /om/device/blueline/firstlight/pack-v0.py \
  --kernel /k/kernel-blob --ramdisk /q/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /q/firstlight.img 2>&1 | tail -2
python3 - <<'"'"'PY'"'"'
import sys, gzip, struct
sys.path.insert(0, "/om/device/blueline/firstlight")
import newc
d = open("/q/firstlight.img", "rb").read()
ks = struct.unpack_from("<I", d, 8)[0]; rs = struct.unpack_from("<I", d, 16)[0]
rd = 4096 + ((ks + 4095) // 4096) * 4096
assert d[40:44] == b"\x00\x00\x00\x00", "page_size-Feld verstellt"
assert d[rd:rd + 3][:2] == b"\x1f\x8b", "ramdisk nicht seitenbuendig gzip"
open("/tmp/f.cpio", "wb").write(gzip.decompress(d[rd:rd + rs]))
nm = {e["name"]: e for e in newc.read_cpio("/tmp/f.cpio")}
init = nm["init"]["content"].decode("utf-8")
ref = open("/om/device/blueline/firstlight/gadget-reference.sh").read()
assert ref in init, "Referenz-Block nicht unveraendert im fertigen Bild"
for probe, why in (("/sys/kernel/config/usb_gadget", "Referenz-Mountlage"),
                   ("g1", "Referenz-Gadgetname"),
                   ("echo 0x18D1", "Referenz-VID"),
                   ("echo 0xD001", "Referenz-PID"),
                   ("acm.GS0", "ACM-Konsole"),
                   ("172.16.42.1", "HOST_IP der Referenz")):
    assert probe in init, "fehlt im fertigen Bild: " + why
assert "cat /config/usb_gadget" not in init and "g=/config/" not in init, "alte Gadget-Lage im fertigen Bild"
assert "touch /etc/omamobile-nogadget" not in init, "no-gadget-Schalter"
assert "etc/omamobile-panic-probe" not in nm, "Sonde"
assert "bin/restart2" in nm, "restart2"
cmd = d[64:576].split(b"\x00")[0].decode()
assert "panic=60" in cmd and "nowatchdog" not in cmd, cmd
print("v0p GEGENGELESEN: Referenz-Gadgetsequenz unveraendert an Bord, %d B Bild, %d B Init" % (len(d), len(init)))
PY
sha256sum /q/firstlight.img
'
