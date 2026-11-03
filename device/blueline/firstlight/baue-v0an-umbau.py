#!/usr/bin/env python3
r"""v0am -> v0an: logflush schliesst die Platte nicht, waehrend /ud haengt.

Gemessen an den Bootes 17:01, 17:03, 17:05 und 17:29 (Wurzel e59b319b, boot_a
v0am): alle vier mit Journal-Abbruch, alle vier bei 29.2 s, alle vier mit

    EXT4-fs error (device loop0): ext4_journal_check_start:86: comm switch_root

`comm switch_root` ist der Hinweis: die erste WRITE kommt nicht von der neuen
Wurzel, sondern von switch_root selbst, das beim Schliessen des alten Roots den
Superblock nachschreibt. Zu diesem Zeitpunkt kann kein Code der neuen Wurzel
laufen - alle Korrekturen dort (Halteschleife, vorziehen, Initramfs-Reste
toeten) waren wirkungslos, was die vier Bootes auch zeigen.

Wer die Platte zuhat, steht im Initramfs selbst, Wort fuer Wort:

    logflush()            Zeile 306
        platte=/dev/...   Zeile 326   (die Platte unter boot_a)
        blockdev --setrw "$platte"    Zeile 327
        dd ... of="$d" ... fsync      Zeile 329   (der Roh-Log-Kanal)
        blockdev --setro "$d"         Zeile 331
        blockdev --setro "$platte"    Zeile 332   <- die Platte geht zu
    aufgerufen in Zeile 641, direkt vor switch_root (Zeile 648)

Der ro-Schalter der Platte nimmt die Partition mit - am laufenden Geraet
gemessen: `--setro /dev/sda` ergibt `platte=1 partition=1`, und ein
`--setrw /dev/sda21` danach meldet Ausgang 0 und bewirkt nichts. Also bleibt
die Platte kinftig offen, solange die userdata-Wurzel haengt; boot_a wird
weiterhin ro geschrieben und anschliessend ro gesetzt, nur die Platte nicht.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 708          # im v0am-Archiv gemessen (init 36968 B)

ALT = ('    blockdev --setro "$d" 2>/dev/null\n'
       '    blockdev --setro "$platte" 2>/dev/null\n')
NEU = ('    blockdev --setro "$d" 2>/dev/null\n'
       '    # v0an: die Platte bleibt offen, solange die userdata-Wurzel haengt.\n'
       '    # Ihr ro-Schalter nimmt die Partition mit (gemessen: setro auf der Platte\n'
       '    # ergibt partition=1, und ein --setrw auf die Partition bewirkt danach\n'
       '    # nichts), und switch_root schreibt beim Schliessen des alten Roots\n'
       '    # selbst - diese WRITE traf bisher ein zues Geraet und kostete das\n'
       '    # Journal. boot_a bleibt auch kinftig ro; nur die Platte nicht.\n'
       "    if grep -q ' /ud ' /proc/mounts; then\n"
       '        mark "v0an: Platte bleibt rw, /ud haengt"\n'
       '    else\n'
       '        blockdev --setro "$platte" 2>/dev/null\n'
       '    fi\n')

TITEL_ALT = "Omarchy Mobile first-light v0am"
TITEL_NEU = "Omarchy Mobile first-light v0an"


def umbau(text: str) -> str:
    assert text.count(ALT) == 1, "die beiden setro-Zeilen von logflush fehlen"
    assert TITEL_ALT in text, "der v0am-Titel fehlt"
    assert 'echo "$UDNAME" > /run/uddev' in text, "v0am laeuft nicht (keine /run-Ausnahme)"
    assert "v0an" not in text, "der Umbau lief schon einmal"
    text = text.replace(ALT, NEU).replace(TITEL_ALT, TITEL_NEU)
    assert text.count("""if grep -q ' /ud ' /proc/mounts; then""") == 1, "die Platten-Ausnahme steht nicht genau einmal"
    assert text.count('blockdev --setro "$platte"') == 1, "es wird nicht mehr genau einmal die Platte zu"
    assert 'blockdev --setro "$d"' in text, "boot_a geht nicht mehr zu"
    assert TITEL_NEU in text and "switch_root /ud /init" in text and "offset=1048576" in text
    assert all(ord(ch) < 128 for ch in text), "Nicht-ASCII im Init"
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0an-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
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
    open(neben, "wb").write(blob)
    zurueck = newc.read_cpio(neben)
    init = next(e["content"] for e in zurueck if e["name"] == "init")
    assert init == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    text = init.decode()
    print("baue-v0an: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), text.count("\n"), len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    print("  Platten-Ausnahme %d mal, Platte-zu %d mal, boot_a-zu %d mal, Titel %s"
          % (text.count("""if grep -q ' /ud ' /proc/mounts"""), text.count('blockdev --setro "$platte"'),
             text.count('blockdev --setro "$d"'), "v0an" if TITEL_NEU in text else "FALSCH"))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
