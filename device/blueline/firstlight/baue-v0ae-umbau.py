#!/usr/bin/env python3
"""v0ad -> v0ae: das Archiv bekommt die Ordner, die der Kernel zum Entpacken braucht.

Der erste Steps.log eines eigenen Kernels (aus boot_a gelesen, 19:58,
evidence/boot-a-beutel-2026-11-01.md) nennt die Ursache des schweigenden
Gadgets selbst:

    [6s] step: KEIN /usr/lib/modules/7.1.0-rc1-sdm845 - Gadget-Module fehlen
    [6s] step: modul libcomposite.ko FEHLER 254        (…und dieselbe Zeile für
    alle sechs Module; 254 = -ENOENT, die Datei ist nicht da)
    [6s] step: usb_gadget not found in configfs, skipping gadget setup
    [21s] step: … can't create /sys/kernel/config/usb_gadget/g1/UDC:
                nonexistent directory      <- das, was am Panel zu lesen war

Gemessen am ausgelieferten Bild (fl-v0ad/firstlight.img, Ramdisk entpackt,
738 Eintraege): die sechs .ko-Dateien sind da, bytegleich, ELF, an den
Eintraegen 730-735. Aber die Ordner darunter fehlen als Eintrag:

    usr        VORHANDEN   usr/lib   VORHANDEN
    usr/lib/modules                                   FEHLT
    usr/lib/modules/7.1.0-rc1-sdm845                  FEHLT
    …/kernel, …/drivers, …/usb, …/gadget, …/function  FEHLT (jeweils)

Der Initramfs-Entpacker des Kernels legt fehlende Elternordner NICHT an: eine
Datei ohne vorhandenen Elternpfad wird still verworfen, ohne Meldung. Also
fehlten im laufenden System seit v0p alle sechs Module, obwohl jedes Pruefamt
sie im Archiv fand — die Pruefung las das Archiv, der Kernel baute ein
Wurzelsystem ohne sie. Kein Modul => kein libcomposite => das configfs-Mount
scheitert (USB_CONFIGFS=m) => kein Ordner usb_gadget => jede Bind-Runde
rennt gegen ein nonexistent directory.

Deshalb v0ae: die sieben Ordnereintraege werden VOR die erste .ko-Datei gesetzt
(der Elternordner muss im Archiv vor seinem Kind stehen), mit dem Modus des
vorhandenen Eintrags `usr/lib` (040755) und eigenen Inode-Nummern. Dazu die
Pruefung, die es bisher nicht gab: **jeder Dateieintrag im fertigen Archiv
muss seinen Elternordner als Eintrag haben.** Das ist die Eigenschaft, die der
Kernel beim Entpacken verlangt, und keine bisherige Pruefung sah sie.
"""
from __future__ import annotations

import hashlib
import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "Omarchy Mobile first-light v0ad - RAM only"
TITEL_NEU = "Omarchy Mobile first-light v0ae - RAM only"

# Der Pfad, dessen Zwischenordner fehlen, in Tiefe. Der Kernel braucht jeden
# einzelne als Eintrag, bevor eine Datei darunter entpackt werden kann.
MODUL_ORDNER = [
    "usr/lib/modules",
    "usr/lib/modules/7.1.0-rc1-sdm845",
    "usr/lib/modules/7.1.0-rc1-sdm845/kernel",
    "usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers",
    "usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb",
    "usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb/gadget",
    "usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb/gadget/function",
]


def elter(name: str) -> str:
    n = name[2:] if name.startswith("./") else name
    return n.rsplit("/", 1)[0] if "/" in n else ""


def fehlende_ordner(eintraege):
    """Jede Datei, deren Elternordner nicht im Archiv steht. Das sind genau
    die Dateien, die der Kernel beim Entpacken verliert."""
    namen = {e["name"] for e in eintraege} | {e["name"][2:] for e in eintraege}
    fehl = []
    for e in eintraege:
        if e["name"] == "TRAILER!!!":
            continue
        if stat.S_ISDIR(e["meta"]["mode"]):
            continue
        p = elter(e["name"])
        if p and p not in namen:
            fehl.append((e["name"], p))
    return fehl


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0ae-umbau.py <new.cpio von v0ad> <new.cpio fuer v0ae>", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"

    vorher = fehlende_ordner(es)
    print("verlorene Dateien im Grundarchiv: %d" % len(vorher))
    for n, p in vorher:
        print("  %s  (Elternordner %s fehlt)" % (n, p))
    assert len(vorher) == 6, "erwartet die sechs Moduldateien, gefunden %d" % len(vorher)

    # 1) Init-Titel
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        treffer += 1
        code = e["content"].decode()
        assert code.count("\n") == 587, "Grundarchiv-Init hat %d Zeilen, erwartet 587 (v0ad)" % code.count("\n")
        assert code.count(TITEL_AN) == 1, "Panel-Titel %d mal" % code.count(TITEL_AN)
        code = code.replace(TITEL_AN, TITEL_NEU, 1)
        assert code.isascii()
        e["content"] = code.encode()
    assert treffer == 1, "init genau %d mal" % treffer

    # 2) Ordnereintraege vor der ersten .ko-Datei
    vorlage = [e for e in es if e["name"] == "usr/lib"][0]
    naechste_ino = max(e["meta"]["ino"] for e in es) + 1
    erster_ko = [i for i, e in enumerate(es) if e["name"].endswith(".ko")][0]
    neu = []
    for i, ordner in enumerate(MODUL_ORDNER):
        assert ordner not in {e["name"] for e in es}, "%s ist schon im Archiv" % ordner
        meta = dict(vorlage["meta"])
        meta["ino"] = naechste_ino + i
        meta["mode"] = 0o40755
        meta["nlink"] = 1
        meta["datasize"] = 0
        neu.append({"meta": meta, "name": ordner, "content": b""})
    es = es[:erster_ko] + neu + es[erster_ko:]
    print("sieben Ordnereintraege gesetzt vor Eintrag %d (erste .ko)" % erster_ko)

    fehl = fehlende_ordner(es)
    assert not fehl, "nach dem Umbau verlieren noch %d Dateien ihren Elternordner: %s" % (len(fehl), fehl[:3])

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = newc.read_cpio(neben)
    # Rueckpruefung auf dem geschriebenen Archiv, nicht auf der Liste im Kopf.
    assert not fehlende_ordner(zurueck), "nach Round-trip fehlen wieder Ordnereintraege"
    namen = [e["name"] for e in zurueck]
    for o in MODUL_ORDNER:
        assert o in namen, "Ordner %s nicht im geschriebenen Archiv" % o
    ko = [e for e in zurueck if e["name"].endswith(".ko")]
    assert len(ko) == 6, "Module nach Round-trip: %d" % len(ko)
    for e in ko:
        assert e["content"][:4] == b"\x7fELF" and len(e["content"]) > 30000, "%s hohl" % e["name"]
        assert namen.index(e["name"]) > namen.index("usr/lib/modules"), \
            "%s vor seinem Elternordner im Archiv" % e["name"]
    assert namen[-1] == "TRAILER!!!", "TRAILER nicht zuletzt"
    assert zurueck[-2]["name"] == "usr/bin/restart2" and zurueck[-2]["meta"]["mode"] & 0o111, \
        "restart2 nicht zuletzt vor dem TRAILER, nicht ausfuehrbar"
    assert zurueck[0]["name"] == "init" or [e for e in zurueck if e["name"] == "init"], "init verloren"
    assert TITEL_NEU in [e for e in zurueck if e["name"] == "init"][0]["content"].decode()
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    d = open(aus_cpio, "rb").read()
    print("geschrieben: %s  %d B  sha %s  Eintraege %d  Ordnereintraege %d"
          % (aus_cpio, len(d), hashlib.sha256(d).hexdigest()[:16], len(zurueck),
             sum(1 for e in zurueck if stat.S_ISDIR(e["meta"]["mode"]))))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
