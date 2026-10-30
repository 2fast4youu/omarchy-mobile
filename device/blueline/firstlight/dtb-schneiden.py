#!/usr/bin/env python3
"""DTB-Belege aus boot-Image-Dateien herausschneiden und benennen.

Grund: ein erster Vergleich von Referenz-DTB und v0r-DTB lief in zwei leere
Ordner, ohne dass eine Zeile Fehler fiel. Dieser Schnitt schneidet den
Flattened-Device-Tree-Block heraus, prueft Kopf und Gesamtlaenge und meldet
jeden Fall, in dem gar nichts herauskommt, als Fehler (Exit 1) - Dunkelheit
darf nicht als Erfolg durchgehen.

Aufbau eines Android-Boot-Image v3: 4096 Byte Kopf, danach Seiten mit
kernel / ramdisk / dtb. Die DTB steht oft nicht im Kopf-verzeichnet, sondern
wird als roher Block angehaengt (Magic d0 0d fe ed, dann 4 Byte Gesamtlaenge).
"""
import struct
import sys

MAGIC = b"\xd0\x0d\xfe\xed"


def dtb_belege(daten: bytes):
    """Alle Plausibilitaets-Kandidaten: (offset, laenge) mit stimmiger Laenge."""
    funde = []
    for versatz in range(0, len(daten) - 8):
        if daten[versatz:versatz + 4] != MAGIC:
            continue
        laenge = struct.unpack(">I", daten[versatz + 4:versatz + 8])[0]
        # Eine echte DTB ist mindestens ein paar hundert Byte und endet
        # innerhalb der Datei; die Laenge ist ein 32-Bit-Wert, kein Muell.
        if 400 <= laenge <= 4_000_000 and versatz + laenge <= len(daten):
            funde.append((versatz, laenge))
    return funde


def schneiden(quelle: str, ziel_ordner: str) -> int:
    daten = open(quelle, "rb").read()
    funde = dtb_belege(daten)
    if not funde:
        print("FEHLER: %s enthaelt keinen plausiblen DTB-Block (%d Byte)" % (quelle, len(daten)))
        return 1
    print("%s: %d Kandidat(en) in %d Byte" % (quelle, len(funde), len(daten)))
    for nr, (versatz, laenge) in enumerate(funde):
        block = daten[versatz:versatz + laenge]
        # Kein Leerzeichen im Namen: ein Pfad wie 'd/ dtb.dtb' findet dtc nicht,
        # und ein Diff zweier leerer Ausgabedateien meldet 'kein Unterschied'.
        ziel = "%s/dtb-%08x-%d.dtb" % (ziel_ordner.rstrip("/"), versatz, nr)
        with open(ziel, "wb") as out:
            out.write(block)
        print("  offset 0x%08x  laenge %d  -> %s" % (versatz, laenge, ziel))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Aufruf: dtb-schneiden.py <boot.img> <ziel_ordner>")
        raise SystemExit(2)
    raise SystemExit(schneiden(sys.argv[1], sys.argv[2]))
