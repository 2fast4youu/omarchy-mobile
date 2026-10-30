#!/usr/bin/env python3
"""v0s: v0r's Bild, Init um drei Stuecke geaendert. Kein anderes Bild als input.

Ausgangslage (gemessen, firstlight/evidence/v0r-null-enumeration-2026-10-30.txt):
v0r laeuft — Panel-Titel und Herzschlag sind um 16:2x auf dem Display gelesen —
aber an KEINEM Bus: 0 Beobachtungen in 302 s, kein fastboot, 0 "Pixel 3" in
ioreg, ping 100 % Verlust, Port 23 zu. Der Fehler sitzt damit im USB-Weg zum
Host, nicht im Init-Pfad bis zur Gadget-Zeile. Das ist die erste Boot-Runde, in
der das Panel unser einziger Beweisungskanal ist, denn die Referenz schrieb ihre
Ausgabe auf ttyMSM0, einen UART ohne Kabel (evidence/startparameter-vergleich).

Drei Aenderungen, jede einzeln begruendet:

1. idProduct 0xD001 -> 0xD002. Eine neue Zahl am Bus ist nur mit diesem Bild zu
   sehen. Ohne sie waere jede spaetere Enumeration mehrdeutig: 0xD001 hat in
   diesem Aufbau schon v0q getragen, und ein Descriptor eines frueheren Bootes
   am selben Kabel ist von einem neuen nicht zu unterscheiden.
2. Zwangs-Nachbinden alle 20 s, dreissig Runden. v0r bindet genau einmal (Zeile
   211 des Inits). Ein einmaliges Binden nach einem Tasten-Reset kann eine
   Verabredung auf der CC-Leitung erwischen, die der Host nie beantwortet; ein
   erneutes Binden ist ein frischer Connect-Event, den der Host neu verhandeln
   muss. Der Weg ist ungetestet, deshalb schreibt jede Runde ihr Ergebnis ins
   Bild: UDC-Knoten, interface-Liste, und — entscheidend — bDeviceState. Steht
   dort "configured", hat der Host uns angesprochen, und die Frage ist nur noch,
   warum kein Netz da ist. Steht dort "not-addressed", hoert der Host nach dem
   Connect-Event auf, und die Suche gehoert an die koerperliche Ebene (Kabel, Rolle,
   VBUS), nicht an unser configfs.
3. bDeviceState in den Herzschlag (Zeile 63–76 des Inits), damit dieselbe Groesse
   auch ohne das Nachbinden alle 20 s auf dem Panel steht.

Pruefung nach dem Schreiben: alle vier Anker genau einmal, Klammerbalance nur um
die belegten Schleifen gewachsen, Archiv rundgelesen, init ausfuehrbar, Module
vollstaendig, kein v0r-Rest im Text.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

PANEL_OLD = "echo 'Omarchy Mobile first-light v0r - RAM only, UDC-Warteschleife + Debug-Shell'"
PANEL_NEW = "echo 'Omarchy Mobile first-light v0s - RAM only, Panel-Beweis + Nachbind alle 20s'"

PRODUCT_OLD = 'echo 0xD001 > "$CONFIGFS/g1/idProduct"'
PRODUCT_NEW = 'echo 0xD002 > "$CONFIGFS/g1/idProduct"   # neue Zahl: nur dieses Bild tragt sie'

REBIND_ANKER = "mark 'debug shell armed'\n"
REBIND_NEU = """mark 'debug shell armed'

# --- Zwangs-Nachbinden (v0s) -------------------------------------------------
# v0r bindet den Controller genau einmal an. Nach einem Tasten-Reset kann das
# Gadget am configfs haengen, ohne dass der Host je einen Connect-Event
# beantwortet; ein erneutes Binden ist ein frischer Event, an dem sich Host und
# Controller neu verhandeln muessen. Ungetestet, also wird jede Runde
# aufgeschrieben: das Ergebnis ist die Messung, nicht das Nachbinden selbst.
(
    rb=0
    while [ "$rb" -lt 30 ]; do
        sleep 20
        rb=$((rb + 1))
        for g in /sys/kernel/config/usb_gadget/*; do
            [ -e "$g/UDC" ] || continue
            u=${udc_cached:-$(ls /sys/class/udc 2>/dev/null | head -1)}
            [ -n "$u" ] || continue
            echo none > "$g/UDC" 2>/dev/null
            sleep 1
            echo "$u" > "$g/UDC" 2>/dev/null
            echo "omamobile-blueline: nachbinden $rb: UDC steht auf $(cat "$g/UDC" 2>/dev/null), state=$(cat "$g/udc/$u/bDeviceState" 2>/dev/null), interfaces=$(ls /sys/class/net 2>/dev/null | tr '\\n' ' ')" > /dev/kmsg
        done
    done
) &
"""

HERZ_OLD = '              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"'
HERZ_NEU = '''              echo "controller-state=$(cat /sys/class/udc/*/bDeviceState 2>/dev/null) gadgetordner=$(ls /sys/kernel/config/usb_gadget 2>/dev/null | tr '\\n' ' ')"
              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"'''

# Erlaubtes Delta der do/done-Zaehlung: +2 (Nachbind-Schleife, und ihr
# Unterprozess endet auf dasselbe 'done'; gemessen am ausgelieferten v0r-Archiv
# mit 22 'done'). Anything else means a brace or loop was lost by the patch.
ERLAUBT_DONE = 2


def main() -> int:
    in_cpio, out_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(in_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher = e["content"].decode()
        text = vorher
        for alt, neu in ((PANEL_OLD, PANEL_NEW), (PRODUCT_OLD, PRODUCT_NEW),
                         (REBIND_ANKER, REBIND_NEU), (HERZ_OLD, HERZ_NEU)):
            n = text.count(alt)
            assert n == 1, "Anker %r genau %d mal, erwartet 1" % (alt[:48], n)
            text = text.replace(alt, neu, 1)
        assert text.count("done") == vorher.count("done") + ERLAUBT_DONE, \
            "do/done-Balance veraendert (erlaubt +%d, gemessen +%d)" % (
                ERLAUBT_DONE, text.count("done") - vorher.count("done"))
        assert "0xD001 > " not in text, "altes idProduct noch in einer Zuweisung"
        assert "first-light v0r" not in text, "alter Panel-Titel noch im Text"
        assert text.count("bDeviceState") == 2, \
            "bDeviceState genau 2 mal erwartet (Nachbind-Protokoll, Herzschlag), gemessen %d" % text.count("bDeviceState")
        assert "telnetd -l /bin/sh" in text, "Debug-Shell verloren"
        assert 'while [ "$udc_wort" -lt 60 ]' in text, "UDC-Warteschleife verloren"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    pfad = "/tmp/v0s-r.cpio"
    open(pfad, "wb").write(blob)
    back = {e["name"]: e for e in newc.read_cpio(pfad)}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    for beweisk in (PANEL_NEW, PRODUCT_NEW, "nachbinden $rb", "controller-state="):
        assert beweisk in init, "fehlte im rundgelesenen Archiv: %s" % beweisk[:40]
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    assert len(module) == len([n for n in {e["name"] for e in es}
                               if n.startswith("usr/lib/modules/")]) >= 5, \
        "Module nach round-trip nicht vollstaendig: %d" % len(module)
    open(out_cpio, "wb").write(blob)
    os.chmod(out_cpio, 0o644)
    # init im Dict ist laengst die neue Fassung (die Schleife hat e["content"]
    # gesetzt); die alte Groesse muss aus dem vorherigen Text kommen, sonst
    # druckt diese Zeile zweimal dieselbe Zahl.
    vorher = {e["name"]: e for e in es}["init"] if False else None
    print("patch-v0s: init %d B, %d Zeilen, Module %d, rundgelesen, vier Anker geprueft"
          % (len(init), init.count(chr(10)), len(module)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
