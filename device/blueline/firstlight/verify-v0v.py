#!/usr/bin/env python3
"""v0v-Beweismale am fertigen Bild, als Datei statt als Heredoc.

Regel aus den Vorfahren: kein Dollarzeichen im Heredoc (ash expandiert in der
Bauplatz-Huelle, `set -u` bringt den Pruefer um), also steht alles hier.

Was v0v beweisen soll, ist eine Abwesenheit und eine Anwesenheit:
  - `bDeviceState` 0 mal. Am Kernel-Binary gemessen (44 498 944 Byte entpackt,
    images/fl-v0u/kernel-blob, gzip): der Knoten existiert in diesem Kernel
    nicht (0 Vorkommen des Namens). v0t hat ihn trotzdem gelesen und ein leeres
    Feld bekommen - Dunkelheit, die wie ein Messwert aussah.
  - `soft_connect` vorhanden. Derselbe Blick auf das Kernel-Binary: 2
    Vorkommen, die Datei im debugfs-Zweig von dwc3 existiert. Sie ist der
    einzige Verbindungsknopf, den noch kein Bild gedreht hat, nachdem v0r und
    v0t zweimal hintereinander 0 Beobachtungen in je 302 s geliefert hatten bei
    Panel-Meldung state=not attached.

Ein Beweismittel, das auch das Vorgaengerbild besteht, prueft nichts: die
Zahlen hier sind am Trockenlauf vorgegeben und werden am fertigen Bild
nachgeprueft.
"""
from __future__ import annotations

import gzip
import importlib.util
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

DA = ("first-light v0v", "weicher-bind", "debugfs-geoffnet", "vorher=$scvor",
      "rc0=$sc0rc", "rc1=$sc1rc", "mount -t debugfs", "write rc=", "spaeter 5s",
      "typc: state=", "echo 0xD002 >", "debug shell armed", "telnetd -l /bin/sh")
WEG = ("first-light v0u", "first-light v0t", "first-light v0s", "first-light v0r",
       "first-light v0q", "beide Knoten:")
ZAHL_BDEVICESTATE = 0      # Knoten existiert nicht (Kernel-Binary, 0 Vorkommen)
ZAHL_PFAD = 2              # der Sucher nennt zwei Kandidaten (Pfad und Platzhalter)
KLAMMERN = True            # jede Zeile muss Klammern und Quotes balancieren
ZEILEN_MIN = 3             # nachbinden, spaeter 5s, weicher-bind - alle an /dev/kmsg


def init_text(bild: str) -> str:
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    raw = gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]])
    with open("/tmp/v0v-pruef.cpio", "wb") as offen:
        offen.write(raw)
    return {e["name"]: e for e in newc.read_cpio("/tmp/v0v-pruef.cpio")}["init"]["content"].decode()


def klammer_pruefung(init: str) -> int:
    """Klammerbilanz: global, und innerhalb der Echo-Zeichenketten.

    Grund: eine Beweiszeile hatte ein Paren zu viel, und kein Pruefer meldete es
    - auf dem Panel ist das unsichtbarer Text, keine Fehlermeldung. Die
    Pro-Zeile-Zaehlung, die das zuerst versuchen sollte, fand 28 'fehlerhafte'
    Zeilen, die alle echt waren: eine '( ... ) &' balanciert ueber Zeilen.

    Die Double-Quotes pro Zeile werden nicht gezaehlt. Sie waeren immer gerade
    und haetten nie einen Defekt gefunden, nur eine Zahl geliefert.
    """
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
            print("not ok - Rest eines frueheren Panel-Titels: " + w); fehler += 1
        else:
            print("ok - kein Titel-Rest: " + w)
    ist = init.count("bDeviceState")
    if ist == ZAHL_BDEVICESTATE:
        print("ok - blinde Lesungen: bDeviceState %d mal (erwartet %d)" % (ist, ZAHL_BDEVICESTATE))
    else:
        print("not ok - bDeviceState %d mal, erwartet %d" % (ist, ZAHL_BDEVICESTATE)); fehler += 1
    pfad = sum(1 for x in init.splitlines()
               if (x.lstrip().startswith("SC=") or x.lstrip().startswith("SC2="))
               and "soft_connect" in x)
    if pfad == ZAHL_PFAD:
        print("ok - soft_connect-Pfad genau %d mal gesetzt" % pfad)
    else:
        print("not ok - soft_connect-Pfad %d mal gesetzt, erwartet %d" % (pfad, ZAHL_PFAD)); fehler += 1
    n = sum(1 for x in init.splitlines() if "> /dev/kmsg" in x and "omamobile-blueline:" in x)
    if n >= ZEILEN_MIN:
        print("ok - Bindblock schreibt %d Beweiszeilen nach /dev/kmsg" % n)
    else:
        print("not ok - nur %d Beweiszeilen, erwartet mindestens %d" % (n, ZEILEN_MIN)); fehler += 1
    # Beide weichen Writes muessen ihren Rueckgabewert behalten, sonst ist der
    # Knopf gedrueckt und die Antwort verloren.
    if "sc0rc=$?" in init and "sc1rc=$?" in init:
        print("ok - beide soft_connect-Writes halten ihren Rueckgabewert")
    else:
        print("not ok - ein soft_connect-Write haelt keinen Rueckgabewert"); fehler += 1
    form = klammer_pruefung(init)
    fehler += form
    if init.isascii():
        print("ok - fertige Init ist reines ASCII")
    else:
        print("not ok - fertige Init traegt Nicht-ASCII"); fehler += 1
    print("%d Beweismale, %d Fehler" % (len(DA) + len(WEG) + 6, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
