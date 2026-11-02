#!/usr/bin/env python3
r"""v0aj -> v0ak: die Platte bleibt rw, und /ud/init wird vor der Uebergabe scharf.

Zwei Funde vom Boot um 00:0x, beide im ausgelieferten Init gemessen:

1) Die Halteschleife laeuft ueber `/sys/class/block/sd*`. Das Muster erfasst die
   Platte `/dev/sda` UND jede Partition. Freigegeben war nur die Partition
   (`$ud` aus /tmp/uddev), also legte die Schleife `/dev/sda` jede Sekunde erneut
   unter ro. Die Partition folgt diesem Schalter (Wurzel #9), und ext4 verlor seine
   Writes durch den Loop:

       [  174.114810] Buffer I/O error on dev loop0, logical block 131072, lost sync page write

   Danach stand der Mount auf ro, ein frisches `touch` meldete 'Read-only file
   system', und ein `chmod +x /ud/init` aus dem laufenden Boot war nach dem
   Neustart wieder weg. Der Mount-Zweig selbst lief durch:

       v0aj userdata rw: /dev/sda21 on /ud type ext4 (rw,relatime)

2) Der Haltbarkeitstest ist bestanden: `.probe-leben` (Inhalt `ueberlebt-v0ai`)
   ueberlebte den Neustart, ebenso `.v0aj-besuch` und `.v0aj-schreib`.
   Es fehlte nur die Uebergabe, weil das Bild ein /ud/init mit 0644 ausliefert und
   `[ -x /ud/init ]` deshalb nein sagt.

Aenderungen: (1) die Halteschleife verschont zusaendlich die Platte der
Userdata-Partition und haelt Platte wie Partition aktiv rw; (2) vor der Uebergabe
wird /ud/init notfalls scharf gemacht, mit Marke. Titel und Marken auf v0ak.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 688          # im v0aj-Archiv gemessen, nicht im Kopf

ALT_WACHE = '''            ud="$(cat /tmp/uddev 2>/dev/null)"
            if [ -n "$ud" ] && [ "$ud" = "${s##*/}" ]; then
                [ "$(cat "$s/ro" 2>/dev/null)" = 0 ] || blockdev --setrw "/dev/$ud"
                continue
            fi
'''

NEU_WACHE = '''            ud="$(cat /tmp/uddev 2>/dev/null)"
            if [ -n "$ud" ]; then
                scheibe="${ud%[0-9]*}"
                # v0ak: die Platte muss mit der Partition rw bleiben. Die
                # Schleife laeuft ueber /sys/class/block/sd* und erwischt
                # darin auch /dev/sda; die Partition folgt dem Plattenschalter.
                if [ "${s##*/}" = "$ud" ] || [ "${s##*/}" = "$scheibe" ]; then
                    [ "$(cat "$s/ro" 2>/dev/null)" = 0 ] || blockdev --setrw "/dev/${s##*/}"
                    continue
                fi
            fi
'''

ALT_UEBERGABE = '''        if [ -x /ud/init ] && [ -x /sbin/switch_root ]; then
'''

NEU_UEBERGABE = '''        if [ ! -x /ud/init ]; then
            chmod 755 /ud/init && mark "v0ak init scharf gemacht: $(ls -l /ud/init | cut -c1-40)"
        fi
        if [ -x /ud/init ] && [ -x /sbin/switch_root ]; then
'''


def umbau(text):
    assert text.count(ALT_WACHE) == 1, "Halteschleife (v0aj-Freigabe) nicht gefunden"
    assert text.count(ALT_UEBERGABE) == 1, "Uebergabe-Zweig nicht gefunden"
    assert "v0ak init scharf" not in text, "der Umbau lief schon einmal"
    assert 'blockdev --setrw "/dev/$UDNAME"' in text, "Grundarchiv ist nicht v0aj"
    assert "offset=1048576" in text, "der Byte-Versatz fehlt"
    text = text.replace(ALT_WACHE, NEU_WACHE).replace(ALT_UEBERGABE, NEU_UEBERGABE)
    text = text.replace("v0aj", "v0ak")
    assert "v0aj" not in text and "v0ai" not in text, "ein Altname bleibt stehen"
    assert 'scheibe="${ud%[0-9]*}"' in text, "die Plattenausnahme fehlt"
    assert "blockdev --setrw \"/dev/${s##*/}\"" in text, "die Halteschleife setzt nichts rw"
    assert "chmod 755 /ud/init" in text, "die Init-Schaerfe fehlt"
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
        print("Gebrauch: baue-v0ak-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
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
    assert "v0ak init scharf" in init.decode(), "die Scharf-Marke ist nach round-trip weg"
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    text = init.decode()
    print("baue-v0ak: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), text.count("\n"), len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    print("  Plattenausnahme %d mal, Halte-rw %d mal, Scharf-Marke %d mal, Byte-Versatz %d mal"
          % (text.count('scheibe="${ud%[0-9]*}"'), text.count('blockdev --setrw "/dev/${s##*/}"'),
             text.count("v0ak init scharf"), text.count("offset=1048576")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
