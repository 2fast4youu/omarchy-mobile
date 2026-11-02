#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rohes Bild -> echtes Android-Sparse-Image, ohne Loecher.

Grund (gemessen 2026-11-02, 16:53): `fastboot flash userdata rootfs.ext4` meldet
'Invalid sparse file format at header magic' und rechnet selbst um — dabei
schickt es 9588 KB fuer ein 1-GiB-Bild und laesst genau die Baelle 4096 und 8192
ungefroren: auf der Partition steht bei 4096 'EFI PART' und bei 8192 der alte
Partitionssatz, waehrend 1024 und 65536 dicht sind. Der Kernel liest die
Gruppenbeschreiber bei 8192, findet GUID-Byte und meldet 'group descriptors
corrupted'. Ein eigenes Sparse-Image nimmt dem Sender die Umrechnung weg: es
traegt alle 4096-Byte-Baelle als DATA, auch die Nullen, also schreibt das
Telefon von Anfang bis Ende durch.

Nach dem Schreiben wird zurueckgelesen und die Bytefolge des rekonstruierten
Stroms gegen die sha256 des Rohbilds gerechnet. Ein Sparse-Image, das nicht
dicht zurueckkommt, wird nicht flashed.
"""
import hashlib
import os
import struct
import sys

MAGIC = 0xED26FF3A          # im Text als 3A FF 26 ED; 0x3AFF26EA ist falsch
                           # und wurde von fastboot mit 'Invalid sparse file format
                           # at header magic' abgelehnt (gemessen 2026-11-02, 17:00)
RAW = 0xCAC1
DONTCARE = 0xCAC3
BLOCK = 4096
# Ein Sack pro 4096-Byte-Block ist erlaubt, aber fuer ABOOT Gift: der Write mit
# 262400 Ein-Block-Saecken kam nach 9 Minuten nicht durch, der Prozess hing mit
# eingefrorener Rechenzeit am Gerat (gemessen 17:2x). Echte Sparse-Bilder
# (img2simg) fassen zusammen, also 4096 Baelle = 16 MiB pro Sack, hier 64 Saecke.
SAECKE = 4096


def schreibe(pfad_bild, pfad_sparse):
    groesse = os.path.getsize(pfad_bild)
    if groesse % (BLOCK * SAECKE):
        raise SystemExit("Bildgroesse %d ist kein Vielfaches von %d"
                         % (groesse, BLOCK * SAECKE))
    saecke = groesse // BLOCK
    bruchstuecke = groesse // (BLOCK * SAECKE)
    gesendet = 0
    with open(pfad_bild, "rb") as Quelle, open(pfad_sparse, "wb") as Z:
        Z.write(struct.pack("<IHHHHIIII", MAGIC, 1, 0, 28, 12, BLOCK, saecke,
                            bruchstuecke + 1, 0))
        for nr in range(bruchstuecke):
            leib = Quelle.read(BLOCK * SAECKE)
            if len(leib) != BLOCK * SAECKE:
                raise SystemExit("Bild bricht im Brocken %d ab" % nr)
            Z.write(struct.pack("<III", RAW, SAECKE, 12 + len(leib)))
            Z.write(leib)
            gesendet += 1
            print("  Brocken %d/%d" % (gesendet, bruchstuecke), flush=True)
        Z.write(struct.pack("<III", DONTCARE, 0, 12))      # Abschluss, wie img2simg
    return gesendet


def lies(pfad_sparse):
    """Strom zuruecklesen: (Bytefolge, Zahl der DATA-Baelle, Zahl der DONT_CARE)."""
    magic, major, minor, fgroesse, chgroesse, block, saecke, anzahl, pruef = \
        struct.unpack("<IHHHHIIII", open(pfad_sparse, "rb").read(28))
    assert magic == MAGIC and major == 1 and fgroesse == 28 and chgroesse == 12, \
        "Kopf nicht dicht: %s" % hex(magic)
    daten = bytearray()
    daten_baelle = care = 0
    mit = open(pfad_sparse, "rb")
    mit.read(fgroesse)
    while True:
        satz = mit.read(chgroesse)
        if len(satz) < chgroesse:
            break
        art, stueck, gesamt = struct.unpack("<III", satz)
        if art == RAW:
            leib = mit.read(stueck * block)
            assert len(leib) == stueck * block, "DATA-Sack zu kurz"
            daten += leib
            daten_baelle += 1
        elif art == DONTCARE:
            if stueck == 0:
                break
            daten += b"\0" * (stueck * block)
            care += 1
        else:
            raise SystemExit("unerwarteter Sacktyp %s" % hex(art))
    mit.close()
    return bytes(daten), daten_baelle, care


def anzahl_brocken(pfad_sparse):
    """Nachzaehlen, was wirklich im Kopf steht — nicht, was wir wollten."""
    _, _, _, _, _, _, _, anzahl, _ = struct.unpack(
        "<IHHHHIIII", open(pfad_sparse, "rb").read(28))
    return max(anzahl - 1, 0)


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-sparse.py BILD.EXT4 BILD.SPARSE")
        return 2
    bild, sparse = sys.argv[1], sys.argv[2]
    groesse = os.path.getsize(bild)
    echt = hashlib.sha256(open(bild, "rb").read()).hexdigest()
    anzahl = schreibe(bild, sparse)
    strom, daten_baelle, care = lies(sparse)
    rueck = hashlib.sha256(strom).hexdigest()
    print("_sparse_: %s, %d B, %d DATA-Baelle in %d Brocken, %d DONT_CARE, Abschluss ja"
          % (os.path.basename(sparse), os.path.getsize(sparse), daten_baelle,
             anzahl_brocken(sparse), care))
    print("Rohbild %d B sha %s" % (groesse, echt[:16]))
    print("zurueckgelesen %d B sha %s -> %s" % (len(strom), rueck[:16],
                                                "dicht" if rueck == echt else "LOCH"))
    if rueck != echt or daten_baelle * BLOCK != groesse:
        return 1
    with open(sparse + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (hashlib.sha256(open(sparse, "rb").read()).hexdigest(),
                              os.path.basename(sparse)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
