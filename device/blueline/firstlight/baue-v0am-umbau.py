#!/usr/bin/env python3
r"""v0al -> v0am: die Wachen-Ausnahme ueberlebt switch_root.

Gemessen am Boot 16:45 (Wurzel mit dem neuen /init 6fbd21b3):

    [   29.205376] Trying to write to read-only block-device sda21
    [   29.318391] EXT4-fs (loop0): I/O error while writing superblock
    [   29.325592] EXT4-fs (loop0): Remounting filesystem read-only

Die Halteschleife der neuen Wurzel meldet im selben Boot
`halte=sda sda21 ro= sda=0 sda21=0` - sie hat also freigegeben. Trotdem traf
der erste Schreibvorgang ein ro-Geraet: die Wache im Initramfs laeuft nach
`switch_root` weiter, liest ihre Ausnahme aber aus `/tmp/uddev`, und `/tmp`
ist mit dem alten Root verschwunden. Ihr naechster Durchlauf legt damit auch
`sda21` unter ro - 0,1 s nach der Freigabe, mitten in den ersten Schreibvorgang.

Fix: der Name der userdata-Partition steht zusaetzlich in `/run/uddev` (/run
ist ein Mount und ueberlebt den Uebergang - /run/steps.log wird danach noch
gelesen), und die Wache liest zuerst /run, dann /tmp.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 707          # im v0al-Archiv gemessen (init 36922 B)

ALT_WRITE = '[ -n "$UDNAME" ] && echo "$UDNAME" > /tmp/uddev'
NEU_WRITE = ('[ -n "$UDNAME" ] && { echo "$UDNAME" > /tmp/uddev; '
             'echo "$UDNAME" > /run/uddev; }')

ALT_READ = '            ud="$(cat /tmp/uddev 2>/dev/null)"'
NEU_READ = ('            ud="$(cat /run/uddev 2>/dev/null)"\n'
            '            [ -n "$ud" ] || ud="$(cat /tmp/uddev 2>/dev/null)"')

TITEL_ALT = "Omarchy Mobile first-light v0al"
TITEL_NEU = "Omarchy Mobile first-light v0am"


def umbau(text: str) -> str:
    assert text.count(ALT_WRITE) == 1, "die uddev-Schreibzeile fehlt"
    assert text.count(ALT_READ) == 1, "die uddev-Lesezeile der Wache fehlt"
    assert "/run/uddev" not in text, "der Umbau lief schon einmal"
    assert TITEL_ALT in text, "der v0al-Titel fehlt"
    assert "v0al runde frueh raus" in text, "der v0al-Fruehausstieg fehlt"
    text = text.replace(ALT_WRITE, NEU_WRITE).replace(ALT_READ, NEU_READ)
    text = text.replace(TITEL_ALT, TITEL_NEU)
    assert text.count('> /run/uddev') == 1, "die /run-Ausnahme steht nicht genau einmal"
    assert text.count('cat /run/uddev') == 1, "die Wache liest /run nicht"
    assert text.count('cat /tmp/uddev') == 1, "der /tmp-Rueckfall fehlt"
    assert TITEL_NEU in text, "der Panel-Titel ist nicht umgestellt"
    assert text.count("v0al runde frueh raus") == 2, "der Fruehausstieg ist veraendert"
    assert "switch_root /ud /init" in text and "offset=1048576" in text, "v0al-Zeilen fehlen"
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
        print("Gebrauch: baue-v0am-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
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
    elternpruefung(zurueck, "nach round-trip")
    os.remove(neben)
    open(aus_cpio, "wb").write(blob)
    os.chmod(aus_cpio, 0o644)
    text = init.decode()
    print("baue-v0am: init %d B, %d Zeilen, Eintraege %d, init sha %s"
          % (len(init), text.count("\n"), len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    print("  /run-Ausnahme %d mal, Wache liest /run %d mal, Titel %s"
          % (text.count("> /run/uddev"), text.count("cat /run/uddev"),
             "v0am" if TITEL_NEU in text else "FALSCH"))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
