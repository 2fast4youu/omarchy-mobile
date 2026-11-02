#!/usr/bin/env python3
"""v0ag -> v0ah: das Dateisystem rueckt hinter den GPT-Bereich.

Grund (gemessen 2026-11-02, 17:0x): v0ag findet userdata (sda21) und versucht den
Mount, aber die Partition liefert bei 4096 'EFI PART' statt der
Gruppenbeschreiber, die das Bild dort traegt (81 00 00 00 89 00 00 00 = Block-
Bitmap bei 129, Inode-Bitmap bei 137). Bei 4096-Byte-LUN-Sektoren wohnen GPT-Kopf
und -saetze genau dort, und ABOOT legt sie beim Start wieder hin — ein noch so
dichtes Sparse-Bild aendert daran nichts (nachgeprueft an 1024/4096/8192/65536).

Also: das Bild traegt jetzt 1 MiB Vorlauf, der Superblock liegt bei 1 MiB + 1024,
und der Mount bekommt offset=1024 (die Einheit sind 1024-Byte-Blocke). Ein
zweiter Versuch ohne Vorlauf bleibt als Diagnose im selben Zweig, damit ein Erfolg
ohne Vorlauf nicht als Glueck durchgeht, sondern als Messung.

Aenderungen: Titel und Markennamen auf v0ah, Mount-Zweig mit Vorlauf-Regel.
Search, Wache-Ausnahme, Rueckweg und Module bleiben, wie v0ag sie geliefert hat.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 671          # im v0ag-Archiv gemessen, nicht im Kopf
ALT_MOUNT = '    if mount -o rw "/dev/$UDNAME" /ud 2>/dev/null; then\n'
NEU_MOUNT = ('    # v0ah: der Vorlauf von 1 MiB liegt im Bild, weil ABOOT seinen\n'
             '    # GPT-Bereich (Kopf bei 4096, Saetze ab 8192) bei jedem Start\n'
             '    # wieder hinlegt. Einheit des Versatzes sind 1024-Byte-Blocke.\n'
             '    # Der zweite Versuch ohne Versatz bleibt als Messung, nicht als\n'
             '    # Rettung: ging er durch, ist der Vorlauf ueberfluessig.\n'
             '    if mount -o rw,offset=1024 "/dev/$UDNAME" /ud 2>/dev/null \\\n'
             '       || mount -o rw "/dev/$UDNAME" /ud 2>/dev/null; then\n')
ALT_FEHLER = '        mark "v0ag userdata mount rw fehlgeschlagen: '
NEU_FEHLER = '        mark "v0ah mount rw fehlgeschlagen (mit und ohne vorlauf): '


def umbau(text):
    assert text.count(ALT_MOUNT) == 1, "Mount-Zweig nicht gefunden"
    assert text.count(ALT_FEHLER) == 1, "Fehlerzweig nicht gefunden"
    assert "first-light v0ag" in text, "Grundarchiv ist nicht v0ag"
    text = text.replace(ALT_MOUNT, NEU_MOUNT)
    text = text.replace(ALT_FEHLER, NEU_FEHLER)
    text = text.replace("v0ag", "v0ah")
    assert "first-light v0ah - userdata rw" in text, "Titel nicht umgestellt"
    assert "v0ag" not in text, "es bleibt ein v0ag-Rest im Init"
    assert "offset=1024" in text, "der Vorlauf-Mount fehlt"
    for zeile in text.splitlines():
        assert all(ord(c) < 128 for c in zeile), "Nicht-ASCII in: %.60s" % zeile
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0ah-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    elternpruefung(es, "Grundarchiv")
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        anfang = e["content"].decode()
        assert anfang.count("\n") == GRUNDZEILEN, \
            "Grundarchiv hat %d Zeilen, erwartet %d" % (anfang.count("\n"), GRUNDZEILEN)
        e["content"] = umbau(anfang).encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    neuer = zurueck["init"]["content"]
    assert neuer == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    assert "offset=1024" in neuer.decode(), "Vorlauf-Mount nach round-trip weg"
    elternpruefung(list(zurueck.values()), "nach round-trip")
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    print("baue-v0ah: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(neuer), neuer.decode().count("\n"), len(zurueck),
             hashlib.sha256(neuer).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
