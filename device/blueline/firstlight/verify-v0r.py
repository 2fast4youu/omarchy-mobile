#!/usr/bin/env python3
"""Prueft das fertige v0r-Bild, von der Platte aus — nicht den Zwischen-cpio.

Dieses Stueck war zuerst ein Heredoc im Bauskript, und ash ohne Quotes hatte
`$(ls /sys/class/udc ...)` und `$_i` schon wegexpandiert, bevor Python die
Zeile sah ('sh: line 14: _i: parameter not set'). Dasselbe Problem steht als
Warnung ueber build-v0q.py selbst. Als Datei gibt es diese Fehlerklasse nicht.
"""
from __future__ import annotations

import gzip
import importlib.util
import os
import struct
import sys

spec = importlib.util.spec_from_file_location(
    "newc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "newc.py"))
assert spec is not None and spec.loader is not None
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

img = sys.argv[1]
d = open(img, "rb").read()
assert d[:8] == b"ANDROID!", "kein AOSP boot image"
page = 4096
ks = struct.unpack_from("<I", d, 8)[0]
rd = page + ((ks + page - 1) // page) * page
assert d[40:44] == bytes.fromhex("00000000"), "page_size-Feld verstellt"
assert d[rd:rd + 2] == bytes.fromhex("1f8b"), "ramdisk nicht seitenbuendig gzip"
cpio = "/tmp/v0r-pruef.cpio"
open(cpio, "wb").write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
ent = {e["name"]: e for e in newc.read_cpio(cpio)}
assert list(ent)[-1] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
init = ent["init"]["content"].decode()

# 1) die beiden Aenderungen, genau einmal
assert init.count('while [ "$udc_wort" -lt 60 ]') == 1, "UDC-Wartesleife nicht genau einmal"
assert "No UDC found in 30 s" in init, "neue Markierung fehlt"
assert "udc=$(ls /sys/class/udc 2>/dev/null | head -1)" in init, "Leser fehlt (in der Schleife erwartet)"
assert init.count("telnetd -l /bin/sh") >= 2, "Debug-Shell fehlt"
assert "first-light v0r - RAM only, UDC-Warteschleife + Debug-Shell" in init, \
    "Panel-Titel nicht auf v0r gestellt"
# 2) nichts von v0q ist verloren: Module, Warteschleife-Titel nicht vergessen
mods = [n for n in ent if n.startswith("usr/lib/modules/") and n.endswith(".ko")]
assert len(mods) >= 5, "Module nicht mehr vollstaendig: %s" % mods
for probe in ("CONFIGFS=/sys/kernel/config/usb_gadget", "echo 0x18D1 > ", "netfunc=ncm.usb0",
              "functions/acm.GS0", "storage guard pass 1", "omamobile-ufs-rw"):
    assert probe in init, "v0q-Pflichtstueck verschwunden: " + probe
# 3) die Warteschleife zaehlt mit udc_wort, nicht mit _i: der Container-ash
#    lief mit -u und meldete '_i: parameter not set' — auf dem Telefon waere
#    das nicht passiert (Init laeuft ohne -u), aber die Datei belegt es jetzt.
assert init.count('udc_wort="$"') == 0 and "udc_wort=$((udc_wort + 1))" in init
print("v0r-Inhalt geprueft: Warteschleife + Debug-Shell + %d Module, init %d B, Bild %d B"
      % (len(mods), len(init), len(d)))
