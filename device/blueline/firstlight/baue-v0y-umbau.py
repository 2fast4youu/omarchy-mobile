#!/usr/bin/env python3
"""v0x -> v0y, als EIN Durchgang ueber das geladene v0x-Archiv.

Grund, gemessen: die Herzschlagzeile des v0x liest
    modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)
Die innere Substitution ist unquotiert. Findet die Suche nichts, erhaelt cat
KEIN Argument und liest dann die Standardeingabe - und die ist bei PID 1 die
Konsole, die Init kennt keine Umleitung davon (gemessen: 0 Fundstellen fuer
'< /dev/null', 'exec <', '0<' in der gelieferten Init). Ein Pty-Versuch auf dem
Rechner zeigte genau dieses Verhalten: 'VOR dem cat' kommt, 'NACH dem cat'
kommt in drei Sekunden nicht.

Entscheidend ist der Ort: dieselbe Schleife fuettert den Watchdog
('echo -n V > "$wd"'). Steht der Druck still, steht die Fuetterung still, und
der Baustein setzt neu ein - in dem Bild, das den Grund fuer eine ausbleibende
Bus-Enumeration melden soll. Der Haenger feuert ausserdem nur im Fehlerfall
(kein mode-Knoten = dwc3-Knoten nie angelegt), also genau in dem Zweig, den wir
ablesen wollen.

Zwei Zeilen, beide mit Grund:
  A  Panel-Titel v0x -> v0y. Der Panel ist bei ausbleibender Enumeration das
     einzige Lesegeraet; ein Foto muss den Stand zeigen.
  B  '</dev/null' an die cat-Ersetzung: eine leere Argumentliste liest die
     schwarze Datei statt zu blockieren. Kein Wegfall einer Messung - debugfs=,
     usb= und modewert= bleiben wortgleich in derselben Zeile.

Der Rest des Bildes bleibt Byte fuer Byte gleich; verify-v0y.py beweist das als
Zeilendififf gegen das v0x-Bild (genau zwei verschiedene Zeilen).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "first-light v0x - RAM only"
TITEL_NEU = "first-light v0y - RAM only"

HANG = ("modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null"
        " | head -1) 2>/dev/null)")
GUARD = ("modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null"
         " | head -1) 2>/dev/null </dev/null)")


def umbau(text: str) -> str:
    arbeit = [(TITEL_AN, TITEL_NEU), (HANG, GUARD)]
    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        # Erst ersetzen, dann zaehlen: die erste Fassung dieser Pruefung stand
        # VOR der Ersetzung und meldete 'Ersatz nicht eindeutig' bei einer
        # Fundstelle von 0, weil der Ersatz in diesem Augenblick noch gar nicht
        # im Text stand. Ein Pruefer, der seinen eigenen Eingriff nicht abwartet,
        # misst die Dunkelheit vor der Arbeit.
        assert text.count(neu) == 1, "Schritt %d: Ersatz danach %d mal, erwartet 1" % (
            nr, text.count(neu))

    # blind, nicht Einzelfall: jede Zeile, die cat mit einer unquotierten
    # Kommandosubstitution fuettert, muss die Standardeingabe geschlossen
    # haben. (Ein Argument fehlt genau dann, wenn die Suche nichts findet; das
    # ist der Normalfall eines nicht gebundenen Controllers.)
    blind = [nr for nr, zeile in enumerate(text.splitlines(), 1)
             if "cat $(" in zeile and "</dev/null" not in zeile]
    offen = [zeile for zeile in text.splitlines() if "cat $(" in zeile]
    print("  cat mit innerer Substitution: %d Zeile(n), davon ohne Stdin-Abschluss: %d"
          % (len(offen), len(blind)))
    assert not blind, "Zeile(n) %s lesen im Leerlauf die Konsole" % blind

    a, z = text.count("("), text.count(")")
    print("  Bilanz nach dem Umbau: %d ( gegen %d )" % (a, z))
    assert a == z, "Paren-Bilanz verschoben: %d offen, %d zu" % (a, z)
    for nr, zeile in enumerate(text.splitlines(), 1):
        if zeile.lstrip().startswith("echo") and zeile.count(chr(34)) >= 2:
            inside = zeile[zeile.find(chr(34)) + 1:zeile.rfind(chr(34))]
            assert inside.count("(") == inside.count(")"), \
                "Zeile %d: Echo-Kette %d ( gegen %d )" % (nr, inside.count("("), inside.count(")"))
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0y-umbau.py <new.cpio von v0x> <new.cpio fuer v0y>", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    vorher = {}
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher = {x["name"]: x["content"] for x in es}
        text = umbau(e["content"].decode())
        assert TITEL_NEU in text, "neuer Panel-Titel fehlt"
        assert "first-light v0x" not in text, "alter Panel-Titel noch im Text"
        assert text.count("mount -t debugfs") == 2, \
            "debugfs-Mounts %d, erwartet 2" % text.count("mount -t debugfs")
        assert "modewert=$MODW" in text and "modepfad=$MODENEUGEFUNDEN" in text, \
            "der modus-Bericht fehlt"
        assert "SCRCA=$?" in text, "die Beschreibbar-Pruefung fehlt"
        for msg in ("debugfs=$(", "usb=$(", "modewert=$("):
            assert msg in text, "Messfeld %s aus dem Herzschlag gefallen" % msg
        for w in ("done", "; do"):
            assert text.count(w) == vorher["init"].decode().count(w), \
                "%s-Zaehlung veraendert" % w
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as offen:
        offen.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    assert zurueck["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert zurueck["init"]["content"] == next(
        e["content"] for e in es if e["name"] == "init"), "round-trip nicht dicht"
    modul = [n for n in zurueck if n.startswith("usr/lib/modules/")]
    soll = len({e["name"] for e in es if e["name"].startswith("usr/lib/modules/")})
    assert len(modul) == soll >= 5, "Module nach round-trip unvollstaendig: %d von %d" % (
        len(modul), soll)
    with open(aus_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(aus_cpio, 0o644)
    init = zurueck["init"]["content"].decode()
    print("baue-v0y: init %d B, %d Zeilen, Module %d, Stdin-Haenger %d, Titel %s"
          % (len(init), init.count(chr(10)), len(modul),
             sum(1 for z in init.splitlines() if "cat $(" in z and "</dev/null" not in z),
             TITEL_NEU.split()[1]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
