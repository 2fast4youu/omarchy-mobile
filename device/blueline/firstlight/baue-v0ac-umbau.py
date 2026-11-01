#!/usr/bin/env python3
"""v0ab -> v0ac: der Log-Kanal findet seine Partition selbst, ohne Daemon.

Drei Messungen, keine gefolgert:

1. DER KANAL IST HEIL. Die Referenz schrieb um 18:07 mit demselben Versatz,
   den unsere Init benutzt (128-KiB-Block 504 = 66060288 B = 63 MiB in
   /dev/sda11, Partition 67108864 B) und las den Marker dort exakt zurueck
   (evidence/boot-a-schreibtest-2026-11-01.md, schreib_rc=0). Der Versatz ist
   also richtig.

2. UNSER BILD SCHRIEB NIE. Zwei Lesungen desselben Bereichs nach zwei eigenen
   Laeufen (17:41, 18:03) fanden keinen OMAMOBILE-Log. Es fehlt nicht an der
   Schreibbarkeit, sondern an einem Schritt davor.

3. DER Fehlende Schritt ist find_bootdev (Zeile 276ff im geladenen Archiv):
   sie kennt nur /dev/disk/by-partlabel/boot_a und /dev/disk/by-name/boot_a.
   Diese Namen legt ein Uevent-Daemon an (Android ueventd, postmarketOS mdev —
   die Referenz hat ihn, deshalb funktioniert sie von dort). Unser first-light
   laeuft im Initramfs ohne jeden Daemon, also gibt es die Symlinks dort nicht,
   find_bootdev gibt 1, logflush kehrt ohne jede Ausgabe zurueck, und die
   Beweislast liegt nie auf der Partition.

Deshalb, einfuegen statt ersetzen: die beiden bekannten Pfade bleiben die
ersten Wahl, und DANEBen steht die eigene Suche — der Kernel legt fuer jede
Partition /sys/block/<disk>/<part>/uevent mit der Zeile PARTNAME=<name> an
(das ist genau die Information, aus der ueventd den Symlink baut). Der
Knotencode kommt aus /sys/block/<disk>/<part>/dev (major:minor), und fehlt
die Gerätedatei im Initramfs, wird sie mit mknod angelegt. Jede Entscheidung
geht als Mark auf das Panel, denn nach einem eigenen Lauf ist das Panel der
einzige Leser (gemessen: der Mac sieht das Geraet erst nach einem harten
Reset wieder).

Nichts wird entfernt: die v0ab-Ablesung, die Modul-Laderunde, das Wartefenster
auf die Prozessnummer und der Selbst-Rueckweg bleiben, wie sie sind.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "Omarchy Mobile first-light v0ab - RAM only"
TITEL_NEU = "Omarchy Mobile first-light v0ac - RAM only"

SUCHE_AN = """find_bootdev() {
    for l in /dev/disk/by-partlabel/boot_a /dev/disk/by-name/boot_a; do
        [ -e "$l" ] || continue
        bootdev=$(basename "$(readlink -f "$l")")
        return 0
    done
    return 1
}"""

SUCHE_NEU = """find_bootdev() {
    for l in /dev/disk/by-partlabel/boot_a /dev/disk/by-name/boot_a; do
        [ -e "$l" ] || continue
        bootdev=$(basename "$(readlink -f "$l")")
        return 0
    done
    # Eigene Suche ohne Daemon: der Kernel haelt den Partitionsnamen in
    # /sys/block/<disk>/<part>/uevent als PARTNAME=, und major:minor in
    # <part>/dev. Genau daraus baut ueventd den Symlink, den wir hier nicht
    # haben. Die Geraetedatei wird angelegt, wenn sie fehlt.
    for u in /sys/block/*/sd*/uevent /sys/block/vd*/uevent; do
        [ -e "$u" ] || continue
        grep -q '^PARTNAME=boot_a$' "$u" 2>/dev/null || continue
        p=${u%/uevent}
        name=${p##*/}
        bootdev=$name
        [ -e "/dev/$name" ] || {
            kk=$(cut -d: -f1 "$p/dev" 2>/dev/null)
            mm=$(cut -d: -f2 "$p/dev" 2>/dev/null)
            mknod "/dev/$name" b "${kk:-0}" "${mm:-0}" 2>/dev/null
            mark "knoten /dev/$name angelegt major=${kk:-0} minor=${mm:-0} rc=$?"
        }
        mark "boot_a selbst gefunden: $name (aus $u)"
        return 0
    done
    mark 'boot_a nirgends gefunden: kein by-partlabel, kein PARTNAME in /sys/block'
    return 1
}"""


def einzige(text: str, teil: str) -> str:
    treffer = [z for z in text.splitlines() if teil in z]
    assert len(treffer) == 1, "Anker %r: %d Fundstellen, erwartet 1" % (teil[:40], len(treffer))
    return treffer[0]


def umbau(text: str, vorher: str) -> str:
    assert text.count(SUCHE_AN) == 1, "find_bootdev: %d Fundstellen" % text.count(SUCHE_AN)
    arbeit = [
        (einzige(text, TITEL_AN), einzige(text, TITEL_AN).replace("v0ab", "v0ac")),
        (SUCHE_AN, SUCHE_NEU),
    ]
    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        assert text.count(neu) >= 1, "Schritt %d: Ersatz danach nicht im Text" % nr

    assert text.isascii(), "Init traegt Nicht-ASCII (Panel ohne UTF-Konsole)"
    assert "PARTNAME=boot_a" in text, "die eigene Partionssuche fehlt"
    assert "logflush" in text and "sync" in text, "der Selbst-Rueckweg ist nicht mehr heil"
    assert "rueckgelesen=" in text, "die Ruecklese-Ablesung fehlt"
    assert "runden_pid=$!" in text, "die Prozessnummer der Runde fehlt"
    assert "restart2 bootloader" in text, "der Restart2-Rueckweg fehlt"
    # Zahlenspur, GEMESSEN (scratch/misse-v0ac-spur.py) statt im Kopf: der
    # erste Baudurchlauf forderte zwei Schleifenkoepfe und fand einen — die
    # Zahl stammte aus der Vorstellung. Gemessene Differenz der Suche: ein
    # Kopf, ein 'for', ein mknod, ein 'grep -q', drei Marks, 20 Zeilen, und
    # die Klammerbilanz bleibt dicht. Ein 'done' in Spalte 0 zaehlt nicht:
    # das neue steht eingerueckt, darum wird die Zahl klammergeprueft.
    for wort, erwartet in (("; do", 1), ("\n    for ", 1), ("mknod", 1),
                           ("grep -q", 1), ("mark ", 3)):
        d = text.count(wort) - vorher.count(wort)
        assert d == erwartet, "%r: Differenz %d, erwartet %d" % (wort, d, erwartet)
    enden = len([z for z in text.splitlines() if z.strip() == "done"])
    enden_vor = len([z for z in vorher.splitlines() if z.strip() == "done"])
    assert enden - enden_vor == 1, "done-Zeilen: Differenz %d, erwartet 1" % (enden - enden_vor)
    assert len(text.splitlines()) - len(vorher.splitlines()) == 20, \
        "Zeilen: %d mehr, erwartet 20" % (len(text.splitlines()) - len(vorher.splitlines()))
    assert text.count("(") == text.count(")"), "Klammerbilanz verschoben"
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0ac-umbau.py <new.cpio von v0ab> <new.cpio fuer v0ac>", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    assert "usr/bin/restart2" in {e["name"] for e in es}, "restart2 fehlt im Grundarchiv"
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        anfang = e["content"].decode()
        assert anfang.count("\n") == 558, "Grundarchiv hat %d Zeilen, erwartet 558 (v0ab)" % anfang.count("\n")
        text = umbau(anfang, anfang)
        assert TITEL_NEU in text and TITEL_AN not in text, "Panel-Titel nicht umgestellt"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    assert zurueck["init"]["content"] == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    assert zurueck["usr/bin/restart2"]["meta"]["mode"] & 0o111, "restart2 nicht ausfuehrbar"
    assert zurueck["usr/bin/restart2"]["content"] == open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart2"), "rb").read(), \
        "restart2-Inhalt nicht dicht"
    modul = [n for n in zurueck if n.startswith("usr/lib/modules/")]
    assert len(modul) >= 5, "Module nach round-trip unvollstaendig: %d" % len(modul)
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    init = zurueck["init"]["content"]
    print("baue-v0ac: init %d B, %d Zeilen, Module %d, restart2 sha %s, Eintraege %d"
          % (len(init), init.count(b"\n"), len(modul),
             hashlib.sha256(zurueck["usr/bin/restart2"]["content"]).hexdigest()[:16], len(zurueck)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
