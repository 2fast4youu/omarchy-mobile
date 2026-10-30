#!/usr/bin/env python3
r"""v0v: v0us Bild, plus der weiche Verbindungspflicht am Controller.

Warum, gemessen (nicht geraten):
  - Am entpackten Kernel-Binary (44 498 944 Byte, aus images/fl-v0u/kernel-blob,
    gzip) steht `soft_connect` 2 mal und `bDeviceState` 0 mal. Das erklaert v0ts
    leere Doppel-Knoten-Zeile vollstaendig: der Knoten existiert in diesem Kernel
    nicht, dort kann man nichts ablesen.
  - v0t meldete am Panel 'state=not attached' bei leerem gebunden=-Feld. Ein
    Controller im Zustand 'not attached' zieht D+ nicht hoch, der Host sieht
    nichts - egal wie oft man das Gadget bindet. Genau das war der Ausgang von
    v0r und v0t: zwei Messlaeufe, 0 Beobachtungen in je 302 s.
  - DWC3 hat in seinem debugfs-Zweig eine Datei soft_connect. Ein 0 schreibt den
   soft disconnect, ein 1 erzwingt die Verbindung beim Host. Das ist der einzige
    Knopf, den noch kein Bild gedreht hat.

Was v0v tut, in der bestehenden Nachbind-Schleife, pro Runde:
    debugfs haengen, soft_connect vor dem Binden lesen, weich trennen,
    abbinden, binden (wie v0u, mit rc und Fehlertext), hart nachbinden,
    weich verbinden, und den Zustand direkt danach aufschreiben.
Der Panel-Herzschlag nennt zusaetzlich 'weicher-bind=debugfs-geoffnet' mit dem
debugfs-Pfad, damit am Bildschirm lesbar ist, ob der Knopf ueberhaupt erreichbar
war - 'Datei fehlt' und 'Knopf gedrueckt, wirkt nicht' sind verschiedene Befunde.

Erwartung: 'state=' geht von 'not attached' auf 'default' oder 'configured', und
der Host sieht Vendor 0x18D1 Produkt 0xD002. Bleibt 'not attached' trotz rc=0 auf
beiden soft_connect-Writes, ist die Verbindung physikalisch weg (VBUS, CC,
Kabel, Port) und kein Softwareweg schuld.

Anker-Regel (drei Trockenlaeufe haben sie erzwungen): jeder Anker ist eine am
Bild gemessene Zeichenkette, zusammengesetzt aus chr(34)/chr(39)/chr(92), nie
aus dem Kopf. Beweismittel: firstlight/anker-vergleich.py.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

Q = chr(34)     # Double-Quote
A = chr(39)     # Single-Quote
B = chr(92)     # Backslash
N = "\n"
K12 = " " * 12
K8 = " " * 8
# tr '\n' ' ')"  - die Abschluegung der Bildzeilen, am Bild gemessen
TRE = "tr " + A + B + "n" + A + " " + A + " " + A + ")" + Q
# dieselbe, aber ohne das schliessende Double-Quote (Zeilen, die weitergehen)
TRK = "tr " + A + B + "n" + A + " " + A + " " + A + ")"
# Die Zeilenenden im Bild: eine Beweiszeile ohne diese Weiterleitung
# schreibt ins Leere. Der Panel zeigt sie trotzdem, /dev/kmsg ist der Kanal.
UMLEITUNG = chr(34) + " > /dev/kmsg" + N

TITEL_ALT = """echo 'Omarchy Mobile first-light v0u - RAM only, Binden ist messbar, Typ-C am Panel'"""
TITEL_NEU = """echo 'Omarchy Mobile first-light v0v - RAM only, weicher Verbindungspflicht am Controller'"""

# Der Herzschlag bekommt eine Zeile, die den Knopf als erreichbar ausweist.
HERZ_ANKER = (K14 := " " * 14) + ('echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"')
HERZ_NEU = (K14 + 'echo "weicher-bind=debugfs-geoffnet pfad=$(ls /sys/kernel/debug/usb/ 2>/dev/null | '
            + TRK + ' ' + Q + N + HERZ_ANKER)

# Die Nachbind-Schleife: vor dem Abbinden der weiche Trenner, nach dem Binden
# der weiche Verbindner, dazwischen der Zustand.
SCHLEIFE_ALT = (
    K12 + '[ -n "$u" ] || continue' + N
    + K12 + 'echo none > "$g/UDC" 2>/dev/null' + N
    + K12 + 'sleep 1' + N)
SCHLEIFE_NEU = (
    K12 + '[ -n "$u" ] || continue' + N
    + K12 + '# v0v: der weiche Verbindungspflicht. v0t meldete state=not attached' + N
    + K12 + '# bei leerem gebunden=-Feld, und ein Controller, der nicht verbindet,' + N
    + K12 + '# zeigt dem Host nichts - egal wie oft man bindet. soft_connect sitzt' + N
    + K12 + '# im debugfs-Zweig von dwc3 (am Kernel-Binary gemessen: 3 Fundstellen).' + N
    + K12 + 'mount -t debugfs none /sys/kernel/debug 2>/dev/null' + N
    + K12 + '# Der Ordner unter /sys/kernel/debug/usb heisst nach dem Gerit (im Kernel: usb/%s). Ob das der UDC-Name ist, ist NICHT beobachtet, also beide Kandidaten festgehalten.' + N
    + K12 + 'SC=/sys/kernel/debug/usb/$u/soft_connect' + N
    + K12 + 'SC2=$(ls /sys/kernel/debug/usb/*/soft_connect 2>/dev/null | head -1)' + N
    + K12 + '[ -f "$SC" ] || SC=${SC2:-$SC}' + N
    + K12 + 'scvor=$(cat "$SC" 2>/dev/null)' + N
    + K12 + 'sc0=$( { echo 0 > "$SC"; } 2>&1 ); sc0rc=$?' + N
    + K12 + 'echo none > "$g/UDC" 2>/dev/null' + N
    + K12 + 'sleep 1' + N)

# Der Anker ist aus dem Vorgaengerbild geschnitten (Zeile 353 an), nicht
# abgetippt. Drei von vier Anlaeufen waren Tippfehler in Zitatzeichen.
# Liste statt Aneinanderreihung: die Zeile traegt selbst Backslashes.
BINDE_ALT = [
    '            echo "omamobile-blueline: nachbinden $rb: write rc=$rc text=$err, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), interfaces=$(ls /sys/class/net 2>/dev/null | tr \'\\n\' \' \')" > /dev/kmsg',
    '            sleep 5',
    '            echo "omamobile-blueline: nachbinden $rb spaeter 5s: UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), udc-state=$(cat /sys/class/udc/*/state 2>/dev/null)" > /dev/kmsg',
    '        done',
    '    done',
]

# v0v: weicher Verbindner, sein Befund, fuenf Sekunden, der Zustand
# danach, dann die zwei done, die erhalten bleiben muessen.
BINDE_NEU = [
    '            echo "omamobile-blueline: weicher-bind $rb: write rc=$rc text=$err vorher=$scvor pfad=$SC rc0=$sc0rc text0=$sc0 rc1=$sc1rc text1=$sc1, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), interfaces=$(ls /sys/class/net 2>/dev/null | tr \'\\n\' \' \')" > /dev/kmsg',
    '            sc1=$( { echo 1 > "$SC"; } 2>&1 ); sc1rc=$?',
    '            sleep 5',
    '            echo "omamobile-blueline: weicher-bind $rb spaeter 5s: sc1rc=$sc1rc sc1text=$sc1, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), udc-state=$(cat /sys/class/udc/*/state 2>/dev/null)" > /dev/kmsg',
    '        done',
    '    done',
]

BINDE_ALT = N.join(BINDE_ALT)
BINDE_NEU = N.join(BINDE_NEU)

ERWARTET_SC_VORHER = 0     # v0u kennt soft_connect nicht
ERWARTET_SC_NACHHER = 3    # gezehlt im Trockenlauf: zwei Pfadzeilen und eine
# Kommentarzeile. Der Platzhalter oben (6, dann 2) war zweimal zu viel.
# eine Kommentarzeile. Eine Zahl aus dem Kopf (zuerst 6) ist hier schon
# einmal umgefallen, siehe die Regel im Text oben.


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
        for alt, neu in ((TITEL_ALT, TITEL_NEU), (HERZ_ANKER, HERZ_NEU),
                         (SCHLEIFE_ALT, SCHLEIFE_NEU), (BINDE_ALT, BINDE_NEU)):
            n = text.count(alt)
            assert n == 1, "Anker %r genau %d mal, erwartet 1" % (alt[:56], n)
            text = text.replace(alt, neu, 1)
        assert vorher.count("soft_connect") == ERWARTET_SC_VORHER, \
            "v0u traegt soft_connect %d mal, erwartet %d" % (
                vorher.count("soft_connect"), ERWARTET_SC_VORHER)
        ist = text.count("soft_connect")
        assert ist == ERWARTET_SC_NACHHER, \
            "soft_connect %d mal, erwartet %d" % (ist, ERWARTET_SC_NACHHER)
        assert text.count("; do") == vorher.count("; do"), \
            "Schleifenzahl veraendert (%d gegen %d)" % (text.count("; do"), vorher.count("; do"))
        assert text.count("done") == vorher.count("done"), \
            "done-Zaehlung veraendert (%d gegen %d)" % (text.count("done"), vorher.count("done"))
        assert "first-light v0u" not in text, "alter Panel-Titel noch im Text"
        assert "debugfs-geoffnet" in text and "rc0=$sc0rc" in text and "rc1=$sc1rc" in text, \
            "Beweiszeilen fehlen (die Labels, nicht die Werte: ein Label, das einen Fehlertext unter einem Vorher-Namen zeigt, ist selbst ein Defekt)"
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        assert len(text) > len(vorher), "Init ist nicht groesser geworden, Zeilen fehlen"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    with open("/tmp/v0v-r.cpio", "wb") as offen:
        offen.write(blob)
    back = {e["name"]: e for e in newc.read_cpio("/tmp/v0v-r.cpio")}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert "soft_connect" in init, "weicher Verbindungspflicht im round-trip verloren"
    assert init.count("soft_connect") == ERWARTET_SC_NACHHER, "round-trip zaehlt anders"
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    assert len(module) == len([n for n in {e["name"] for e in es}
                               if n.startswith("usr/lib/modules/")]) >= 5, \
        "Module nach round-trip nicht vollstaendig: %d" % len(module)
    with open(out_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(out_cpio, 0o644)
    print("patch-v0v: init %d B, %d Zeilen, Module %d, soft_connect %d -> %d, Balancegleich"
          % (len(init), init.count(chr(10)), len(module),
             ERWARTET_SC_VORHER, ERWARTET_SC_NACHHER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
