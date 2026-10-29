#!/usr/bin/env python3
"""v0r: zwei Aenderungen an v0q's Init, sonst nichts.

1. UDC-Warten statt Einmal-Lesen. Das Orakel (Telefon lief die ganze Zeit,
   firstlight/evidence/) zeigt: die Referenz liest /sys/class/udc erst bei
   1,708 s Kernelzeit, und die configfs-Gadget-Bindung (HOST MAC) erscheint um
   1,734 s im dmesg. V0q's Init (Zeile 150 des Archives) liest einmal, kurz
   nach PID-1-Start, und verwirft das Gadget mit 'No UDC found, skipping gadget
   setup' fuer den ganzen Boot, wenn der dwc3-Controller in diesem Moment noch
   nicht probiert hat. 83 Minuten Bus-Abwesenheit sind damiterklaert, ohne
   dass etwas kaputt sein muss.
2. Debug-Shell auf Port 23. Die Referenz endet im Debug-Shell und verkauft
   ihn ueber telnetd; genau dadurch ist sie messbar. V0q bot dem Host nichts.

Pruefung nach dem Schreiben: beide Ersetzungen genau einmal, Archiv liest
sich zurueck, Init bleibt ausfuehrbar im Archivgrund, Module bleiben stehen.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

UDC_OLD = """    udc=$(ls /sys/class/udc 2>/dev/null | head -1)
    if [ -z "$udc" ]; then
        mark 'No UDC found, skipping gadget setup'
    else
"""

UDC_NEW = """    udc_wort=0
    while [ "$udc_wort" -lt 60 ]; do
        udc=$(ls /sys/class/udc 2>/dev/null | head -1)
        [ -n "$udc" ] && break
        [ "$udc_wort" -eq 0 ] && mark 'udc noch leer - warte auf dwc3 (Referenz bindet bei 1.734 s)'
        udc_wort=$((udc_wort + 1)); sleep 0.5
    done
    if [ -z "$udc" ]; then
        mark 'No UDC found in 30 s, skipping gadget setup'
    else
"""

SHELL_OLD = """mark 'dropbear start'
"""

PANEL_OLD = "'Omarchy Mobile first-light v0h - RAM only, Watchdog-Fuetterer + Pstore'"
PANEL_NEW = "'Omarchy Mobile first-light v0r - RAM only, UDC-Warteschleife + Debug-Shell'"
SHELL_NEW = """# Debug-Shell (v0r): die Referenz ist nur messbar, WEIL sie im Debug-Shell
# endet und den ueber telnetd :23 verkauft. Lauscht auf *:23, auch ohne usb0;
# der Host kommt drauf, sobald NCM erscheint - und wenn nicht, ist wenigstens
# steps.log uber telnet lesbar, sobald es ein Netzwerk gibt.
say 'debug shell: telnetd -l /bin/sh (Port 23, alle Adressen)'
( while :; do telnetd -l /bin/sh; sleep 2; done ) &
mark 'debug shell armed'
"""


def main() -> int:
    in_cpio, out_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(in_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    hit = 0
    for e in es:
        if e["name"] != "init":
            continue
        text = e["content"].decode()
        for old, new in ((UDC_OLD, UDC_NEW), (SHELL_OLD, SHELL_NEW),
                         (PANEL_OLD, PANEL_NEW)):
            n = text.count(old)
            assert n == 1, "Anker %r genau %d mal, erwartet 1" % (old.splitlines()[0][:40], n)
            text = text.replace(old, new, 1)
        # Gegenpruefung der Klammerbalance: die Zahl der if/fi, do/done, else
        # darf nur um die nachweislich eingefuegten Stuecke gewachsen sein.
        def tally(s):
            return (len(s.split("\n else")) - 1, len(s.split("\n" + " " * 12 + "else")) - 1)
        before = tally(e["content"].decode())
        assert text.count('while [ "$udc_wort" -lt 60 ]') == 1
        # erlaubte Deltas: +2 'done' (UDC-Wartesleife, Shell-Nachloop), die
        # if/else-Struktur bleibt, weil die Warteschleife den bestehenden
        # if/else-Zweig nur innen umhängt
        assert text.count("done") == e["content"].decode().count("done") + 2, \
            "do/done-Balance veraendert (erlaubt: +2 fuer die zwei neuen Schleifen)"
        assert text.count("telnetd -l /bin/sh") >= 2
        e["content"] = text.encode()
        hit += 1
    assert hit == 1, "init genau %d mal im Archiv" % hit
    blob = newc.emit(es)
    open("/tmp/r.cpio", "wb").write(blob)
    back = {e["name"]: e for e in newc.read_cpio("/tmp/r.cpio")}
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert 'while [ "$udc_wort" -lt 60 ]' in back["init"]["content"].decode()
    assert "telnetd -l /bin/sh" in back["init"]["content"].decode()
    mods = [n for n in back if n.startswith("usr/lib/modules/")]
    assert len(mods) == len([n for n in {e['name'] for e in es} if n.startswith("usr/lib/modules/")]) >= 5, \
        "Module nach round-trip nicht mehr vollstaendig: %s" % mods
    open(out_cpio, "wb").write(blob)
    os.chmod(out_cpio, 0o644)
    print("patch-v0r: init %d -> %d B, Module %d, rundgelesen, Balance geprueft"
          % (len(es[[e['name'] for e in es].index("init")]["content"]),
             len(back["init"]["content"]), len(mods)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
