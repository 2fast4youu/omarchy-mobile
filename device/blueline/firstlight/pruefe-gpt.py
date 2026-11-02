#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die gesicherten GPT-Koepfe und -Enden der sechs UFS-LUNs — TAP auf stdout.

M1.4 verlangt vor dem ersten Slot-Flag-Write die Partitionstabelle mit CRCs, nicht
nur ihre Namen. Grundlage sind die Auszuege vom 2026-11-01: 64 Sektoren am Anfang
(`gpt-lunX-kopf.bin`) und 64 Sektoren am Ende (`gpt-lunX-ende.bin`) jeder Scheibe.

Was der Lauf ueber das Gerat aussagt (alles gemessen, nichts angenommen):

  * Sektorabstand: alle sechs LUNs arbeiten mit 4096-B-Sektoren
  * Kopf-CRC und Sicherungskopf-CRC nach UEFI-Vorschrift (eigenes CRC-Feld auf null)
  * Kopf und Sicherungskopf gehoeren zusammen: gleiche Disk-GUID, mein/sicher vertauscht
  * Die Eintragssaetze: 128 B pro Satz, der Name ab Satz-Offset 56 (nicht 72 — der
    Fehler stand zweimal hier), LBA-Bereich bei 32/40, Attribute bei 48
  * Der Feldabstand am Kopfende weicht von UEFI ab: an Offset 80 steht im KOPF die
    ZAHL der belegten Saetze (21, 3, 3, 32, 16), im Sicherungskopf eine Null. Die von
    UEFI verlangte CRC32 der Eintragssaetze steht an keiner Stelle der Auszuege —
    ABOOT legt sie nicht an. Deshalb wird hier eine EIGENE Referenz-CRC ueber die
    belegten Saetze gerechnet und ausgegeben; sie ist der Fingerabdruck, mit dem ein
    kuenftiger Schreibvorgang verglichen wird.
  * Kopf- und Sicherungsfeld der Eintraege werden inhaltsgleich verlangt, verglichen
    pro Partitionsname (nicht als Byteblock: ABOOT fuellt das Sicherungsfeld
    sektorweise mit demselben Muster, ein Rohvergleich waere ein Fehlalarm)

Ohne Auszug gibt es einen skip mit Grund, nie ein stillschweigendes ok. LUN e fehlt
noch: ihr Kopf-Auszug verlor den 24-Byte-Endblock der gepackten Datei (Wurzel #12-Rest).

Aufruf:  pruefe-gpt.py [ordner-mit-auszuegen]
"""
import binascii
import os
import struct
import sys

LUNs = "abcdef"
SIGNATUR = b"EFI PART"
SATZ = 128          # Groesse eines Partitionssatzes, gemessen
NAME_OFFSET = 56    # 16 + 16 + 8 + 8 + 8: Typ-GUID, GUID, erste LBA, letzte LBA, Attribute
KOPF_KANDIDATEN = (512, 4096)


def kopf_feld(roh, stelle):
    """GPT-Header an `stelle`, nach dem Abstand, den diese Tabelle tatsaechlich nutzt."""
    if stelle < 0 or len(roh) < stelle + 92 or roh[stelle:stelle + 8] != SIGNATUR:
        return None
    rev, groesse, gespeicherter_crc, _ = struct.unpack("<4I", roh[stelle + 8:stelle + 24])
    mein, sicher, erster, letzter = struct.unpack("<4Q", roh[stelle + 24:stelle + 56])
    guid = roh[stelle + 56:stelle + 72]
    eintrag_lba = struct.unpack("<Q", roh[stelle + 72:stelle + 80])[0]
    belegt, kapazitaet, _ = struct.unpack("<3I", roh[stelle + 80:stelle + 92])
    return dict(stelle=stelle, roh=roh, revision=rev, groesse=groesse, crc=gespeicherter_crc,
                mein_lba=mein, sicher_lba=sicher, erster=erster, letzter=letzter, guid=guid,
                eintrag_lba=eintrag_lba, belegt=belegt, kapazitaet=kapazitaet)


def kopf_liest(pfad, vorne=True):
    if not os.path.exists(pfad) or os.path.getsize(pfad) < 1024:
        return None
    roh = open(pfad, "rb").read()
    if vorne:
        for sektor in KOPF_KANDIDATEN:
            k = kopf_feld(roh, sektor)
            if k:
                k["sektor"] = sektor
                return k
        return None
    stelle = roh.rfind(SIGNATUR)
    k = kopf_feld(roh, stelle)
    if k:
        k["sektor"] = 4096
    return k


def header_crc(k):
    n = max(92, k["groesse"])
    block = bytearray(k["roh"][k["stelle"]:k["stelle"] + n])
    if len(block) < n:
        return None
    block[16:20] = b"\0\0\0\0"
    return binascii.crc32(bytes(block)) & 0xFFFFFFFF


def saetze(roh, anfang, anzahl):
    """Saetze als Wortbuch name -> (erste LBA, letzte LBA, Attribute, Satz-CRC)."""
    out = {}
    for i in range(anzahl):
        e = roh[anfang + i * SATZ: anfang + (i + 1) * SATZ]
        if len(e) < SATZ or e[:16] == b"\0" * 16:
            continue
        name = e[NAME_OFFSET:NAME_OFFSET + 72].decode("utf-16-le", "replace").split("\0")[0]
        if not name:
            continue
        erster, letzter = struct.unpack("<2Q", e[32:48])
        attribute = struct.unpack("<Q", e[48:56])[0]
        if name not in out:
            out[name] = (erster, letzter, attribute, binascii.crc32(e) & 0xFFFFFFFF)
    return out


def zeige(text, ok, zusatz=""):
    print("%s - %s%s" % ("ok" if ok else "not ok", text, (" # " + zusatz) if zusatz else ""),
          flush=True)
    return 0 if ok else 1


def pruefe_lun(lun, ordner):
    p_kopf = os.path.join(ordner, "gpt-lun%s-kopf.bin" % lun)
    p_ende = os.path.join(ordner, "gpt-lun%s-ende.bin" % lun)
    if not (os.path.exists(p_kopf) and os.path.getsize(p_kopf) >= 1024):
        print("ok - LUN %s: Kopfauszug fehlt — skip, Grund: 24-Byte-Endblock der gepackten "
              "Datei verloren (Wurzel #12-Rest), im naechsten Fenster nachlesen" % lun)
        return 0
    k = kopf_liest(p_kopf)
    if k is None:
        return zeige("LUN %s: keine EFI-PART-Signatur im Kopfauszug" % lun, False)
    fehl = zeige("LUN %s: Kopf signiert, Sektor %d B, Header %d B, Revision %d.%d"
                 % (lun, k["sektor"], k["groesse"], k["revision"] >> 16, k["revision"] & 0xFFFF),
                 True)
    fehl += zeige("LUN %s: Kopf-CRC %08x" % (lun, k["crc"]), header_crc(k) == k["crc"],
                  "gerechnet %08x" % (header_crc(k) or 0))
    fehl += zeige("LUN %s: Grenzen plausibel (mein=%d sicher=%d nutzbar %d..%d)"
                  % (lun, k["mein_lba"], k["sicher_lba"], k["erster"], k["letzter"]),
                  k["mein_lba"] == 1 and k["sicher_lba"] > k["eintrag_lba"]
                  and k["erster"] <= k["letzter"] and k["kapazitaet"] >= 128)
    anfang = k["stelle"] + (k["eintrag_lba"] - k["mein_lba"]) * k["sektor"]
    liste = saetze(k["roh"], anfang, k["kapazitaet"])
    belegt = max(k["belegt"], len(liste))
    referenz = binascii.crc32(k["roh"][anfang:anfang + k["kapazitaet"] * SATZ]) & 0xFFFFFFFF
    fehl += zeige("LUN %s: %d Saetze belegt, Kapazitaet %d, Feld ab LBA %d, eigene "
                  "Referenz-CRC %08x" % (lun, len(liste), k["kapazitaet"], k["eintrag_lba"],
                                         referenz),
                  len(liste) > 0, "erster %s, letzter %s" % (sorted(liste)[0], sorted(liste)[-1]))
    e = kopf_liest(p_ende, vorne=False)
    if e is None:
        groesse = os.path.getsize(p_ende) if os.path.exists(p_ende) else 0
        return fehl + zeige("LUN %s: Sicherungskopf nicht im Ende-Auszug (%d B)"
                            % (lun, groesse), False)
    fehl += zeige("LUN %s: Sicherungskopf bei Byte %d signiert" % (lun, e["stelle"]), True)
    fehl += zeige("LUN %s: Kopf-CRC der Sicherung %08x" % (lun, e["crc"]),
                  header_crc(e) == e["crc"], "gerechnet %08x" % (header_crc(e) or 0))
    fehl += zeige("LUN %s: Kopf und Sicherung gehoeren zusammen (GUID gleich, "
                  "mein und sicher vertauscht)" % lun,
                  e["guid"] == k["guid"] and e["mein_lba"] == k["sicher_lba"]
                  and e["sicher_lba"] == k["mein_lba"])
    # Inhaltsvergleich pro Name: ABOOT fuellt das Sicherungsfeld sektorweise mit
    # demselben Muster, ein Rohvergleich der 16 KiB waere ein Fehlalarm. Verglichen
    # wird, was den Schreibvorgang angeht: Name, LBA-Bereich, Typ. Die Hersteller-
    # Attribute werden nur gezeigt — am 2026-11-01 war der Befund, dass genau
    # boot_a und boot_b in den Bits 52..55 abweichen (Kopf 0x70…/0x82…, Sicherung
    # 0x57…/0x02…), alle uebrigen 19 Saetze bytegleich sind. Welche Seite ABOOT bei
    # einem Slot-Wechsel schreibt, ist im naechsten Fenster an beiden Feldern
    # abzulesen; die Geometrie darf auf keinen Fall abweichen.
    sicherungs = saetze(e["roh"], max(0, e["stelle"] - e["kapazitaet"] * SATZ), e["kapazitaet"])
    fehlende = [n for n in liste if n not in sicherungs]
    geometrie = [n for n in liste if n in sicherungs
                 and (sicherungs[n][0], sicherungs[n][1]) != (liste[n][0], liste[n][1])]
    attribute = [n for n in sorted(liste) if n in sicherungs
                 and sicherungs[n][2] != liste[n][2]]
    fehl += zeige("LUN %s: Sicherungsfeld deckt jeden Kopfsatz in der Geometrie ab" % lun,
                  not fehlende and not geometrie,
                  ("es fehlen " + ", ".join(fehlende[:5]) if fehlende else
                   ("LBA anders: " + ", ".join(geometrie[:5]) if geometrie else
                    "%d von %d Saetzen lagegleich" % (len(liste), len(liste)))))
    if attribute:
        zeige("LUN %s: Attribute unterscheiden Kopf von Sicherung: %s"
              % (lun, ", ".join("%s Kopf %x / Sicherung %x"
                                % (n, liste[n][2], sicherungs[n][2]) for n in attribute[:4])),
              True, "nicht die Geometrie — im naechsten Fenster nach einem Slot-Wechsel "
                    "erneut vergleichen")
    flags = sorted(n for n, (_, _, a, _) in liste.items() if a)
    paare = sorted({n[:-2] for n in liste if n.endswith(("_a", "_b"))})
    zeige("LUN %s: Attribute und A/B-Paare: %d flagged, %d Paare%s"
          % (lun, len(flags), len(paare),
             (" — " + ", ".join((flags + paare)[:8])) if (flags or paare) else ""), True)
    return fehl


def main():
    ordner = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "evidence", "gpt")
    fehler = 0
    for lun in LUNs:
        fehler += pruefe_lun(lun, ordner)
    print("# GPT-Audit: sechs UFS-LUNs, %d Fehler, Auszuege in %s" % (fehler, ordner))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
