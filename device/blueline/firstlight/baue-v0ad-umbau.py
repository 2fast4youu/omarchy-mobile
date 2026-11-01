#!/usr/bin/env python3
"""v0ac -> v0ad: der Log-Kanal dreht die PLATTE frei, nicht nur die Partition.

Vier Messungen von heute abend, alle am laufenden Geraet, keine gefolgert:

1. DER VERSATZ STIMMT. 128-KiB-Block 504 = 66060288 B in /dev/sda11
   (Partition 67108864 B). Die Referenz schrieb dahin um 18:07 einen Marker
   und las ihn exakt zurueck (evidence/boot-a-schreibtest-2026-11-01.md).

2. UNSER BILD SCHRIEB NIE. Um 19:35 liegt bei 66060288 unveraendert der
   Schreibtest-Marker von 18:07 (od -c, evidence/ro-kausalitaet-2026-11-01.md).
   Der v0ac-Lauf 18:16-18:21 hat dort keine einzige Zeile hinterlassen, obwohl
   er ueber 334 s lief und logflush mehrfach aufrief.

3. WARUM, gemessen (19:40:50-19:41:14, dasselbe Geraet, Kernel 7.1.0-rc1-sdm845):
   nach `blockdev --setro /dev/sda` meldet `blockdev --setrw /dev/sda11`
   anschieend immer noch `sda11=1` — der ro-Schalter der Partition folgt dem
   der Platte. dd daraufhin: "dd: error writing '/dev/sda11': Operation not
   permitted", 0 Bytes, rc=1. Sobald die PLATTE rw ist (platte_rw=0), schreibt
   dd 24 Bytes mit rc=0, und der Marker steht beim Lesen da.

4. UNSERE EIGENE storage_guard setzt beim Boot jede Platte und jede Partition
   auf ro (Init ~Zeile 486). logflush drehte bisher nur die Partition zurueck,
   also war jede Schreiboperation seit dem ersten Bau dieser Guard zum
   Scheitern verurteilt — und `2>/dev/null` an der dd-Zeile hat den
   Fehlertext verschluckt, so dass nichts davon irgendwo stand.

Deshalb: logflush befreit die Platte, dann die Partition, schreibt, faengt den
Fehlertext in eine Variable statt in /dev/null, stellt beide Zurueck ro, und
meldet rc, Fehlertext und den ro-Zustand als Mark auf das Panel. Die Guard
selbst bleibt, wo sie ist — sie soll schuetzen, nur darf der eine Schreibpfad
sie nicht gegen eine Wand laufen lassen.

Zusaetzlich, auf Bitte von Claude (Check-in 19:20), zwei Marks an der
Gadget-Stelle, die genau die drei Fragen beantworten, die das Panel bisher
nicht beantwortet hat: ist configfs gemountet, existiert der usb_gadget-Ordner,
und ist libcomposite VOR dem Anlegen der Funktionen geladen. Ohne diese drei
Zahlen ist "kein Gadget am Baum" nur die Beobachtung, nicht die Ursache.

Nichts wird entfernt: PARTNAME-Suche, Ablesung, Prozessnummer-Wartung und
Selbst-Rueckweg bleiben.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "Omarchy Mobile first-light v0ac - RAM only"
TITEL_NEU = "Omarchy Mobile first-light v0ad - RAM only"
# Gemessen am Grundarchiv (images/fl-v0ac/new.cpio, neue Zeilen der Init).
GRUNDZEILEN = 578

SCHREIB_AN = """    blockdev --setrw "$d" 2>/dev/null
    dd if=/run/log.pad of="$d" bs=131072 seek=504 conv=notrunc,fsync 2>/dev/null
    blockdev --setro "$d" 2>/dev/null
}"""

SCHREIB_NEU = """    # Der ro-Schalter der Partition folgt dem der Platte (19:40 gemessen).
    # Also die Platte zuerst, dann die Partition; nachher beide zurueck ro.
    platte=/dev/$(echo "$bootdev" | sed 's/[0-9]*$//')
    blockdev --setrw "$platte" 2>/dev/null
    blockdev --setrw "$d" 2>/dev/null
    schreib=$(dd if=/run/log.pad of="$d" bs=131072 seek=504 conv=notrunc,fsync 2>&1)
    schreib_rc=$?
    blockdev --setro "$d" 2>/dev/null
    blockdev --setro "$platte" 2>/dev/null
    mark "schreib_rc=$schreib_rc $(echo "$schreib" | tr '\\n' ' ' | cut -c1-70) platte=$platte ro_achter=$(cat /sys/class/block/$bootdev/ro 2>/dev/null)"
}"""

VOR_AN = 'mkdir -p "$(dirname "$CONFIGFS")"'
VOR_NEU = """mark 'vor mkdir: configfs=$(grep -c " type configfs " /proc/mounts) libcomposite=$(grep -c libcomposite /proc/modules 2>/dev/null) module=$(wc -l < /proc/modules 2>/dev/null)'
mkdir -p "$(dirname "$CONFIGFS")\""""

NACH_AN = 'mount -t configfs -o nodev,noexec,nosuid configfs "$(dirname "$CONFIGFS")" 2>/dev/null'
NACH_NEU = """mount -t configfs -o nodev,noexec,nosuid configfs "$(dirname "$CONFIGFS")" 2>/dev/null
mark 'nach mount: configfs=$(grep -c " type configfs " /proc/mounts) ordner=$([ -d "$CONFIGFS" ] && echo ja || echo nein) udc=$(ls /sys/class/udc 2>/dev/null | xargs)'"""


def einzige(text: str, teil: str) -> str:
    treffer = [z for z in text.splitlines() if teil in z]
    assert len(treffer) == 1, "Anker %r: %d Fundstellen, erwartet 1" % (teil[:40], len(treffer))
    return treffer[0]


def umbau(text: str, vorher: str) -> str:
    arbeit = [
        (einzige(text, TITEL_AN), einzige(text, TITEL_AN).replace("v0ac", "v0ad")),
        (VOR_AN, VOR_NEU),
        (NACH_AN, NACH_NEU),
        (SCHREIB_AN, SCHREIB_NEU),
    ]
    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        assert text.count(neu) >= 1, "Schritt %d: Ersatz danach nicht im Text" % nr

    assert text.isascii(), "Init traegt Nicht-ASCII (Panel ohne UTF-Konsole)"
    # Inhalt: der bewiesene Fix und die drei Fragen an das Panel.
    assert 'blockdev --setrw "$platte"' in text, "die Platte wird nicht freigegeben"
    assert 'schreib=$(dd' in text, "dd schreibt weiterhin ins Nichts"
    assert "schreib_rc=" in text, "der Schreib-Fehlerbericht fehlt"
    assert 'vor mkdir: configfs=' in text and 'nach mount: configfs=' in text, \
        "die Gadget-Spionage fehlt"
    assert "PARTNAME=boot_a" in text, "die eigene Partitionssuche fehlt"
    assert "rueckgelesen=" in text, "die Ruecklese-Ablesung fehlt"
    assert "runden_pid=$!" in text, "die Prozessnummer der Runde fehlt"
    assert "restart2 bootloader" in text, "der Restart2-Rueckweg fehlt"
    assert text.count("(") == text.count(")"), "Klammerbilanz verschoben"
    # Zahlenspur: die Differenz wird aus den eingesetzten Textbloecken
    # BERECHNET, nicht in den Kopf geschrieben (bei v0ac stand eine Zahl im
    # Umbau, die nicht stimmte, und der erste Bau lief nur wegen ihr nicht).
    # Stimmt die Differenz nicht, wurde irgendwo nebenbei Text veraendert.
    for wort in ("; do", "for ", "blockdev", "mark ", "dd ", "sed "):
        erwartet = sum(neu.count(wort) - alt.count(wort) for alt, neu in arbeit)
        gemessen = text.count(wort) - vorher.count(wort)
        assert gemessen == erwartet, "%r: Differenz %d, aus den Bloecken erwartet %d" % (wort, gemessen, erwartet)
        print("  Zahlspur %-10s Differenz %+d (erwartet %+d)" % (wort, gemessen, erwartet))
    mehr = len(text.splitlines()) - len(vorher.splitlines())
    erwartet_mehr = sum(len(neu.splitlines()) - len(alt.splitlines()) for alt, neu in arbeit)
    assert mehr == erwartet_mehr, "Zeilen: %+d, aus den Bloecken erwartet %+d" % (mehr, erwartet_mehr)
    print("  Zahlspur Zeilen     Differenz %+d" % mehr)
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0ad-umbau.py <new.cpio von v0ac> <new.cpio fuer v0ad>", file=sys.stderr)
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
        assert anfang.count("\n") == GRUNDZEILEN, \
            "Grundarchiv hat %d Zeilen, erwartet %d (v0ac)" % (anfang.count("\n"), GRUNDZEILEN)
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
    assert "schreib_rc=" in zurueck["init"]["content"].decode(), "Fix nach round-trip weg"
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
    print("baue-v0ad: init %d B, %d Zeilen, Module %d, restart2 sha %s, Eintraege %d"
          % (len(init), init.count(b"\n"), len(modul),
             hashlib.sha256(zurueck["usr/bin/restart2"]["content"]).hexdigest()[:16], len(zurueck)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
