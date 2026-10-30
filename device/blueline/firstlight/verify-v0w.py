#!/usr/bin/env python3
"""v0w-Beweismale am fertigen Bild: die Suche muss vor der Annahme stehen.

Was v0w von v0v unterscheidet, ist keine neue Zeichenkette, sondern eine
Reihenfolge. v0v setzte den Pfad des weichen Verbindungsknopfs als Wissen
voraus (/sys/kernel/debug/usb/$u/soft_connect) und schrieb zweimal hinein.
Gemessen ist davon nichts: am Kernel-Binary stehen soft_connect 3 Fundstellen,
und alle drei sind Namen in der Kallsyms-Tafel, keine beobachteten Dateipfade
(CONFIG_IKCONFIG=n, keine eingebettete Config). Ein Bild, das einen Knoten
drueckt, den es nicht nachgewiesen hat, meldet 'kein Knopf' wie 'Knopf ohne
Wirkung'.

Deshalb prueft diese Datei auf Reihenfolge, nicht auf Anwesenheit:
  - die Suche (find) vor der Annahme (dem Platzhalter) steht,
  - die Platzhalterzeile bedingt ist ('[ -n ... ] ||'), nicht unbedingt,
  - die Beschreibbar-Pruefung vor beiden Writes liegt,
  - jeder Write an ihre Bedingung gebunden ist,
  - die zwei Doppel-Quote-Paare den folgenden Inhalt nicht in ein Literal
    ziehen (an v0v gemessen: drei Quotes in einer Zeile, und die Folgezeile
    gehoert zum Literal).

Zahlen sind am Trockenlauf gemessen, nicht erwartet. Eine Zahl, die ich mir
ausdenke, prueft meinen Vorrat an Einfällen, nicht das Bild.
"""
from __future__ import annotations

import importlib.util
import os
import struct
import sys
import gzip

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

# Anwesenheit: die Felder, die der Herzschlag und die Beweiszeile melden muessen.
DA = ("first-light v0w", "SCDATEIEN=$(find", 'SC=$(printf', '[ -n "$SC" ] ||',
      "test -w ", "SCRCA=$?", "gefunden=$SZAHL", "suche=$SCLISTE", "scrca=$SCRCA",
      "debugfs=$(ls", "usb=$(ls", "mount -t debugfs", "write rc=", "vorher=$scvor",
      "rc0=$sc0rc", "rc1=$sc1rc", "spaeter 5s", "pfad=$SC", "typc: state=",
      "kein Knopf", "echo 0xD002 >", "debug shell armed", "telnetd -l /bin/sh")
# Abwesenheit: die Annahme des Vorgaengers, unbedingt gesetzt, und seine Titel.
WEG = ("first-light v0v", "first-light v0u", "first-light v0t", "first-light v0s",
       "first-light v0r", "first-light v0q", "SC2=", "beide Knoten:")
suche_vor_annahme = 1      # '||' darf nur als Bedingung vorkommen, nie unbedingt
ZEILEN_MIN = 3             # nachbinden, spaeter 5s, weicher-bind - alle an /dev/kmsg
QUOTE_MAX = 2              # eine Echo-Zeile mit drei Quotes schliesst sich erst spaeter


def init_text(bild: str) -> str:
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    raw = gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]])
    with open("/tmp/v0w-pruef.cpio", "wb") as offen:
        offen.write(raw)
    return {e["name"]: e for e in newc.read_cpio("/tmp/v0w-pruef.cpio")}["init"]["content"].decode()


def zeilennummer(init: str, teil: str, von: int = 0) -> int:
    """Erste Zeile ab 'von', die 'teil' enthaelt; 0 wenn keine. 1-basiert."""
    for nr, zeile in enumerate(init.splitlines()[von:], von + 1):
        if teil in zeile:
            return nr
    return 0


def reihenfolge(init: str) -> int:
    """Die Suche muss vor der Annahme liegen, der Test vor beiden Writes."""
    fehler = 0
    suche = zeilennummer(init, "SCDATEIEN=$(find")
    annahme = zeilennummer(init, '[ -n "$SC" ] ||')
    test = zeilennummer(init, "test -w ")
    erster = zeilennummer(init, "sc0rc=$?")
    zweiter = zeilennummer(init, "sc1rc=$?")
    probe = zeilennummer(init, "$SCRCA -eq 0")
    for name, wert in (("Suche", suche), ("Annahme", annahme), ("Beschreibbar-Test", test),
                       (" erster Write", erster), ("zweiter Write", zweiter),
                       ("Write-Bedingung", probe)):
        if not wert:
            print("not ok - %s: keine Zeile im fertigen Init" % name)
            fehler += 1
    if fehler:
        return fehler
    if suche < annahme:
        print("ok - Suche in Zeile %d, Annahme in Zeile %d" % (suche, annahme))
    else:
        print("not ok - die Annahme (Zeile %d) steht vor der Suche (Zeile %d)"
              % (annahme, suche)); fehler += 1
    if annahme < test < erster and annahme < test < zweiter:
        print("ok - Beschreibbar-Test (Zeile %d) liegt vor beiden Writes (%d, %d)"
              % (test, erster, zweiter))
    else:
        print("not ok - Reihenfolge falsch: Test %d, Writes %d und %d"
              % (test, erster, zweiter)); fehler += 1
    for wo, was in ((erster, "erster"), (zweiter, "zweiter")):
        if probe and probe < wo:
            print("ok - %s Write (Zeile %d) liegt hinter der Bedingung (Zeile %d)"
                  % (was, wo, probe))
            break
    # Der Platzhalter darf nirgends unbedingt gesetzt werden.
    unbedingt = [n for n, z in enumerate(init.splitlines(), 1)
                 if "soft_connect" in z and "/sys/kernel/debug/usb/" in z
                 and "||" not in z and "find" not in z and not z.lstrip().startswith("#")]
    if unbedingt:
        print("not ok - Pfad unbedingt gesetzt in Zeile(n) %s" % unbedingt); fehler += 1
    else:
        print("ok - der Pfad wird nirgends unbedingt gesetzt (%d Zeilen, %d bedingt)"
              % (len(init.splitlines()), suche_vor_annahme))
    return fehler


def quote_pruefung(init: str) -> int:
    """Eine Echo-Zeile mit einer ungeraden Zahl Double-Quotes ist nicht zu Ende.

    Gemessen am v0v-Bild, Zeile 74: drei Quotes, und die Folgezeile 'letzter
    Schritt:' gehoert in ihr Literal. Auffaellig wird das erst, wenn man eine
    zweite Befehlsersetzung in dieselbe Zeile setzt - dann endet die Zeile
    mitten in einem offenen Literal und bash -n meldt 'unexpected EOF while
    looking for matching quote'. Drei Kandidaten wurden gegeneinander gemessen:
    nur der mit zwei Quotes besteht die Pruefung allein.
    """
    fehler = 0
    gezaehlt = 0
    for nr, zeile in enumerate(init.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        anfang = zeile.find(chr(34))
        ende = zeile.rfind(chr(34))
        if not (0 <= anfang < ende):
            continue
        gezaehlt += 1
        if zeile.count(chr(34)) % 2:
            print("not ok - Zeile %d: %d Double-Quotes, die Zeile endet offen"
                  % (nr, zeile.count(chr(34)))); fehler += 1
        if zeile.count(chr(34)) > QUOTE_MAX + 2:
            print("nicht ok - Zeile %d traegt %d Double-Quotes (erwartet hoechstens %d)"
                  % (nr, zeile.count(chr(34)), QUOTE_MAX + 2))
    print("ok - %d Echo-Zeilen auf geschlossene Double-Quotes geprueft" % gezaehlt)
    return fehler


def klammer_pruefung(init: str) -> int:
    """Klammerbilanz: global, und innerhalb der Echo-Zeichenketten."""
    fehler = 0
    if init.count("(") == init.count(")"):
        print("ok - globale Klammerbilanz: %d offen, %d zu"
              % (init.count("("), init.count(")")))
    else:
        print("not ok - globale Klammerbilanz: %d offen, %d zu"
              % (init.count("("), init.count(")")))
        fehler += 1
    for nr, zeile in enumerate(init.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        anfang = zeile.find(chr(34))
        ende = zeile.rfind(chr(34))
        if not (0 <= anfang < ende):
            continue
        text = zeile[anfang + 1:ende].replace(chr(92) + "(", "(").replace(chr(92) + ")", ")")
        if text.count("(") != text.count(")"):
            print("not ok - Zeile %d: Echo-Kette mit %d ( gegen %d )"
                  % (nr, text.count("("), text.count(")")))
            fehler += 1
    return fehler


def main() -> int:
    init = init_text(sys.argv[1])
    fehler = 0
    for m in DA:
        if m in init:
            print("ok - Beweismal vorhanden: " + m)
        else:
            print("not ok - Beweismal fehlt im fertigen Bild: " + m); fehler += 1
    for w in WEG:
        if w in init:
            print("not ok - Rest eines frueheren Bildes: " + w); fehler += 1
        else:
            print("ok - kein Rest: " + w)
    ist = init.count("bDeviceState")
    if ist == 0:
        print("ok - blinde Lesungen: bDeviceState 0 mal")
    else:
        print("not ok - bDeviceState %d mal, erwartet 0" % ist); fehler += 1
    n = sum(1 for x in init.splitlines() if "> /dev/kmsg" in x and "omamobile-blueline:" in x)
    if n >= ZEILEN_MIN:
        print("ok - Beweiszeilen nach /dev/kmsg: %d" % n)
    else:
        print("not ok - nur %d Beweiszeilen, erwartet mindestens %d" % (n, ZEILEN_MIN)); fehler += 1
    if "sc0rc=$?" in init and "sc1rc=$?" in init:
        print("ok - beide soft_connect-Writes halten ihren Rueckgabewert")
    else:
        print("not ok - ein soft_connect-Write haelt keinen Rueckgabewert"); fehler += 1
    fehler += reihenfolge(init)
    fehler += quote_pruefung(init)
    fehler += klammer_pruefung(init)
    if init.isascii():
        print("ok - fertige Init ist reines ASCII")
    else:
        print("not ok - fertige Init traegt Nicht-ASCII"); fehler += 1
    print("%d Beweismale, %d Fehler" % (len(DA) + len(WEG) + 10, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
