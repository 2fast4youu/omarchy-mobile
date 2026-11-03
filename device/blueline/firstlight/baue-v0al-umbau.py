#!/usr/bin/env python3
r"""v0ak -> v0al: die USB-Runde endet, sobald der Host das Gadget hat.

Gemessen am laufenden v0ak-Boot (2026-11-03 15:34, Wurzel #21, /run/steps.log):

    [167s] step: warten beendet nach 160s, runde  fertig
    [168s] step: v0ak freigabe: platte rc=0 partition rc=0 ro=0
    [169s] step: v0ak uebergabe: switch_root /ud /init

Der Zustand stand ab dem ersten Durchlauf auf `state=configured` (der Host hatte
enumeriert), die Runde lief trotzdem acht Runden zu je 15 s weiter, und der
Hauptfluss wartete per `kill -0` auf sie. 160 der 169 s bis `switch_root` sind
damit Wartezeit, die der Zweck der Runde nicht braucht.

Zwei Aenderungen:

1) Die Runde prueft den Zustand VOR ihrem `sleep 15` und bricht ab, wenn er
   schon `configured` ist. Der Fall, fuer den sie gebaut wurde (UDC kommt
   spaeter als die 30-s-Wartezeit der Anlage), bleibt unveraendert: ohne
   Bindung schlaeft sie weiter und legt an wie bisher.

2) Die Zeile, die den Rundenstand nach /run/steps.log schreiben sollte, war ein
   nacktes Anfuehrungszeichen-Kommando (`"akt=..."`) und lief als Befehl ins
   Leere. Deshalb begann jede Rundenzeile in der Log mit `step:  |`. Sie heisst
   jetzt `akt="..."`; der Fehler ist an der laufenden Kiste gemessen (leerer
   Praefix vor jedem `| g1 war da`).
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 697          # im v0ak-Archiv gemessen (init 36159 B), nicht im Kopf

ALT_AKT = ('        "akt=v0z runde $zs bei $(cut -d. -f1 /proc/uptime)s: '
           'debugfsrc=$dfrc configfsrc=$cfrc udc=${udc:-KEINER}"')

NEU_AKT = ('        akt="v0al runde $zs bei $(cut -d. -f1 /proc/uptime)s: '
           'debugfsrc=$dfrc configfsrc=$cfrc udc=${udc:-KEINER}"')

ALT_WHILE = """    while [ "$zs" -lt 8 ]; do
        sleep 15
        zs=$((zs + 1))
"""

NEU_WHILE = """    while [ "$zs" -lt 8 ]; do
        # v0al: hat der Host schon enumeriert, ist der Zweck der Runde erfuellt.
        # Gemessen 2026-11-03: state=configured ab 7 s, die Runde lief 8 x 15 s,
        # und der Boot wartete 160 s auf sie. Nur wenn nichts gebunden ist, wird
        # weiter gewartet und angelegt - der Fall des spaeten UDC bleibt.
        if [ -n "$(cat /sys/kernel/config/usb_gadget/g1/UDC </dev/null 2>/dev/null)" ] \\
           && [ "$(cat /sys/class/udc/*/state </dev/null 2>/dev/null)" = configured ]; then
            echo "[$(cut -d. -f1 /proc/uptime)s] step: v0al runde frueh raus: state=configured nach $zs Runde(n)" >> /run/steps.log 2>/dev/null
            echo "omamobile-blueline: v0al runde frueh raus: state=configured" > /dev/kmsg
            break
        fi
        sleep 15
        zs=$((zs + 1))
"""

TITEL_ALT = "Omarchy Mobile first-light v0ak"
TITEL_NEU = "Omarchy Mobile first-light v0al"


def umbau(text: str) -> str:
    assert text.count(ALT_AKT) == 1, "die nackte akt=-Zeile der Runde fehlt"
    assert text.count(ALT_WHILE) == 1, "der Rundenkopf (while + sleep 15) fehlt"
    assert "v0al runde frueh raus" not in text, "der Umbau lief schon einmal"
    assert TITEL_ALT in text, "der v0ak-Titel fehlt"
    text = text.replace(ALT_WHILE, NEU_WHILE).replace(ALT_AKT, NEU_AKT)
    text = text.replace(TITEL_ALT, TITEL_NEU)
    assert text.count("v0al runde frueh raus") == 2, "der Fruehausstieg steht nicht genau zweimal (Log + kmsg)"
    assert text.count("step: v0al runde frueh raus") == 1, "die Schritt-Log-Zeile fehlt"
    assert '        "akt=' not in text, "die nackte akt=-Zeile steht noch da"
    assert TITEL_NEU in text, "der Panel-Titel ist nicht umgestellt"
    assert text.count("sleep 15") == 1, "der Runden-sleep hat sich veraendert"
    assert text.count('while [ "$zs" -lt 8 ]') == 1, "die Rundenzahl ist nicht mehr 8"
    assert "switch_root /ud /init" in text and "offset=1048576" in text, "v0ak-Zeilen fehlen"
    assert all(ord(ch) < 128 for ch in text), "Nicht-ASCII im Init"
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0al-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    elternpruefung(es, "Grundarchiv")
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        anfang = e["content"].decode()
        assert anfang.count("\n") == GRUNDZEILEN, \
            "Grundarchiv hat %d Zeilen, erwartet %d" % (anfang.count("\n"), GRUNDZEILEN)
        neuer_text = umbau(anfang)
        e["content"] = neuer_text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    open(neben, "wb").write(blob)
    zurueck = newc.read_cpio(neben)
    init = next(e["content"] for e in zurueck if e["name"] == "init")
    assert init == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    text = init.decode()
    print("baue-v0al: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), text.count("\n"), len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    print("  Fruehausstieg %d mal, akt=-Zeile %d mal, Titel %s"
          % (text.count("v0al runde frueh raus"), text.count('akt="v0al runde'),
             "v0al" if TITEL_NEU in text else "FALSCH"))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
