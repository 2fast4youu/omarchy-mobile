#!/usr/bin/env python3
"""v0ae -> v0af: der Selbst-Rueckweg wird an eine Funkstille gebunden.

Grund (Besprechung 2026-11-01, 20:5x): der Rueckweg ist jetzt eine Stoppuhr. Er
holt das Telefon ~372 s nach dem Start zurueck, auch wenn eine Shell offen ist —
er nimmt sie also genau dann weg, wenn man daran arbeitet. v0af kehrt erst
zurueck, nachdem fuenf Minuten lang keine Verbindung zu sehen war, und ein
`touch /tmp/halt` in der Shell haelt das Bild beliebig lange. Obere Grenze
bleibt, damit ein Fenster nicht unbemerkt tagelang Akku zieht.

Drei Aenderungen, jede auf den im Bild gelesenen Text verankert:

  A) Halteschleife vor dem letzten logflush. "Verbunden" heisst: ein Prozess hat
     einen Datei descriptor auf /dev/pts — busybox-telnetd holt pro Verbindung
     ein Pseudo-Terminal, im Leerlauf gibt es keins. Der immer laufende getty auf
     ttyGS0 waere mit `ps` als Verbindung durchgegangen, deshalb nicht ps. Die
     Zahl der TCP-Verbindungen auf :23 wird nur notiert, nicht entschieden.
  B) und C) die zwei Marks aus v0ad, die in einfachen Anfuehrungszeichen standen
     und deshalb ihren eigenen Befehl gedruckt haben statt ihrer Messung.

Der Rest des Bildes bleibt, wie er ist: Module, Ordnereintraege, Rueckweg-
Binaries, storage guard.
"""
import hashlib
import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 587          # im v0ae-Archiv gemessen, nicht im Kopf
TITEL_AN = "v0ae"
TITEL_NEU = "v0af"

ALT_A = "mark 'v0ab Ziel erreicht: letztes logflush, dann Ablesung, dann Selbst-Rueckweg'"
NEU_A = """# v0af: der Selbst-Rueckweg ist keine Stoppuhr mehr, die die Shell weg nimmt.
# Zurueckgekehrt wird erst nach fuenf Minuten Funkstille (60 Runden a 5s).
# Verbunden heisst hier: ein Prozess haelt einen Descriptor auf /dev/pts -
# busybox-telnetd holt pro Verbindung ein Pseudo-Terminal, im Leerlauf keins.
# Mit `ps` waere der immer laufende getty auf ttyGS0 als Verbindung durch-
# gegangen. Zusaetzlich haelt /tmp/halt das Bild unbegrenzt (in der Shell:
# touch /tmp/halt). Obergrenze 60 Minuten, damit ein Fenster nicht tagelang
# Akku zieht, wenn keiner abmeldet.
stille=0
wachen=0
verb=0
while [ "$wachen" -lt 720 ]; do
    wer=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c /dev/pts)
    verb=$(grep -c ':0017 .* 01 ' /proc/net/tcp 2>/dev/null)
    if [ -e /tmp/halt ] || [ "${wer:-0}" -gt 0 ]; then
        stille=0
    else
        stille=$((stille + 1))
        [ "$stille" -ge 60 ] && break
    fi
    sleep 5
    wachen=$((wachen + 1))
done
mark "Halteschleife nach $((wachen * 5))s, Funkstille $stille Runden, pts $wer, tcp23 ${verb:-0}, halt $([ -e /tmp/halt ] && echo ja || echo nein)"
mark 'v0af Ziel erreicht: letztes logflush, dann Ablesung, dann Selbst-Rueckweg'"""

ALT_B = """mark 'vor mkdir: configfs=$(grep -c " type configfs " /proc/mounts) libcomposite=$(grep -c libcomposite /proc/modules 2>/dev/null) module=$(wc -l < /proc/modules 2>/dev/null)'"""
NEU_B = """mark "vor mkdir: configfs=$(grep -c ' type configfs ' /proc/mounts) libcomposite=$(grep -c libcomposite /proc/modules 2>/dev/null) module=$(wc -l < /proc/modules 2>/dev/null)\""""

ALT_C = """mark 'nach mount: configfs=$(grep -c " type configfs " /proc/mounts) ordner=$([ -d "$CONFIGFS" ] && echo ja || echo nein) udc=$(ls /sys/class/udc 2>/dev/null | xargs)'"""
NEU_C = """mark "nach mount: configfs=$(grep -c ' type configfs ' /proc/mounts) ordner=$([ -d "$CONFIGFS" ] && echo ja || echo nein) udc=$(ls /sys/class/udc 2>/dev/null | xargs)\""""

# Der Panel-Titel ist die einzige Kennung, die am Telefon selbst zu sehen ist.
# Steht dort noch v0ae, laeuft ein anderes Bild als das, fuer das ich Belege
# sammle - also mit dem Umbau umstellen, nicht nachtraeglich raten.
ALT_D = "echo 'Omarchy Mobile first-light v0ae - RAM only, der Knopf wird gesucht' > /dev/console 2>/dev/null"
NEU_D = "echo 'Omarchy Mobile first-light v0af - RAM only, Rueckkehr nach Funkstille' > /dev/console 2>/dev/null"

ARBEIT = [(ALT_A, NEU_A), (ALT_B, NEU_B), (ALT_C, NEU_C), (ALT_D, NEU_D)]


def umbau(text):
    vorher = text
    for alt, neu in ARBEIT:
        n = text.count(alt)
        assert n == 1, "Anker %r genau %d mal im Init gefunden (erwartet 1)" % (alt[:48], n)
        text = text.replace(alt, neu)
    assert "Halteschleife" in text and "/tmp/halt" in text, "Halteschleife fehlt"
    assert "mark 'vor mkdir:" not in text and "mark 'nach mount:" not in text, \
        "die einfachen Anfuehrungszeichen stehen noch"
    assert TITEL_NEU in text, "der neue Titel fehlt"
    assert text.count("(") == text.count(")"), "Klammerbilanz verschoben %d/%d" % (
        text.count("("), text.count(")"))
    laengste_vorher = max(len(z) for z in vorher.splitlines())
    laengste = max(len(z) for z in text.splitlines())
    assert laengste <= laengste_vorher, "längste Zeile gewachsen: %d über %d" % (laengste, laengste_vorher)
    # Die eigenen Bloeecke bleiben kurz: das Panel bricht bei ~80 Spalten um, und
    # ein ueberlanger Mark-Text ist auf dem Panel nicht mehr abzulesen.
    for alt, neu in ARBEIT:
        m = max(len(z) for z in neu.splitlines())
        assert m < 200, "neuer Block mit Zeile %d Zeichen" % m
    for wort in ("; do", "mark ", "sleep ", "if ", "while "):
        erwartet = sum(neu.count(wort) - alt.count(wort) for alt, neu in ARBEIT)
        gemessen = text.count(wort) - vorher.count(wort)
        assert gemessen == erwartet, "%r: Differenz %+d, aus den Bloecken erwartet %+d" % (
            wort, gemessen, erwartet)
        print("  Zahlspur %-8s Differenz %+d (erwartet %+d)" % (wort, gemessen, erwartet))
    mehr = len(text.splitlines()) - len(vorher.splitlines())
    erwartet_mehr = sum(len(neu.splitlines()) - len(alt.splitlines()) for alt, neu in ARBEIT)
    assert mehr == erwartet_mehr, "Zeilen: %+d, erwartet %+d" % (mehr, erwartet_mehr)
    print("  Zahlspur Zeilen   Differenz %+d" % mehr)
    if any(ord(c) > 126 for c in text):
        bad = sorted({c for c in text if ord(c) > 126})
        raise AssertionError("Nicht-ASCII im Init: %r" % bad)
    return text


def elternpruefung(es, wo):
    """Keine Datei ohne ihren Elternordner — das verlangt der Entpacker."""
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!".replace("!!!", "!!!")
            and not stat.S_ISDIR(e["meta"]["mode"])
            and "/" in e["name"]
            and e["name"].rsplit("/", 1)[0] not in namen]
    ko = [e for e in es if e["name"].endswith(".ko")]
    print("%s: %d Eintraege, %d Module, Dateien ohne Elternordner: %d %s" % (
        wo, len(es), len(ko), len(fehl), fehl[:3]))
    assert len(ko) == 6 and not fehl, "%s verliert Module" % wo
    return ko


def haupt() -> int:
    if len(sys.argv) != 3:
        print(" usage: baue-v0af-umbau.py <ein.cpio> <aus.cpio>")
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    elternpruefung(es, "Grundarchiv")
    assert "usr/bin/restart2" in {e["name"] for e in es}, "restart2 fehlt im Grundarchiv"
    restart2_pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restart2")
    dichte = open(restart2_pfad, "rb").read()

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
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    assert zurueck["init"]["content"] == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    assert "Halteschleife" in zurueck["init"]["content"].decode(), "Fix nach round-trip weg"
    assert zurueck["usr/bin/restart2"]["meta"]["mode"] & 0o111, "restart2 nicht ausfuehrbar"
    assert zurueck["usr/bin/restart2"]["content"] == dichte, "restart2-Inhalt nicht dicht"
    elternpruefung(list(zurueck.values()), "nach round-trip")
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    init = zurueck["init"]["content"]
    print("baue-v0af: init %d B, %d Zeilen, restart2 sha %s, Eintraege %d, init sha %s" % (
        len(init), init.decode().count("\n"),
        hashlib.sha256(zurueck["usr/bin/restart2"]["content"]).hexdigest()[:16],
        len(zurueck), hashlib.sha256(init).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
