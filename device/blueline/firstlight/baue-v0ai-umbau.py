#!/usr/bin/env python3
"""v0ah -> v0ai: der Versatz in Byte, und der Fehlerwortlaut kommt in die Marke.

Grund (gemessen 2026-11-02, 22:5x, arm64-Container, dasselbe mount aus dem
ausgelieferten Archiv — util-linux 2.41.6, libmount 2.42.4): ein Dateisystem, das
bei 1 MiB in einem Blockgeraet liegt, haelt bei

    offset=1048576 -> ERFOLG   (inhalt: lost+found)
    offset=1024    -> FEHLER rc=32 'wrong fs type, bad option, bad superblock'
    offset=2048    -> FEHLER rc=32 'wrong fs type, bad option, bad superblock'

Die Einheit von offset= ist also BYTE, nicht der 1024-Byte-Block, den v0ah
angesetzt hat. v0ah haette damit bei 1024 B statt bei 1 MiB angefangen zu lesen —
ein zweiter, von der GPT-Frage unabhaengiger Grund, warum der Mount fehlschlaegt.

Zweite Aenderung: kein 2>/dev/null mehr an den Mounts. Der Fehlerwortlaut landet
in $udfehler und wird in der Marke ausgegeben. Ein versteckter Fehlerwortlaut hat
bei der ro-Wache (Wurzel #9) schon einmal Stunden gekostet. Der Erfolg wird
nicht aus dem Ausgangswort abgelesen, sondern daraus, dass /ud in der mount-Tafel
steht — ein Mount, der meldet und doch durchgeht, zaehlt als Erfolg.

Dritte Aenderung: ob der Vorlauf noetig ist, entscheidet nicht dieser Umbau,
sondern die Marker-Messung (images/userdata-alpine/marker-4mib.sparse.img,
MK0000/MK4096/MK8192 vor dem Boot, nach dem Neustart wiedergelesen). Bis die
vorliegt, bleibt der Versuch ohne Versatz im selben Zweig stehen.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 677          # im v0ah-Archiv gemessen, nicht im Kopf

ALT_MOUNT = (
    '    # v0ah: der Vorlauf von 1 MiB liegt im Bild, weil ABOOT seinen\n'
    '    # GPT-Bereich (Kopf bei 4096, Saetze ab 8192) bei jedem Start\n'
    '    # wieder hinlegt. Einheit des Versatzes sind 1024-Byte-Blocke.\n'
    '    # Der zweite Versuch ohne Versatz bleibt als Messung, nicht als\n'
    '    # Rettung: ging er durch, ist der Vorlauf ueberfluessig.\n'
    '    if mount -o rw,offset=1024 "/dev/$UDNAME" /ud 2>/dev/null \\\n'
    '       || mount -o rw "/dev/$UDNAME" /ud 2>/dev/null; then\n')

NEU_MOUNT = (
    '    # v0ai: offset= ist in BYTE (gemessen mit dem mount aus diesem Archiv,\n'
    '    # util-linux 2.41.6: 1048576 -> ERFOLG, 1024 und 2048 -> bad superblock).\n'
    '    # Kein 2>/dev/null: der Wortlaut kommt in die Marke. Erfolg ist, dass\n'
    '    # /ud in der mount-Tafel steht, nicht dass der Mount schweigt.\n'
    '    udfehler=$(mount -o rw,offset=1048576 "/dev/$UDNAME" /ud 2>&1)\n'
    '    if ! grep -q " /ud " /proc/mounts; then\n'
    '        mark "v0ai VersatzMount (1048576 B): $(echo "$udfehler" | tr \'\\n\' \' \' | cut -c1-80)"\n'
    '        udfehler=$(mount -o rw "/dev/$UDNAME" /ud 2>&1)\n'
    '    fi\n'
    '    if grep -q " /ud " /proc/mounts; then\n')

ALT_FEHLER = ('        mark "v0ah mount rw fehlgeschlagen (mit und ohne vorlauf): '
              '$(dmesg | tail -3 | tr \'\\n\' \';\')"\n')
NEU_FEHLER = ('        mark "v0ai beide Mounts fehl: $(echo "$udfehler" | tr \'\\n\' \' \' '
              '| cut -c1-70) dmesg: $(dmesg | tail -3 | tr \'\\n\' \';\' | cut -c1-90)"\n')


def umbau(text):
    assert text.count(ALT_MOUNT) == 1, "Mount-Zweig mit offset=1024 nicht gefunden"
    assert text.count(ALT_FEHLER) == 1, "Fehler-Marke nicht gefunden"
    assert "offset=1048576" not in text, "der Umbau lief schon einmal"
    text = text.replace(ALT_MOUNT, NEU_MOUNT).replace(ALT_FEHLER, NEU_FEHLER)
    text = text.replace("v0ah", "v0ai")
    assert "offset=1024" not in text, "ein Versatz auf 1024 ist noch uebrig"
    assert "offset=1048576" in text
    assert 'mount -o rw,offset=1048576 "/dev/$UDNAME" /ud 2>&1' in text
    assert '2>/dev/null \\\n       || mount -o rw' not in text, "der alte Doppel-Mount steht noch"
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0ai-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
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
        neuer_text = umbau(anfang)
        assert all(ord(ch) < 128 for zeile in neuer_text.splitlines() for ch in zeile), \
            "Nicht-ASCII im Init"
        e["content"] = neuer_text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    open(neben, "wb").write(blob)
    zurueck = newc.read_cpio(neben)
    init = next(e["content"] for e in zurueck if e["name"] == "init")
    assert init == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    assert "offset=1048576" in init.decode(), "Versatz nach round-trip weg"
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    print("baue-v0ai: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), init.decode().count("\n"), len(zurueck),
             hashlib.sha256(init).hexdigest()[:16]))
    print("  Versatz in Byte %d mal, Fehlermarke %d mal, alter Doppel-Mount %d mal"
          % (init.decode().count("offset=1048576"),
             init.decode().count("v0ai beide Mounts fehl"),
             init.decode().count("offset=1024")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
