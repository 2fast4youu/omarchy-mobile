#!/usr/bin/env python3
"""v0u-Beweismale am fertigen Bild, als Datei statt als Heredoc.

Grund fuer die Auslagerung (gemessen, nicht vermutet): der Zusammenbau laeuft in
der Alpine-Box unter `sh -euc`, also ash. Ash kennt die bash-Escapeform \\\" nicht
und expandiert Dollarzeichen auch in Markierungen; `set -u` bringt den Pruefer
dann mit 'CONFIGFS: parameter not set' um - nach 28/0 des Bautests, ohne dass am
Bild etwas zu beanstanden waere. Diese Datei haelt die Regel 'kein Dollarzeichen
im Heredoc' fuer v0u.

Was hier Beweismal ist, ist die *Abwesenheit*: v0u nimmt alle blinden Lesungen
des Knotens bDeviceState raus (im v0t-Bild 4 mal in 3 Zeilen, gemessen). Eine
Zeile, deren Ausgabefeld auf diesem Kernel nachweislich immer leer bleibt, ist
kein Messwert. 0 Vorkommen sind deshalb die Zahl, die der Bau treffen muss -
nicht 'beliebig viel'.

Laeuft in der Box:  python3 /om/verify-v0u.py /r/firstlight.img
Laeuft auf dem Mac: python3 verify-v0u.py <Bild>   (derselbe Code, kein Pfadzwang)
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

# Markierungen ohne Dollarzeichen: sie ueberleben jede Shell um den Aufruf.
DA = ("first-light v0u", "write rc=", "spaeter 5s", "typc: state=",
      "udc-state=", "is_active=", "controller-state=", "echo 0xD002 >",
      "debug shell armed", "telnetd -l /bin/sh")
WEG = ("first-light v0t", "first-light v0s", "first-light v0r", "first-light v0q",
       "beide Knoten:")
ZAHL_BDEVICESTATE = 0     # vor Gerechnet: v0u nimmt alle vier raus
NEUZEILEN_MIN = 2         # nachbinden-Zeile und spaeter-5s-Zeile, beide an/kmsg


def init_text(bild: str) -> str:
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    raw = gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]])
    with open("/tmp/v0u-pruef.cpio", "wb") as offen:
        offen.write(raw)
    return {e["name"]: e for e in newc.read_cpio("/tmp/v0u-pruef.cpio")}["init"]["content"].decode()


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
        print("not ok - bDeviceState %d mal, erwartet %d: eine blinde Lesung steht noch drin"
              % (ist, ZAHL_BDEVICESTATE)); fehler += 1
    n = sum(1 for x in init.splitlines() if "nachbinden $rb" in x and "> /dev/kmsg" in x)
    if n >= NEUZEILEN_MIN:
        print("ok - Bindblock schreibt %d Beweiszeilen nach /dev/kmsg" % n)
    else:
        print("not ok - Bindblock schreibt nur %d Beweiszeilen, erwartet mindestens %d"
              % (n, NEUZEILEN_MIN)); fehler += 1
    # Der Rueckgabewert des binden-write muss gehalten werden: ohne rc=$? ist
    # die Ursache weg, auch wenn ein 2>&1 irgendwo im Text steht (ein erster
    # Pruefer auf 2>&1 blieb blind, weil v0t die Form schon an anderer Stelle
    # traegt - ein Merkmal, das auch das Alt Bild zeigt, prueft nichts).
    if "rc=$?" in init:
        print("ok - Rueckgabewert des binden-write wird gehalten (rc=$?)")
    else:
        print("not ok - binden-write haelt keinen Rueckgabewert"); fehler += 1
    if init.isascii():
        print("ok - fertige Init ist reines ASCII")
    else:
        print("not ok - fertige Init traegt Nicht-ASCII"); fehler += 1
    print("%d Beweismale, %d Fehler" % (len(DA) + len(WEG) + 4, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
