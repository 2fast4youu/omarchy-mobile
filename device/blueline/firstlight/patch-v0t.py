#!/usr/bin/env python3
"""v0t: v0s's Bild, eine Herzschlagzeile mehr. Sonst nichts.

Warum: v0s liest bDeviceState, belegt ist an einer Datei aber nur der Knoten
`state` (evidence/reference-live-vor-v0r-2026-10-30.txt Zeile 46, Inhalt
`configured`). Ein Herzschlag, der nur bDeviceState zeigt, kann zwei grundlos
verschiedene Sachverhalte nicht trennen: 'diese Datei existiert auf diesem
Kernel nicht' und 'sie existiert und enthält etwas anderes'. Beide brauchen
eine andere Suche, und das Panel ist der einzige Kanal, den wir besitzen.

Die neue Zeile liest deshalb beide Knoten, mit ihrem vollen Pfad im Ausgabe-
text, damit die Datei selbst sagt, welcher Knoten geantwortet hat.

Trockenlauf:  python3 patch-v0t.py <v0s-new.cpio> /tmp/v0t-trocken.cpio
Der Lauf prueft alle drei Anker auf genau einen Treffer, die do/done-Balance
(muelt unveraendert bleiben, es kommt keine Schleife dazu), ASCII, Round-trip,
Ausfuehrbarkeit und die Modulzahl.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

PANEL_OLD = "echo 'Omarchy Mobile first-light v0s - RAM only, Panel-Beweis + Nachbind alle 20s'"
PANEL_NEW = "echo 'Omarchy Mobile first-light v0t - RAM only, Doppel-Knoten-Lesung am Panel'"

DOPPEL_ANKER = '              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"'
DOPPEL_NEU = '''              echo "beide Knoten: state=$(cat /sys/class/udc/*/state 2>/dev/null) bDeviceState=$(cat /sys/class/udc/*/bDeviceState 2>/dev/null) udcdateien=$(ls /sys/class/udc/*/ 2>/dev/null | tr '\\n' ' ')"
              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"'''

REBIND_ANKER = '            echo "omamobile-blueline: nachbinden $rb:'
REBIND_HINWEIS = "nachbinden $rb"

# Zahl der bDeviceState-Erwaehnungen im Init-Text, vorgerechnet und am Bild
# gemessen (nicht aus dem Kopf, ein erster Ansatz mit 3 war falsch): v0s traegt
# genau 2 — Herzschlagzeile 72 und Nachbind-Protokollzeile 347 — und die
# Doppelzeile von v0t nennt beide Knoten, also 2 + 2 = 4. Eine feste Zahl statt
# "beliebig viel", damit eine verlorene Zeile auffaellt; der erste Trockenlauf
# hat mit 'vier gegen erwartet drei' genau diese Rechenart geruegt.
ERWARTET_BDEVICESTATE = 4


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
        for alt, neu in ((PANEL_OLD, PANEL_NEW), (DOPPEL_ANKER, DOPPEL_NEU)):
            n = text.count(alt)
            assert n == 1, "Anker %r genau %d mal, erwartet 1" % (alt[:48], n)
            text = text.replace(alt, neu, 1)
        assert REBIND_HINWEIS in text, "Nachbind-Block aus v0s fehlt"
        assert text.count("done") == vorher.count("done"), \
            "do/done-Balance veraendert (%d gegen %d), v0t fuegt keine Schleife ein" % (
                text.count("done"), vorher.count("done"))
        assert text.count("bDeviceState") == ERWARTET_BDEVICESTATE, \
            "bDeviceState %d mal, erwartet %d" % (text.count("bDeviceState"), ERWARTET_BDEVICESTATE)
        assert "first-light v0s" not in text, "alter Panel-Titel noch im Text"
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        assert len(text) > len(vorher), "Init ist nicht groesser geworden, Zeile fehlt"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    offen = open("/tmp/v0t-r.cpio", "wb"); offen.write(blob); offen.close()
    back = {e["name"]: e for e in newc.read_cpio("/tmp/v0t-r.cpio")}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert "beide Knoten: state=" in init, "Doppelzeile im round-trip verloren"
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    assert len(module) == len([n for n in {e["name"] for e in es}
                               if n.startswith("usr/lib/modules/")]) >= 5, \
        "Module nach round-trip nicht vollstaendig: %d" % len(module)
    offen = open(out_cpio, "wb"); offen.write(blob); offen.close()
    os.chmod(out_cpio, 0o644)
    print("patch-v0t: init %d B, %d Zeilen, Module %d, Doppelzeile drin, Balancegleich"
          % (len(init), init.count(chr(10)), len(module)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
