#!/usr/bin/env python3
"""Beweismale an v0y, gemessen AM FERTIGEN BILD und im Zeilendiff gegen v0x.

Warum der Diff und nicht nur eine Liste von Anwesenheiten: die Regel, die sich
aus frueheren Laeufen geschrieben hat, lautet 'ein Ersatz darf eine vorhandene
Messung nicht stumm entfernen'. Eine Anwesenheitsliste sieht das nicht - sie
prueft, was drin steht, nicht, was weggeblieben ist. Der Zeilendiff gegen das
Vorgaengerbild beweist beides in einem: die Zahl der verschiedenen Zeilen und
ihr Inhalt.

Erwartet genau zwei verschiedene Zeilen:
  die Titelzeile (v0x -> v0y, damit ein Foto den Stand nennt) und
  die Herzschlagzeile (Stdin der cat-Ersetzung auf die schwarze Datei).
Alles andere muss bytegleich sein.
"""
from __future__ import annotations

import gzip
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

V0X = os.environ.get("V0X", "/Users/gregor/hermes-workspace/images/fl-v0x/firstlight.img")

TITEL_AN = "first-light v0x - RAM only"
TITEL_NEU = "first-light v0y - RAM only"
GUARD = ("modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null"
         " | head -1) 2>/dev/null </dev/null)")

# Messfelder, die im Herzschlag stehen muessen (Bild 19778004 B, Zeile 77)
MESSFELDER = ("debugfs=$(", "usb=$(", "modewert=$(", "controller-state=$(",
              "udc-state=$(", "is_active=$(", "typc: state=$(", "pid1=$(")
# v0x-Beweise, die unveraendert stehen muessen
MARKEN = ('mount -t debugfs none /sys/kernel/debug 2>/dev/null || true',
          '[ -n "$SC" ] || SC=""   # v0x: der v0w-Fallback war ein Phantom',
          'if [ -n "$SC" ]; then test -w "$SC"; SCRCA=$?; else SCRCA=9; fi',
          "scrca=$SCRCA modepfad=$MODENEUGEFUNDEN modewert=$MODW rc0=$sc0rc",
          "scrca=$SCRCA gefunden=$SZAHL modewert=$MODW, ",
          "MODEPFAD=$(find /sys/kernel/debug -name mode 2>/dev/null | head -2)",
          'MODENEUGEFUNDEN=$(printf %s "$MODEPFAD" 2>/dev/null | grep -c . 2>/dev/null)',
          'MODE=$(printf %s "$MODEPFAD" 2>/dev/null | head -1)',
          'MODW=$( { cat "$MODE"; } 2>&1 ); MODWRC=$?')


def init_text(bild: str) -> str:
    """Init aus einem Android boot.img, Seite fuer Seite wie im Vorgaenger.

    Der Versatz ist nicht geraten: kernel_size bei 8, ramdisk groesse bei 16,
    die ramdisk beginnt an der Seite HINTER dem Kernel (page + aufgerueckter
    Kernel). Eine fruehere Fassung rechnete 24 + kernel_size und bekam
    'Not a gzipped file (b\\x00\\x00)'.
    """
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    laenge = struct.unpack_from("<I", d, 16)[0]
    roh = gzip.decompress(d[rd:rd + laenge])
    ordner = tempfile.mkdtemp(prefix="v0y-pruef-")
    pfad = os.path.join(ordner, "ram.cpio")
    with open(pfad, "wb") as offen:
        offen.write(roh)
    return {e["name"]: e for e in newc.read_cpio(pfad)}["init"]["content"].decode()


def haupt() -> int:
    if len(sys.argv) != 2:
        print("usage: verify-v0y.py <firstlight.img von v0y>", file=sys.stderr)
        return 2
    neu = init_text(sys.argv[1])
    alt = init_text(V0X)
    fehler = 0
    zahl = 0

    def pruef(cond: bool, meldung: str) -> None:
        nonlocal fehler, zahl
        zahl += 1
        if cond:
            print("ok - " + meldung)
        else:
            print("not ok - " + meldung)
            fehler += 1

    alts, neus = alt.splitlines(), neu.splitlines()
    pruef(len(alts) == len(neus),
          "Zeilenzahl gleich (%d wie im Vorgaenger)" % len(neus))
    versch = [(i + 1, a, b) for i, (a, b) in enumerate(zip(alts, neus)) if a != b]
    pruef(len(versch) == 2,
          "genau zwei verschiedene Zeilen gegen v0x (gemessen: %d -> %s)"
          % (len(versch), [n for n, _, _ in versch]))
    inhalte = {b for _, _, b in versch}
    pruef(any(TITEL_NEU in b for b in inhalte), "die eine Aenderung ist der Panel-Titel v0y")
    pruef(any(GUARD in b for b in inhalte), "die andere ist der Stdin-Abschluss der cat-Ersetzung")

    pruef(TITEL_NEU in neu, "Panel-Titel v0y im fertigen Bild")
    pruef(TITEL_AN not in neu, "kein Panel-Titel v0x mehr")
    pruef("first-light v0w" not in neu and "first-light v0t" not in neu,
          "keine aelteren Panel-Titel")

    blind = [i + 1 for i, z in enumerate(neus) if "cat $(" in z and "</dev/null" not in z]
    pruef(not blind, "keine cat-Ersetzung ohne Stdin-Abschluss (Zeilen %s)" % blind)
    for feld in MESSFELDER:
        pruef(feld in neu, "Messfeld %s steht im Herzschlag" % feld)
    for marke in MARKEN:
        pruef(neu.count(marke) >= 1, "v0x-Beweis unveraendert: %s" % marke[:52])
    pruef(neu.count("mount -t debugfs") == 2,
          "debugfs-Mounts: %d (der fruehe und der idempotente)" % neu.count("mount -t debugfs"))
    tests = [z for z in neus if "test -w " in z]
    pruef(len(tests) == 1 and tests[0].lstrip().startswith("if ["),
          "test -w: %d Zeile(n), in ihrer Bedingung" % len(tests))
    for w in ("done", "; do", "while"):
        pruef(neu.count(w) == alt.count(w), "%s-Zaehlung gleich (%d)" % (w, neu.count(w)))
    pruef(neu.isascii(), "fertige Init ist reines ASCII (Panel ohne UTF-Konsole)")
    paren = sum(z.count("(") - z.count(")") for z in neus)
    pruef(paren == 0, "Klammer-Bilanz ueber alle Zeilen: %d" % paren)
    # Der Hänger selbst, als positiver Beweis: die Herzschlagzeile endet ihre
    # cat-Ersetzung mit der schwarzen Datei, liest also im Leerlauf nichts.
    herz = [z for z in neus if GUARD in z]
    pruef(len(herz) == 1, "die geschuetzte steht genau einmal (%d)" % len(herz))

    print("%d Beweismale, %d Fehler" % (zahl, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(haupt())
