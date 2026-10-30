#!/usr/bin/env python3
"""Zeigt die Zeichenketten um soft_connect im Kernel-Image, mit Adresse.

Grund: v0v schreibt die soft_connect-Datei unter einem Pfad, den ich aus der
Erinnerung gebaut hatte ('/sys/kernel/debug/usb/<udc-name>/soft_connect'). Ob
der Zwischenpfad existiert und wie das Verzeichnis wirklich heisst, steht nur in
den Zeichenketten des Kernels. Zwei fruhere Annahmen waren schon Vermutungen,
die ein Bild nicht getroffen hat - also nachsehen, nicht wissen.

Der Kernel in images/fl-v0u/kernel-blob ist gzip (16 154 423 B, entpackt
44 498 944 B). Busybox-grep kennt kein -b, deshalb Python.

Aufruf:  python3 kernel-zeichen.py <kernel-blob> [suchbegriff ...]
"""
import gzip
import sys
import zlib

SUCHE = ["soft_connect", "usb/%s", "gadget/%s", "dwc3", "debug_enabled",
         "/sys/kernel/debug", "a600000"]


def hole_members(pfad: str) -> list[bytes]:
    """Alle gzip-Glieder der Datei, in Reihenfolge.

    kernel-blob ist kein Einzelfall-Stream: nach dem Kernel folgt in derselben
    Datei ein zweites Glied, das mit d0 0d (DTB-Magic) beginnt. Python-
    `gzip.open` liest nur das erste Glied und meldet beim naechsten Kopf
    'Not a gzipped file'; `gzip -dc` haengt beide aneinander. Wer hier nur ein
    Glied liest, sucht in einem Teil des Kernels und halt ein Nicht-Finden fuer
    eine Abwesenheit.
    """
    rohb = open(pfad, "rb").read()
    glieder = []
    # Ein Glied nach dem anderen: `decompress` gibt den nicht verbrauchten Rest
    # zurueck, der wird der neue Anfang. Eine Bedingung, die auf dem ersten Wurf
    # abbricht, liesse den Rest des Kernels ungelesen (und ein Nicht-Finden ist
    # dann keine Abwesenheit, sondern Nicht-Lesen).
    while rohb[:2] == b"\x1f\x8b":
        de = zlib.decompressobj(16 + zlib.MAX_WBITS)
        glieder.append(de.decompress(rohb))
        rohb = de.unconsumed_tail
    return glieder


def haupt() -> int:
    quelldatei = sys.argv[1]
    suche = sys.argv[2:] or SUCHE
    glieder = hole_members(quelldatei)
    daten = b"".join(glieder)
    print("entpackt: %d Byte in %d Glied(ern), Groessen %s"
          % (len(daten), len(glieder), [len(g) for g in glieder]))
    for begriff in suche:
        Stellen = []
        von = 0
        while True:
            i = daten.find(begriff.encode(), von)
            if i < 0:
                break
            Stellen.append(i)
            von = i + 1
            if len(Stellen) > 40:
                break
        print()
        print("=== %r: %d Fundstelle(n)%s" % (
            begriff, len(Stellen), ", erste 12 gezeigt" if len(Stellen) > 12 else ""))
        for i in Stellen[:12]:
            kontext = daten[max(0, i - 24):i + len(begriff) + 24]
            # Nur druckbares, damit die Ausgabe lesbar bleibt.
            zeichen = "".join(chr(c) if 32 <= c < 127 else "." for c in kontext)
            print("  0x%08x  %s" % (i, zeichen))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
