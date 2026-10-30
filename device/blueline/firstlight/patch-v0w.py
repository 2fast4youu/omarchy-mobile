#!/usr/bin/env python3
"""Baut v0w aus v0us Archiv: der Pfad zum Knopf wird gesucht, nicht angenommen.

Warum, alles gemessen (firstlight/evidence/debugfs-zweig-kernelbinary-2026-10-30.txt):
die drei soft_connect-Fundstellen im Kernel-Binary liegen in der Kallsyms-
Namenstafel und heissen dwc3_gadget_soft_connect, dwc3_gadget_soft_disconnect,
soft_connect_store - Funktionsnamen, keine Dateinamen. 'usb/%s' (0x01c21594) ist
ein Format-String, deren Einsatz am Binary nicht zu lesen ist, 'usb/%d' gibt es
nicht, und eine eingebettete Config fehlt (CONFIG_IKCONFIG=n, gemessen mit
kernel-config-from-image.py). v0v schreibt deshalb zwei angenommene Pfade an und
meldet im Blindfall 'No such file or directory' - eine Meldung, die zwei
verschiedene Ursachen deckt: 'der Knopf fehlt' und 'der Knopf liegt woanders'.

v0v hat den Pfad zwei mal gesetzt und einmal geraten. v0w sucht ihn und meldet
die Suche:
  - Herzschlag: 'debugfs=...' (liegt der Zaehlkanal ueberhaupt im Bild) und
    'usb=...' (der Inhalt von /sys/kernel/debug/usb)
  - Nachbind-Runde: 'gefunden=<n>' und 'suche=<pfadliste>'
  - gedrueckt wird nur, wenn die gefundene Datei beschreibbar ist (test -w);
    sonst heisst der Befund 'kein Knopf' statt einer Fehlermeldung

Panel-Titel: 'Omarchy Mobile firstlight v0w - RAM only, der Knopf wird gesucht'.

Anker-Regel, die viimal geblutet hat: jeder Anker wird aus dem geladenen Archiv
gelesen und mit gezaehlter Fundstelle gemeldet, bevor geschrieben wird. Anker
werden nicht abgetippt. Die Zitatzeichen kommen aus chr(), damit kein
Fortsetzungszeichen hinter einem String verloren gehen kann, der selbst einen
Backslash traegt.
"""
from __future__ import annotations

import importlib.util
import os
import sys

Q, E, B, N = chr(34), chr(39), chr(92), chr(10)
I12, I8 = " " * 12, " " * 8
HIER = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("newc", os.path.join(HIER, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

# Die zwei Abschluss-Folgen, am Bild gemessen (Zeilen 74 und 365 des v0v-Init):
#   Zeile  74  endet auf  tr '\n' ' ')"            - Herzschlag, ein Paren weniger
#   Zeile 365  endet auf  tr '\n' ' ')" > /dev/kmsg - Bindblock, mit Paren
# Ein Konstantenname, der eine Folge beschreibt, ist nicht die Folge: die erste
# Fassung setzte das Double-Quote vor das Paren und oeffnete eine
# Befehlsersetzung, die keine schloss. Die Bilanz-Pruefung nach dem Umbau fand
# es (146 offen gegen 145 zu) - dieselbe Pruefung, die den ersten v0v-Defekt
# (die zwei fehlenden done) gefunden haette, wenn sie damals schon dagestanden
# haette. TRE endet ohne Paren, TRL mit; welche Zeile welche braucht, steht in
# der Klammer dahinter, nicht im Namen.
TRA = "tr " + E + B + "n" + E + " " + E + " " + E + ")"     # bis zum Paren
TRE = TRA + Q                                              # Herzschlag:  ')"'
TRL = TRE + " > /dev/kmsg"                                  # Bindblock:   ')" > /dev/kmsg'

TITEL_ALT = ("echo " + E + "Omarchy Mobile first-light v0v - RAM only, weicher "
             "Verbindungspflicht am Controller" + E)
TITEL_NEU = ("echo " + E + "Omarchy Mobile first-light v0w - RAM only, der Knopf "
             "wird gesucht" + E)


def lerne_anker(init):
    """Die Anker, die im Bild stehen, durch Schnitt statt durch Abschreiben."""
    z = init.splitlines()
    herz = next(x for x in z if "weicher-bind=debugfs-geoffnet" in x)
    # Die vier Zeilen, die den Pfad annehmen, und die Beweiszeile der Runde.
    pfad1 = next(x for x in z if x.strip().startswith("SC=/sys/kernel/debug/usb"))
    pfad2 = next(x for x in z if x.strip().startswith("SC2=$(ls /sys/kernel/debug"))
    fall = next(x for x in z if x.strip().startswith("[ -f " + Q + "$SC"))
    trenner = next(x for x in z if x.strip().startswith("sc0=$("))
    verbindung = next(x for x in z if "sc1=$( { echo 1 >" in x)
    runde = next(x for x in z if "weicher-bind $rb:" in x and "vorher=$scvor" in x)
    return dict(herz=herz, pfad1=pfad1, pfad2=pfad2, fall=fall, trenner=trenner,
                verbindung=verbindung, runde=runde)


def umbau(init, a):
    """Sucher statt Pfadannahme, mit erhaltenem Bindblock-Ende."""
    text = init
    arbeit = []

    # 1) Titel.
    arbeit.append((TITEL_ALT, TITEL_NEU))

    # 2) Herzschlag: der Suchbericht statt des einzelnen Pfad-Felds.
    #    Die Form ist nicht erfunden, sondern an drei Kandidaten gemessen: nur
    #    die mit ZWEI Double-Quotes besteht bash -n allein. Die dreiteilige Form
    #    (eine Quote in der Zeilenmitte zusaetzlich) ueberlebt nur, weil die
    #    naechste Zeile ihr Double-Quote schliesst - sie zieht die Folgezeile in
    #    ihr Literal und ist damit ein versteckter Defekt, kein Muster.
    #    Der Block laeuft in } > /dev/console, braucht also keine Umleitung.
    arbeit.append((a["herz"],
                   " " * 14 + "echo " + Q + "debugfs=$(ls /sys/kernel/debug 2>/dev/null | "
                   + TRA + " usb=$(ls /sys/kernel/debug/usb 2>/dev/null | " + TRE))

    # 3) Die drei Zeilen, die einen Pfad annehmen, werden durch die Suche ersetzt.
    suche = N.join([
        I12 + "# v0w: der Pfad ist eine Annahme des Vorfaehgers, keine Beobachtung.",
        I12 + "# Gesucht wird im ganzen haengten Zaehlkanal, und die Suche selbst",
        I12 + "# wird zum Messwert: gefundene Zahl und Pfade stehen im Herzschlag.",
        I12 + "SCDATEIEN=$(find /sys/kernel/debug -name soft_connect 2>/dev/null | head -6)",
        I12 + "SCLISTE=$(printf %s " + Q + "$SCDATEIEN" + Q + " 2>/dev/null | " + TRA,
        I12 + "SZAHL=$(printf %s " + Q + "$SCDATEIEN" + Q + " 2>/dev/null | "
        "grep -c . 2>/dev/null)",
        I12 + "SC=$(printf %s " + Q + "$SCDATEIEN" + Q + " 2>/dev/null | head -1)",
        I12 + '[ -n "$SC" ] || SC=/sys/kernel/debug/usb/$u/soft_connect',
        I12 + "test -w " + Q + "$SC" + Q + "; SCRCA=$?",
    ])
    arbeit.append((a["pfad1"] + N + a["pfad2"] + N + a["fall"], suche))

    # 4) Gedrueckt wird nur, wenn die Datei beschreibbar ist.
    arbeit.append((a["trenner"],
                   I12 + "if [ $SCRCA -eq 0 ]; then " + a["trenner"].strip()
                   + "; else sc0=" + Q + "kein Knopf" + Q + "; sc0rc=9; fi"))
    arbeit.append((a["verbindung"],
                   I12 + "if [ $SCRCA -eq 0 ]; then " + a["verbindung"].strip()
                   + "; else sc1=" + Q + "kein Knopf, Suche: $SCLISTE" + Q + "; sc1rc=9; fi"))

    # 5) Die Beweiszeile der Runde nennt die Suche.
    arbeit.append(("vorher=$scvor pfad=$SC ",
                   "vorher=$scvor pfad=$SC gefunden=$SZAHL suche=$SCLISTE scrca=$SCRCA "))
    # Die zweite Rundenzeile: der Befund nach den fuenf Sekunden.
    arbeit.append(("sc1rc=$sc1rc sc1text=$sc1, ",
                   "sc1rc=$sc1rc sc1text=$sc1 scrca=$SCRCA gefunden=$SZAHL, "))

    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
    # Bilanz nach jedem Umbau, vor jedem Geraet. Ein offenes Paren ist auf dem
    # Panel unsichtbar (der Text bricht ab, wo er abbricht), aber sh -n kennt es.
    offen = text.count("(")
    zu = text.count(")")
    print("  Bilanz nach dem Umbau: %d ( gegen %d )" % (offen, zu))
    assert offen == zu, "Paren-Bilanz verschoben: %d offen, %d zu" % (offen, zu)
    # Kein '$( '-Test: '$( { echo ...; } 2>&1 )' ist gueltige Shell (eine
    # Gruppenanweisung in einer Befehlsersetzung) und steht dreimal im Bild. Eine
    # Pruefung, die drei echte Zeilen anklagt, fuehrt dazu, dass man echte Zeilen
    # umschreibt, um ihr zu gehorchen. Echtes Urteil: sh -n auf den Init.
    for nr, zeile in enumerate(text.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        inside = zeile[zeile.find(Q) + 1:zeile.rfind(Q)] if zeile.count(Q) >= 2 else ""
        if inside.count("(") != inside.count(")"):
            print("  not ok - Zeile %d: Echo-Kette %d ( gegen %d )"
                  % (nr, inside.count("("), inside.count(")")))
    return text


def haupt():
    if len(sys.argv) != 3:
        print("usage: patch-v0w.py <neu.cpio von v0v> <neu.cpio fuer v0w>", file=sys.stderr)
        return 2
    in_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(in_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    neben = aus_cpio + ".r"          # Rundschreiben: nur der Ausgabepfad ist beschreibbar
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher = e["content"].decode()
        a = lerne_anker(vorher)
        text = umbau(vorher, a)
        assert "first-light v0w" in text, "neuer Panel-Titel fehlt"
        assert "first-light v0v" not in text, "alter Panel-Titel noch im Text"
        assert text.count("bDeviceState") == 0, "blinde Lesung zurueckgekehrt"
        assert text.count("done") == vorher.count("done"), \
            "done-Zaehlung veraendert (%d gegen %d)" % (text.count("done"), vorher.count("done"))
        assert text.count("; do") == vorher.count("; do"), \
            "Schleifenzahl veraendert (%d gegen %d)" % (text.count("; do"), vorher.count("; do"))
        assert "gefunden=$SZAHL" in text and "suche=$SCLISTE" in text, \
            "der Suchbericht fehlt in der Beweiszeile"
        assert "SCRCA=$?" in text, "die Beschreibbar-Pruefung fehlt"
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    with open(neben, "wb") as offen:
        offen.write(blob)
    back = {e["name"]: e for e in newc.read_cpio(neben)}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert back["init"]["content"].decode() == next(
        e["content"].decode() for e in es if e["name"] == "init"), "round-trip nicht dicht"
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    soll = len({e["name"] for e in es if e["name"].startswith("usr/lib/modules/")})
    assert len(module) == soll >= 5, "Module nach round-trip nicht vollstaendig: %d von %d" % (
        len(module), soll)
    with open(aus_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(aus_cpio, 0o644)
    roh = os.environ.get("V0W_ROHTEXT")
    if roh:
        os.makedirs(os.path.dirname(roh), exist_ok=True)
        with open(roh, "w", encoding="utf-8") as offen:
            offen.write(init)
    print("patch-v0w: init %d B, %d Zeilen, Module %d, soft_connect %d, Suchbericht %d mal"
          % (len(init), init.count(chr(10)), len(module),
             init.count("soft_connect"), init.count("gefunden=$SZAHL")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
