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
import argparse
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


def schreibe(pfad_bild, pfad_sparse, vorlauf=0):
    """Bilder mit vollen Brocken, einem Reststueck und Loechern fuer Nullserien.

    Zwei Gruende, beide gemessen. Erstens: ein Bild von 1 MiB Vorlauf + 1 GiB ist
    kein Vielfaches von 16 MiB — die erste Brockengroessen-Fassung wies es ab, und
    die Ablehnung verschwand hinter 'python3 … | tail -4 && sh …', weil die
    Rohrleitung den Exit von tail meldet; zwei Write liefen auf dem alten Bild.
    Zweitens, und der teurere: fastboot zerlegt eine 1-GiB-Uebertragung in fuenf
    Sitzungen zu je 262141 KB (max-download-size 268435456). Der erste Hanger blieb
    beim Uebergang von 'Sending 1/5' auf 'Sending 2/5' stehen. Ein echtes
    Sparse-Bild mit DONT_CARE fuer die Nullserien (img2simg macht das so) bleibt mit
    seinem Inhalt von ~60 MiB in EINER Sitzung.

    Achtung, damit die runde Pruefung nicht fuehrt: ein DONT_CARE schreibt das
    Feld NICHT, dort steht nach dem Write Alteres. Der Round-trip füllt die
    Loecher mit Nullen und vergleicht gegen das Rohbild — was das wirklich belegt,
    ist die Summe der DATA-Brocken. Beides wird ausgegeben.
    """
    groesse = vorlauf + os.path.getsize(pfad_bild)
    if groesse % BLOCK:
        raise SystemExit("Bildgroesse %d ist kein Vielfaches von %d" % (groesse, BLOCK))
    saecke = groesse // BLOCK
    brocken = (groesse + BLOCK * SAECKE - 1) // (BLOCK * SAECKE)
    daten_brocken = loecher = daten_byte = 0
    mit = open(pfad_bild, "rb")
    Z = open(pfad_sparse, "wb")
    Z.write(struct.pack("<IHHHHIIII", MAGIC, 1, 0, 28, 12, BLOCK, saecke,
                        brocken + 1, 0))
    for nr in range(brocken):
        null_byte = min(vorlauf, BLOCK * SAECKE)
        leib = bytes(null_byte) + mit.read(BLOCK * SAECKE - null_byte)
        vorlauf -= null_byte
        if not leib or len(leib) % BLOCK:
            raise SystemExit("Brocken %d hat %d Byte" % (nr, len(leib)))
        if leib.strip(b"\0") == b"":
            Z.write(struct.pack("<III", DONTCARE, len(leib) // BLOCK, 12))
            loecher += 1
        else:
            Z.write(struct.pack("<III", RAW, len(leib) // BLOCK, 12 + len(leib)))
            Z.write(leib)
            daten_brocken += 1
            daten_byte += len(leib)
        if nr + 1 == brocken or (nr + 1) % 8 == 0:
            print("  Brocken %d/%d (%s, %d B)"
                  % (nr + 1, brocken, "Loch" if leib.strip(b"\0") == b"" else "Daten",
                     len(leib)), flush=True)
    Z.write(struct.pack("<III", DONTCARE, 0, 12))          # Abschluss, wie img2simg
    mit.close()
    Z.close()
    return daten_brocken, loecher, daten_byte


def lies(pfad_sparse):
    """Hash und Blockzahlen des rekonstruierten Images berechnen."""
    magic, major, minor, fgroesse, chgroesse, block, saecke, anzahl, pruef = \
        struct.unpack("<IHHHHIIII", open(pfad_sparse, "rb").read(28))
    assert magic == MAGIC and major == 1 and fgroesse == 28 and chgroesse == 12, \
        "Kopf nicht dicht: %s" % hex(magic)
    digest = hashlib.sha256()
    nullen = bytes(BLOCK * SAECKE)
    daten_baelle = care = blocke = 0
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
            digest.update(leib)
            daten_baelle += 1
            blocke += stueck
        elif art == DONTCARE:
            if stueck == 0:
                break
            rest = stueck * block
            while rest:
                laenge = min(rest, len(nullen))
                digest.update(nullen[:laenge])
                rest -= laenge
            blocke += stueck
            care += 1
        else:
            raise SystemExit("unerwarteter Sacktyp %s" % hex(art))
    mit.close()
    return digest.hexdigest(), daten_baelle, care, blocke


def anzahl_brocken(pfad_sparse):
    """Nachzaehlen, was wirklich im Kopf steht — nicht, was wir wollten."""
    _, _, _, _, _, _, _, anzahl, _ = struct.unpack(
        "<IHHHHIIII", open(pfad_sparse, "rb").read(28))
    return max(anzahl - 1, 0)


def datei_sha256(pfad, vorlauf=0):
    digest = hashlib.sha256()
    while vorlauf:
        null_byte = min(vorlauf, 1024 * 1024)
        digest.update(bytes(null_byte))
        vorlauf -= null_byte
    with open(pfad, "rb") as datei:
        for daten in iter(lambda: datei.read(1024 * 1024), b""):
            digest.update(daten)
    return digest.hexdigest()


def haupt():
    parser = argparse.ArgumentParser(description="Pack an Android sparse image.")
    parser.add_argument("bild")
    parser.add_argument("sparse")
    parser.add_argument("--prefix-bytes", type=int, default=0,
                        help="prepend this many zero bytes before the input image")
    args = parser.parse_args()
    bild, sparse, vorlauf = args.bild, args.sparse, args.prefix_bytes
    if vorlauf < 0 or vorlauf % BLOCK:
        parser.error("--prefix-bytes must be a non-negative multiple of 4096")
    groesse = vorlauf + os.path.getsize(bild)
    echt = datei_sha256(bild, vorlauf)
    daten_brocken, loecher, daten_byte = schreibe(bild, sparse, vorlauf)
    rueck, daten_baelle, care, blocke = lies(sparse)
    rueckgroesse = blocke * BLOCK
    print("_sparse_: %s, %d B — geschrieben werden %d DATA-Brocken = %d B, "
          "dazu %d DONT_CARE (Kopf kuendigt %d Saecke an, Abschluss ja)"
          % (os.path.basename(sparse), os.path.getsize(sparse), daten_brocken,
             daten_byte, loecher, anzahl_brocken(sparse)))
    sitzung = 268435456
    print("Sitzungen bei max-download-size %d B: %d  (eine Sitzung ist das Ziel)"
          % (sitzung, 1 + (os.path.getsize(sparse) - 1) // sitzung))
    print("Rohbild %d B sha %s" % (groesse, echt[:16]))
    print("zurueckgelesen %d B sha %s -> %s" % (rueckgroesse, rueck[:16],
                                                "dicht" if rueck == echt else "LOCH"))
    if rueck != echt or rueckgroesse != groesse:
        return 1
    sparse_sha = datei_sha256(sparse)
    with open(sparse + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (sparse_sha, os.path.basename(sparse)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
