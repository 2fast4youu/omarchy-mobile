#!/usr/bin/env python3
r"""v0u: macht das Binden selbst messbar, nimmt die blinden Lesungen raus.

Warum: v0t meldet am Panel 'state=not attached' und eine leere gebunden=-Zeile.
Diese zwei Fakten sind nur trennbar, wenn das Binden seinen Rueckgabewert,
seinen Fehlertext und den Zustand kurz danach selbst aufschreibt. Ausserdem
lesen drei Zeilen des v0t-Init einen Knoten, den dieser Kernel nicht hat:
`bDeviceState` kommt 4 mal in 3 Zeilen vor (72, 73 zweimal, 348 - an einem Bild
gemessen, nicht aus dem Kopf) und bleibt nachweislich leer. Eine Zeile, deren
Ausgabefeld strukturell leer bleibt, ist kein Messwert, sondern Dunkelheit mit
gutem Gewissen. v0u stellt sie auf den belegten Knoten `state` um
(evidence/reference-live-vor-v0r-2026-10-30.txt, Inhalt 'configured') und
verlangt am Ende, dass kein bDeviceState mehr im Text steht.

Nebenan kommt die Typ-C-Zeile dazu: 'not attached' am UDC ist ein Satz ueber
die Verbindung, nicht ueber das Gadget, und die Verbindung messen die Typ-C-
und power_supply-Knoten (state, power_role, online).

Drei eigene Fehler, die hier als Regel stehen:
  1) Ein Anker aus vier Zeilen, der die Folgezeile nicht mitnimmt, laesst die
     alte Echo-Zeile stehen und meldet 'genau 1 mal' trotzdem als Erfolg. Der
     Bindblock-Anker endet deshalb bis /dev/kmsg.
  2) Backslash-Zauberei in einer Shell: ein Heredoc machte aus zwei Backslashes
     einen und Python meldete 'unexpected character after line continuation'.
  3) .rstrip() am Ankerende frass den Leerstrich vor dem schliessenden
     Double-Quote ('tr \n' ' ')" wurde zu 'tr \n' ')" ) - 0 Treffer. Ein Anker
     endet an einer gemessenen Zeichenkette, nie an einer zurechtgestutzten.
     Anker gegen das Bild pruefen, bevor geflasht wird: firstlight/
    anker-vergleich.py zeigt die erste Abweichung Zeichen fuer Zeichen.

Trockenlauf:  python3 patch-v0u.py <v0t-new.cpio> /tmp/v0u-trocken.cpio
Der Lauf prueft jeden Anker auf genau einen Treffer, die do/done-Balance,
ASCII, Round-trip, Ausfuehrbarkeit, Modulzahl und dass bDeviceState verschwindet.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

Q = chr(34)   # Double-Quote
A = chr(39)   # Single-Quote
B = chr(92)   # Backslash
E = Q         # Doppel-Quote, unfluchtiert: am Bild gemessen (Zeichen 20 und
              # 27 der Zeile 348: U+0022, kein Backslash davor). Ein erster
              # Griff mit \" (U+005C U+0022) meldete 0 Treffer; die
              # Anfuhrungszeichen in den Init-Zeilen sind nackt.

# Die tr-Abschluegung der Init-Zeichenkette, am Bild gemessen (5 Zeilen):
# tr + Leerstrich + Einfach-Quote + Backslash + n + Einfach-Quote + Leerstrich
# + Einfach-Quote + Einfach-Quote + Klammer zu + Double-Quote
TRE = "tr " + A + B + "n" + A + " " + A + " " + A + ")" + Q

TITEL_ALT = """echo 'Omarchy Mobile first-light v0t - RAM only, Doppel-Knoten-Lesung am Panel'"""
TITEL_NEU = """echo 'Omarchy Mobile first-light v0u - RAM only, Binden ist messbar, Typ-C am Panel'"""

# Die blinden Herzschlagzeilen durch die belegte Lesung ersetzen.
STAAT_ALT = ('              echo "controller-state=$(cat /sys/class/udc/*/bDeviceState 2>/dev/null) '
             'gadgetordner=$(ls /sys/kernel/config/usb_gadget 2>/dev/null | ' + TRE)
STAAT_NEU = ('              echo "controller-state=$(cat /sys/class/udc/*/state 2>/dev/null) '
             'gadgetordner=$(ls /sys/kernel/config/usb_gadget 2>/dev/null | ' + TRE)

# v0ts Doppelzeile hatte die Antwort schon geliefert: der eine Knoten existiert,
# der andere nicht. Die Dateiaufzaehlung bleibt, sie ist der Beleg dafuer.
DOPPEL_ALT = ('              echo "beide Knoten: state=$(cat /sys/class/udc/*/state 2>/dev/null) '
              'bDeviceState=$(cat /sys/class/udc/*/bDeviceState 2>/dev/null) '
              'udcdateien=$(ls /sys/class/udc/*/ 2>/dev/null | ' + TRE)
TRK = ("tr " + A + B + "n" + A + " " + A + " " + A + ")")
# TRK ist wie TRE, aber ohne das schliessende Double-Quote: fuer Zeilen, die
# nach der tr-Abschluegung noch weitergehen (DOPPEL_NEU, TYP_NEU).
DOPPEL_NEU = ('              echo "udcdateien=$(ls /sys/class/udc/*/ 2>/dev/null | ' + TRK +
              ' udc-state=$(cat /sys/class/udc/*/state 2>/dev/null) '
              'is_active=$(cat /sys/class/udc/*/is_active 2>/dev/null)"')

# Die Typ-C-/VBUS-Zeile, neu, hinter der bestehenden rolle-Zeile.
TYP_ALT = ('              echo "dwc3 rolle=$(cat /sys/class/typec/*/data_role 2>/dev/null) '
           'typec=$(ls /sys/class/typec 2>/dev/null) '
           'vbus=$(cat /sys/class/power_supply/usb/online 2>/dev/null)"')
TYP_NEU = ('              echo "typc: state=$(cat /sys/class/typec/*/state 2>/dev/null) '
           'power_role=$(cat /sys/class/typec/*/power_role 2>/dev/null) '
           'vbus_online=$(cat /sys/class/power_supply/*/online 2>/dev/null) '
           'stecker=$(ls /sys/class/power_supply 2>/dev/null | ' + TRE)

# Der Bindblock: vier Zeilen plus die ganze Folgezeile bis /dev/kmsg, damit
# nichts Altes stehenbleibt. Fehlertext, Rueckgabewert, zwei zeitliche Stiche.
N = "\n"
K12 = " " * 12
BINDEFIX_ALT = (
    K12 + '[ -n "$u" ] || continue' + N
    + K12 + 'echo none > "$g/UDC" 2>/dev/null' + N
    + K12 + 'sleep 1' + N
    + K12 + 'echo "$u" > "$g/UDC" 2>/dev/null' + N
    + K12 + 'echo "omamobile-blueline: nachbinden $rb: UDC steht auf '
    + '$(cat ' + E + '$g/UDC' + E + ' 2>/dev/null), state=$(cat ' + E + '$g/udc/$u/bDeviceState' + E + ' 2>/dev/null), '
    + 'interfaces=$(ls /sys/class/net 2>/dev/null | ' + TRE + ' > /dev/kmsg' + N)

BINDEFIX_NEU = (
    K12 + '[ -n "$u" ] || continue' + N
    + K12 + 'echo none > "$g/UDC" 2>/dev/null' + N
    + K12 + 'sleep 1' + N
    + K12 + "# Der Fehlertext ist der Messwert: 'device or resource busy'," + N
    + K12 + "# 'invalid argument' und 'no such device' sind drei verschiedene" + N
    + K12 + "# Ursachen und hoeren sich drei verschieden an. Bisher lief der" + N
    + K12 + '# write mit 2>/dev/null ins Leere, die Ursache war unsichtbar.' + N
    + K12 + 'err=$( { echo "$u" > "$g/UDC"; } 2>&1 )' + N
    + K12 + 'rc=$?' + N
    + K12 + 'echo "omamobile-blueline: nachbinden $rb: write rc=$rc text=$err, '
    + 'UDC steht auf $(cat ' + E + '$g/UDC' + E + ' 2>/dev/null), staat=$(cat ' + E + '$g/udc/$u/state' + E + ' 2>/dev/null), '
    + 'interfaces=$(ls /sys/class/net 2>/dev/null | ' + TRE + ' > /dev/kmsg' + N
    + K12 + 'sleep 5' + N
    + K12 + 'echo "omamobile-blueline: nachbinden $rb spaeter 5s: '
    + 'UDC steht auf $(cat ' + E + '$g/UDC' + E + ' 2>/dev/null), staat=$(cat ' + E + '$g/udc/$u/state' + E + ' 2>/dev/null), '
    + 'udc-state=$(cat /sys/class/udc/*/state 2>/dev/null)" > /dev/kmsg' + N)

# Vorgerechnet am v0t-Bild: 4 Vorkommen in 3 Zeilen, alle vier verschwinden.
ERWARTET_VORHER = 4
ERWARTET_NACHHER = 0


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
        for alt, neu in ((TITEL_ALT, TITEL_NEU), (STAAT_ALT, STAAT_NEU),
                         (DOPPEL_ALT, DOPPEL_NEU), (TYP_ALT, TYP_NEU),
                         (BINDEFIX_ALT, BINDEFIX_NEU)):
            n = text.count(alt)
            assert n == 1, "Anker %r genau %d mal, erwartet 1" % (alt[:52], n)
            text = text.replace(alt, neu, 1)
        assert vorher.count("bDeviceState") == ERWARTET_VORHER, \
            "v0t traegt bDeviceState %d mal, erwartet %d" % (
                vorher.count("bDeviceState"), ERWARTET_VORHER)
        assert text.count("bDeviceState") == ERWARTET_NACHHER, \
            "bDeviceState noch %d mal, erwartet %d: eine blinde Lesung steht noch drin" % (
                text.count("bDeviceState"), ERWARTET_NACHHER)
        assert text.count("; do") == vorher.count("; do"), \
            "Schleifenzahl veraendert (%d gegen %d)" % (text.count("; do"), vorher.count("; do"))
        assert text.count("done") == vorher.count("done"), \
            "done-Zaehlung veraendert (%d gegen %d)" % (text.count("done"), vorher.count("done"))
        assert "first-light v0t" not in text, "alter Panel-Titel noch im Text"
        assert "write rc=$rc" in text and "spaeter 5s" in text, "Binden-Beweiszeilen fehlen"
        assert TRE in text, "tr-Abschluegung verloren"
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        assert len(text) > len(vorher), "Init ist nicht groesser geworden, Zeilen fehlen"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    with open("/tmp/v0u-r.cpio", "wb") as offen:
        offen.write(blob)
    back = {e["name"]: e for e in newc.read_cpio("/tmp/v0u-r.cpio")}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert "write rc=$rc" in init, "Binden-Beweis im round-trip verloren"
    assert init.count("bDeviceState") == ERWARTET_NACHHER, \
        "round-trip hat bDeviceState zurueckgebracht"
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    assert len(module) == len([n for n in {e["name"] for e in es}
                               if n.startswith("usr/lib/modules/")]) >= 5, \
        "Module nach round-trip nicht vollstaendig: %d" % len(module)
    with open(out_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(out_cpio, 0o644)
    print("patch-v0u: init %d B, %d Zeilen, Module %d, bDeviceState %d -> %d, Balancegleich"
          % (len(init), init.count(chr(10)), len(module), ERWARTET_VORHER, ERWARTET_NACHHER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
