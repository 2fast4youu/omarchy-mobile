#!/usr/bin/env python3
"""v0aa -> v0ab: das Wartfenster haelt sich an die Runde, nicht an eine Uhr.

Zwei Befunde, beide gemessen (evidence/v0aa-lauf-1-2026-11-01.md):

1. DAS FENSTER WAR ZU KNAPP. Die Knopf-Runde laeuft 8 x 15 s = 120 s, das
   starre Wartefenster war 120 s, und beides laeuft parallel — der Rand ist
   null. Im Lauf 1 war bei 120 s Schluss, ohne dass die Runde gemeldet haette,
   fertig zu sein. Also: die Runde merkt sich beim Start ihre Prozessnummer
   (`runden_pid=$!` nach dem `(...) &`), und das Ende wartet auf genau diesen
   Prozess, mit einer Kappe von 48 x 5 s = 240 s fuer den Fall, dass die Runde
   haengt. `kill -0` ist in Busybox vorhanden; eine leere Nummer laeuft ins
   `break` und lasst das logflush trotzdem laufen.

2. DER NAME IST KEINE FREIHE. Der erste Versuch schrieb die Zahlung in `_wt`;
   in Bash ist `_wt` der Sonderparameter fuer das letzte Argument und damit
   leer — die Schleife lief null Runden (Gegentoess: bash-runden=0 gegen
   saubere-runden=3). Der Name `warte` bleibt, die Prüfung `_wt nicht im Text`
   auch.

Nichts Vorhandenes wird entfernt: der Titel wird umgestellt, die Runde
behalt jeden Messschritt, nur ihre Prozessnummer kommt dazu, und das starre
Warten wird durch das wartende Nachsehen ersetzt.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "Omarchy Mobile first-light v0aa - RAM only"
TITEL_NEU = "Omarchy Mobile first-light v0ab - RAM only"
RUNDEN_ENDE_AN = """        echo "omamobile-blueline: $akt" > /dev/kmsg
    done
) &
mkdir -p /etc/dropbear"""
RUNDEN_ENDE_NEU = """        echo "omamobile-blueline: $akt" > /dev/kmsg
    done
) &
runden_pid=$!
mkdir -p /etc/dropbear"""
WARTEN_AN = """warte=0
while [ "$warte" -lt 120 ]; do
    sleep 10
    warte=$((warte + 1))
done"""
WARTEN_NEU = """warte=0
while [ "$warte" -lt 48 ]; do
    kill -0 "$runden_pid" 2>/dev/null || break
    sleep 5
    warte=$((warte + 1))
done
mark 'warten beendet nach '$((warte * 5))'s, runde ' $(kill -0 "$runden_pid" 2>/dev/null && echo laeuft-noch || echo fertig)"""


def einzige(text: str, teil: str) -> str:
    treffer = [z for z in text.splitlines() if teil in z]
    assert len(treffer) == 1, "Anker %r: %d Fundstellen, erwartet 1" % (teil[:40], len(treffer))
    return treffer[0]


def umbau(text: str, vorher: str) -> str:
    arbeit = [
        (einzige(text, TITEL_AN), einzige(text, TITEL_AN).replace("v0aa", "v0ab")),
        (WARTEN_AN, WARTEN_NEU),
    ]
    assert text.count(RUNDEN_ENDE_AN) == 1, "Runden-Ende: %d Fundstellen" % text.count(RUNDEN_ENDE_AN)
    arbeit.append((RUNDEN_ENDE_AN, RUNDEN_ENDE_NEU))
    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        assert text.count(neu) >= 1, "Schritt %d: Ersatz danach nicht im Text" % nr

    assert text.isascii(), "Init traegt Nicht-ASCII (Panel ohne UTF-Konsole)"
    assert "_wt" not in text, "Sonderparameter-Name _wt ist im Text (Bash: leer)"
    assert "runden_pid=$!" in text, "die Prozessnummer der Runde fehlt"
    assert 'kill -0 "$runden_pid"' in text, "das Nachsehen fehlt"
    assert "logflush\nsync" in text, "der Selbst-Rueckweg ist nicht mehr heil"
    assert "OMAMOBILE-LOG" in text and "seek=504" in text, "der Lesekanal ist nicht mehr heil"
    # Zahlenspur: das neue Wartefenster bringt einen Kopf und ein Ende, das
    # alte Fenster hatte beides schon — Differenz also 0, und die runde Zahl
    # der Messschritte bleibt unangetastet.
    assert text.count("; do") - vorher.count("; do") == 0, \
        "Schleifenkoepfe: Differenz %d, erwartet 0" % (text.count("; do") - vorher.count("; do"))
    assert text.count("\ndone") - vorher.count("\ndone") == 0, \
        "done: Differenz %d, erwartet 0" % (text.count("\ndone") - vorher.count("\ndone"))
    assert text.count("mark ") >= vorher.count("mark "), "Marks sind weggefallen"
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0ab-umbau.py <new.cpio von v0aa> <new.cpio fuer v0ab>", file=sys.stderr)
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
    modul = [n for n in zurueck if n.startswith("usr/lib/modules/")]
    assert len(modul) >= 5, "Module nach round-trip unvollstaendig: %d" % len(modul)
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    init = zurueck["init"]["content"]
    print("baue-v0ab: init %d B, %d Zeilen, Module %d, restart2 sha %s, Eintraege %d"
          % (len(init), init.count(b"\n"), len(modul),
             hashlib.sha256(zurueck["usr/bin/restart2"]["content"]).hexdigest()[:16], len(zurueck)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
