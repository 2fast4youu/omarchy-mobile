#!/usr/bin/env python3
"""v0z -> v0aa: Ziel boot_a, und das Bild meldet sich selbst zurueck.

Drei Befunde, alle gemessen, keiner gefolgert:

1. DER LESEKANAL IST SCHON DA und war nie benutzt: logflush (Zeile 284ff im
   geladenen v0z-init) schreibt die ganze Beweislast nach 63 MiB auf boot_a
   (seek=504 * 128 KiB, gepolstert, Marker OMAMOBILE-LOG). Ein frueher Plan
   wollte sie mit `fastboot fetch` lesen -- das Geraet kann fetch nicht
   (gemessen 2026-11-01: 'Device does not support fetch command'). Gelesen
   wird jetzt anders: die Referenz hat Telnet, und von dort ist boot_a eine
   blockdatei. Voraussetzung ist nur, dass das eigene Bild AM ENDE ein
   letztes logflush abliefert und danach weg ist -- nicht im Endlos-Park.

2. DER RUECKWEG IST GEBUNKERT, nicht erraten: /tmp/restart2 mit
   reboot(2, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_MAGIC2A, 0xa1b2c3d4,
   "bootloader") bringt die laufende Referenz in 7 s nach Fastboot, ohne
   einen Slot-Retry zu verbrauchen (gemessen 2026-11-01 15:34, retry b blieb
   auf seinem Stand). Busybox-`reboot bootloader` kann das nicht (kennt das
   Argument nicht; gemessen: Kommando verworfen, 120 s kein Fastboot), und
   nacktes `reboot` aus der Referenz-Shell liess das Geraet 2026-11-01 16:38
   vollstaendig vom USB-Baum verschwinden -- eine Tastenaktion war noetig.

3. DAS FENSTER WAR ZU LANG: die v0z-Runde laeuft 20 x 15 s = 300 s, danach
   parkt PID 1 endlos. Fuer einen Selbst-Rueckweg muss das Bild bei
   bekannter Uhrzeit fertig sein. 8 Runden a 15 s = 120 s plus Anfahrt sind
   genug Messzeit und lassen genug Rand bis zur ABOOT-Zeitnahme von ~120 s,
   die v0r/v0w/v0y je ~120 s nach dem Start ins Fastboot zurueckwarf (Panel
   'SoC Watchdog BITE!', kein Kernel-Neustart).

Deshalb, in dieser Reihenfolge, alles DAZU oder eine Zahl gekuerzt, kein
einziger vorhandener Messschritt wird ersetzt:
  A  Titel v0z -> v0aa (ein Foto muss den Stand nennen)
  B  Rundenanzahl 20 -> 8 in der v0z-Runde (die einzige '-lt 20'-Stelle im
     Text, vor der Aenderung gemessen)
  C  restart2 (statisches aarch64-Binary, sha256 im Build-Log) als
     /usr/bin/restart2 ins Archiv, ausfuehrbar
  D  das Endlosparken (while :; do sleep 60; done, Zeile 526ff) wird zum
     Ziel: letzte Markierung, letztes logflush, sync, restart2 bootloader.
     Bei leerem boot_a-Pfad (Kanal tot) bleibt nur der sysrq-Notausgang.

Zielbootist boot_a: v0aa liegt auf boot_a, schreibt sein log an den eigenen
Schwanz (63 MiB, freier Platz des eigenen Bildes), und die Referenz auf
boot_b + dtbo_b bleibt unangetastet. boot_b ist der Rettungsweg und wird
von diesem Umbau nirgends geschrieben.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "Omarchy Mobile first-light v0z - RAM only"
TITEL_NEU = "Omarchy Mobile first-light v0aa - RAM only"
RUNDEN_AN = '    while [ "$zs" -lt 20 ]; do'
RUNDEN_NEU = '    while [ "$zs" -lt 8 ]; do'
PARK_AN = """while :; do
    sleep 60
done"""
RESTART2_Pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart2")
RESTART2_Ziel = "usr/bin/restart2"


def einzige(text: str, teil: str) -> str:
    treffer = [z for z in text.splitlines() if teil in z]
    assert len(treffer) == 1, "Anker %r: %d Fundstellen, erwartet 1" % (teil[:40], len(treffer))
    return treffer[0]


ZIEL = """mark 'v0aa wartet das Messfenster der Runde aus'
warte=0
while [ "$warte" -lt 120 ]; do
    sleep 10
    warte=$((warte + 1))
done
mark 'v0aa Ziel erreicht: letztes logflush, dann Selbst-Rueckweg'
logflush
sync
if [ -x /usr/bin/restart2 ]; then
    /usr/bin/restart2 bootloader
fi
# Nur noch hier: restart2 hat nicht zurueckgegeben oder fehlt. Sysrq-Notausgang.
echo b > /proc/sysrq-trigger
sleep 30"""


def umbau(text: str, vorher: str) -> str:
    arbeit = []
    arbeit.append((einzige(text, TITEL_AN), einzige(text, TITEL_AN).replace("v0z", "v0aa")))
    arbeit.append((einzige(text, RUNDEN_AN), RUNDEN_NEU))
    assert text.count(PARK_AN) == 1, "Endlospark: %d Fundstellen, erwartet 1" % text.count(PARK_AN)
    arbeit.append((PARK_AN, "mark 'init main flow complete; v0aa steuert den Selbst-Rueckweg an'\n" + ZIEL))

    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        assert text.count(neu) >= 1, "Schritt %d: Ersatz danach nicht im Text" % nr

    assert text.isascii(), "Init traegt Nicht-ASCII (Panel ohne UTF-Konsole)"
    assert "OMAMOBILE-LOG" in text and "seek=504" in text, "der Lesekanal ist nicht mehr heil"
    assert "echo connect > " in text, "die v0z-Knopfrunde ist nicht mehr heil"
    assert 'while [ "$zs" -lt 20 ]' not in text, "die Rundenanzahl nicht gekuerzt"
    # Zahlenspur: der Umbau darf genau einen Schleifenkopf und ein
    # Schleifenende mehr hinterlassen (das Wartfenster). Eine andere Differenz
    # heisst: ein Anker hat ein Stueck Init verschluckt oder verdoppelt.
    # Zahlenspur, am Gegenstoß gemessen: der erste Durchlauf setzte einen
    # Namen _wt, und _wt ist in Bash der SPECIAL-PARAMETER (letzes Argument,
    # hier leer) — der Kopf lautete [ "" -lt 120 ], die Zaehlung lief null
    # Runden, und die Zahlenspur meldete Differenz 0 statt +1. Darum jetzt:
    # fensterloser Name 'warte', und der Sonderparameter-Fall ist als
    # eigene Pruefung im Text verankert.
    assert "_wt" not in text, "Sonderparameter-Name _wt ist im Text (Bash: leer)"
    assert text.count("; do") - vorher.count("; do") == 0, \
        "Schleifenkoepfe: Differenz %d, erwartet 0 (Fenster bringt 1, Park geht 1)" % (text.count("; do") - vorher.count("; do"))
    assert text.count("\ndone") - vorher.count("\ndone") == 0, \
        "done: Differenz %d, erwartet 0 (Fenster bringt 1, Park geht 1)" % (text.count("\ndone") - vorher.count("\ndone"))
    assert text.count("while :; do") == vorher.count("while :; do") - 1, \
        "das Endlospark muss genau eine 'while :; do' verlieren"
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0aa-umbau.py <new.cpio von v0z> <new.cpio fuer v0aa>", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    namen = {e["name"] for e in es}
    assert RESTART2_Ziel not in namen, "restart2-Pfad schon belegt"
    blob_restart2 = open(RESTART2_Pfad, "rb").read()
    sha = hashlib.sha256(blob_restart2).hexdigest()
    assert blob_restart2[:4] == b"\x7fELF" and len(blob_restart2) > 100000, "restart2 kein ELF"
    print("  restart2: %d B, sha256 %s" % (len(blob_restart2), sha))

    treffer = 0
    vorher_len = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher_len = len(e["content"])
        anfang = e["content"].decode()
        text = umbau(anfang, anfang)
        assert TITEL_NEU in text and TITEL_AN not in text, "Panel-Titel nicht umgestellt"
        assert ZIEL in text, "das Ziel fehlt"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    # Neues Mitglied: dieselbe Meta-Form, die read_cpio liefert (die flachen
    # FIELDS aus newc). Der Archivordner 'bin' existiert (Alpine-Layout, unten
    # geprueft), darum ist /bin/restart2 dasselbe Ziel. Der Eintrag muss VOR
    # dem TRAILER stehen -- v0m verlor so sein restart2 (newc.emit-Dokt.).
    assert "bin" in namen, "kein Ordner 'bin' im Archiv, /bin-Pfad waef leer"
    restart2_eintrag = {
        "name": RESTART2_Ziel,
        "meta": {"ino": 0, "mode": 0o100755, "uid": 0, "gid": 0, "nlink": 1,
                 "mtime": 0, "datasize": len(blob_restart2), "devmajor": 0,
                 "devminor": 0, "rdevmajor": 0, "rdevminor": 0,
                 "namesize": len(RESTART2_Ziel) + 1, "check": 0},
        "content": blob_restart2,
    }
    trailer_nr = [e["name"] for e in es].index("TRAILER!!!")
    es.insert(trailer_nr, restart2_eintrag)

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    assert zurueck["init"]["content"] == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    assert "usr/bin/restart2" in zurueck, "restart2 nach emit nicht im Archiv"
    assert zurueck["usr/bin/restart2"]["content"] == blob_restart2, "restart2-Inhalt nicht dicht"
    assert zurueck["usr/bin/restart2"]["meta"]["mode"] & 0o111, "restart2 nicht ausfuehrbar"
    modul = [n for n in zurueck if n.startswith("usr/lib/modules/")]
    soll = len({e["name"] for e in es if e["name"].startswith("usr/lib/modules/")})
    assert len(modul) == soll >= 5, "Module nach round-trip unvollstaendig: %d von %d" % (len(modul), soll)
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    print("baue-v0aa: init %d B (vorher %d), restart2 sha %s, Module %d, Eintraege %d"
          % (len(zurueck["init"]["content"]), vorher_len, sha[:16], len(modul), len(zurueck)))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
