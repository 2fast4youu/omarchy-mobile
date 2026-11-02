#!/usr/bin/env python3
r"""v0ai -> v0aj: die Partition selbst wird freigegeben, nicht nur die Platte.

Grund (am Geraet gemessen 2026-11-02, 23:2x): die Platte war rw, der Loop lag auf
den richtigen 1 MiB (`losetup -l` zeigt /dev/loop0 <- /dev/sda21, offset 1048576,
an Loop-Byte 1080 steht 53 ef), und ext4 meldete trotzdem

    EXT4-fs (loop0): I/O error while writing superblock
    mount: /ud: can't read superblock on /dev/loop0

Das ist Wurzel #9 von hinten: pass 1 der Wache legt JEDE Partition einzeln unter
ro. Die Ausnahme in der Halteschleife verhindert nur das erneute Setzen — sie hebt
das vorhandene ro nicht auf, und ein `--setrw` auf der Partition selbst war nie
gelaufen (`blockdev --getro /dev/sda21` antwortete 1). Von Hand freigegeben
montierte derselbe Loop sofort rw:

    /dev/loop0 /ud ext4 rw,relatime 0 0        Datei geschrieben und zurueckgelesen

Aenderungen: (1) im Mount-Zweig Platte UND Partition freigeben, rc und ro-Stand
gehen in die Marke; (2) die Halteschleife haelt die Partition jetzt aktiv rw, statt
sie nur zu verschonen. Titel und Marken auf v0aj. Der Byte-Versatz bleibt, wie v0ai
ihn geliefert hat.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 680          # im v0ai-Archiv gemessen, nicht im Kopf

ALT_FREIGABE = '''if [ -n "$UDNAME" ]; then
    blockdev --setrw /dev/sda 2>/dev/null
    mkdir -p /ud/dev /ud/proc /ud/sys /ud/run /ud/tmp
'''

NEU_FREIGABE = '''if [ -n "$UDNAME" ]; then
    # v0aj: Platte UND Partition freigeben. pass 1 der Wache hat jede
    # Partition einzeln unter ro gelegt; die Ausnahme hebt das alte ro
    # nicht auf, sie verhindert nur das erneute Setzen.
    plat_ro=$(blockdev --setrw /dev/sda 2>&1); plat_rc=$?
    ud_ro=$(blockdev --setrw "/dev/$UDNAME" 2>&1); ud_rc=$?
    mark "v0aj freigabe: platte rc=$plat_rc partition rc=$ud_rc ro=$(blockdev --getro "/dev/$UDNAME" 2>&1) text=$(echo "$plat_ro$ud_ro" | tr '\\n' ' ' | cut -c1-40)"
    mkdir -p /ud/dev /ud/proc /ud/sys /ud/run /ud/tmp
'''

ALT_WACHE = '''            ud="$(cat /tmp/uddev 2>/dev/null)"
            [ -n "$ud" ] && [ "$ud" = "${s##*/}" ] && continue
'''

NEU_WACHE = '''            ud="$(cat /tmp/uddev 2>/dev/null)"
            if [ -n "$ud" ] && [ "$ud" = "${s##*/}" ]; then
                [ "$(cat "$s/ro" 2>/dev/null)" = 0 ] || blockdev --setrw "/dev/$ud"
                continue
            fi
'''


def umbau(text):
    assert text.count(ALT_FREIGABE) == 1, "Freigabe-Zweig nicht gefunden"
    assert text.count(ALT_WACHE) == 1, "Wache-Ausnahme nicht gefunden"
    assert "offset=1048576" in text, "der Byte-Versatz fehlt — Grundarchiv ist nicht v0ai"
    assert "v0aj freigabe" not in text, "der Umbau lief schon einmal"
    text = text.replace(ALT_FREIGABE, NEU_FREIGABE).replace(ALT_WACHE, NEU_WACHE)
    text = text.replace("v0ai", "v0aj")
    assert "v0ai" not in text and "v0ah" not in text, "ein Altname bleibt stehen"
    assert 'blockdev --setrw "/dev/$UDNAME"' in text, "die Partitionsfreigabe fehlt"
    assert 'blockdev --setrw "/dev/$ud"' in text, "die Wache haelt die Partition nicht rw"
    assert "offset=1048576" in text and "switch_root /ud /init" in text
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0aj-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
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
    assert "v0aj freigabe" in init.decode(), "die Freigabe-Marke ist nach round-trip weg"
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    text = init.decode()
    print("baue-v0aj: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), text.count("\n"), len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    print("  Freigabe-Marke %d mal, Partitions-setrw in der Wache %d mal, Byte-Versatz %d mal"
          % (text.count("v0aj freigabe"), text.count('blockdev --setrw "/dev/$ud"'),
             text.count("offset=1048576")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
