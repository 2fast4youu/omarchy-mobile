#!/usr/bin/env python3
"""v0t-Beweismale am fertigen Bild, als Datei statt als Heredoc.

Grund fuer die Auslagerung (gemessen, nicht vermutet): der Zusammenbau laeuft in
der Alpine-Box unter `sh -euc`, also ash. Ash kennt die bash-Escapeform \" nicht,
eine Markierung wie "echo 0xD002 > \\"$CONFIGFS/g1/idProduct\\"" wird dort
expandiert, und `set -u` bringt den Pruefer mit 'CONFIGFS: parameter not set' um
— nach 28/0 des Bautests, ohne dass am Bild etwas zu beanstanden waere. Das
v0s-Rezept haelt die Regel ein ('Der Heredoc traegt keine Dollarzeichen'); diese
Datei haelt sie fuer v0t.

Laeuft in der Box:  python3 /om/verify-v0t.py /r/firstlight.img
Laeuft auf dem Mac: python3 verify-v0t.py <Bild>   (derselbe Code, kein Pfadzwang)
"""
from __future__ import annotations

import gzip
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

# Markierungen ohne Dollarzeichen und ohne Anführungszeichen: sie ueberleben
# jede Shell, die den Aufruf umgibt, und sind trotzdem lang genug, um eine
# verlorene Zeile zu erkennen.
DA = ("first-light v0t", "beide Knoten: state=", "echo 0xD002 >",
      "debug shell armed", "controller-state=", "bDeviceState",
      "telnetd -l /bin/sh")
WEG = ("first-light v0s", "first-light v0r", "first-light v0q")
ZAHL_BDEVICESTATE = 4     # gemessen am v0s-Bild: 2, plus 2 aus der Doppelzeile


def init_text(bild: str) -> str:
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    raw = gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]])
    offen = open("/tmp/v0t-pruef.cpio", "wb"); offen.write(raw); offen.close()
    return {e["name"]: e for e in newc.read_cpio("/tmp/v0t-pruef.cpio")}["init"]["content"].decode()


def main() -> int:
    bild = sys.argv[1]
    init = init_text(bild)
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
        print("ok - bDeviceState %d mal wie vorgerechnet" % ist)
    else:
        print("not ok - bDeviceState %d mal, erwartet %d" % (ist, ZAHL_BDEVICESTATE)); fehler += 1
    if init.isascii():
        print("ok - fertige Init ist reines ASCII")
    else:
        print("not ok - fertige Init traegt Nicht-ASCII"); fehler += 1
    print("%d Beweismale, %d Fehler" % (len(DA) + len(WEG) + 2, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
