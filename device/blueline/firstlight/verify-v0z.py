#!/usr/bin/env python3
"""Beweismale an v0z, gemessen AM FERTIGEN BILD und im Zeilendiff gegen v0y.

Warum der Diff und nicht eine Anwesenheitsliste: die Regel aus frueheren Laeuften
lautet 'ein Ersatz darf eine vorhandene Messung nicht stumm entfernen'. Eine
Anwesenheitsliste prueft, was drin steht, nicht, was weggeblieben ist. v0z ist
deshalb ALS EINFUEGUNG gebaut, und der Diff beweist genau das:

  * genau eine geaenderte Zeile (der Panel-Titel v0y -> v0z),
  * nur eingefuegte Zeilen sonst, keine geloeschte,
  * jede Messung des Vorgaengers steht wortglich noch drin,
  * kein Leser in einem neuen Zeilentext haelt die Standardeingabe offen.

Der letzte Punkt ist die Klasse des v0y-Grundes: 'cat $(suche)' ohne Fund gibt
cat KEIN Argument, und die Standardeingabe der PID 1 ist die Konsole (am Pty
gemessen). Ein Leser ohne Ziel in einer neuen Zeile waere derselbe Defekt.
"""
from __future__ import annotations

import difflib
import gzip
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

V0Y = os.environ.get("V0Y", "/Users/gregor/hermes-workspace/images/fl-v0y/firstlight.img")

LESER = ("cat", "tac", "head", "tail", "wc", "dd", "grep", "sed", "awk", "tr",
         "od", "hexdump", "strings", "md5sum", "sha256sum", "sum", "cmp", "xargs")


def init_text(bild: str) -> str:
    """Init aus einem Android boot.img, Seite fuer Seite wie im Vorgaenger.

    kernel_size bei 8, ramdisk-Groesse bei 16, die ramdisk beginnt an der Seite
    HINTER dem Kernel. 24 + kernel_size ist falsch und meldet
    'Not a gzipped file (b\\x00\\x00)' - gemessen.
    """
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    laenge = struct.unpack_from("<I", d, 16)[0]
    roh = gzip.decompress(d[rd:rd + laenge])
    ordner = tempfile.mkdtemp(prefix="v0z-pruef-")
    pfad = os.path.join(ordner, "ram.cpio")
    with open(pfad, "wb") as offen:
        offen.write(roh)
    return {e["name"]: e for e in newc.read_cpio(pfad)}["init"]["content"].decode()


def _klammer_ende(text: str, offnung: int) -> int:
    """Index der schliessenden Klammer zu text[offnung] == '('."""
    tiefe = 0
    i = offnung
    while i < len(text):
        if text[i] == "(":
            tiefe += 1
        elif text[i] == ")":
            tiefe -= 1
            if tiefe == 0:
                return i
        i += 1
    return len(text)


def leser_ohne_ziel(zeile: str, stelle: int = 0) -> list:
    """Leser, deren Argument aus einer Substitution kommt, ohne Geschuetz.

    Eine leere Kommandosubstitution gibt dem Leser KEIN Argument, und ein Leser
    ohne Argument liest die Standardeingabe, und die ist bei PID 1 die Konsole
    (am Pty gemessen: 'VOR' erscheint, 'NACH' kommt in drei Sekunden nicht).

    Das Geschuetz muss ein Argument des LESERS sein, nicht der aeusseren
    Ersetzung. Die erste Fassung dieser Pruefung sammelte den Text bis zur
    Aeusseren Klammer ein und sah dort ein '</dev/null', das in Wahrheit die
    AEUSSERE Ersetzung deckt (gemeldet als Fund auf Zeile 77, in Wahrheit ein
    Selbstfehler des Pruefers). Jetzt: die innere Ersetzung wird mit eigener
    Klammerbilanz ausgeschnitten, der Text DAHINTER bis zum Ende dieses
    Befehlsabschnitts ist das, was dem Leser zugehoert. Ein Leser ohne Argument
    in einem geleerten Zweig bleibt ein Fund, auch wenn spaeter in der Zeile
    ein Geschuetz steht - ein spaeteres Deckt ein frueheres nicht.
    """
    funde = []
    for m in __import__("re").finditer(r"\b(" + "|".join(LESER) + r")[ \t]+\$\(", zeile):
        leser = m.group(1)
        aussen = m.end() - 2                   # die '(' der inneren Ersetzung
        ende = _klammer_ende(zeile, aussen + 1)
        innen = zeile[aussen + 2:ende]
        # der dem Leser zugehoerige Text: nach der inneren Ersetzung bis zu
        # einem Rohr, einem Schluss oder dem Zeilenende
        schwanz = zeile[ende + 1:]
        schnitt = len(schwanz)
        for zeichen in ("|", ")", ";", "&"):
            pos = schwanz.find(zeichen)
            if 0 <= pos < schnitt:
                schnitt = pos
        befahl = schwanz[:schnitt]
        # Nach welcher Umleitung die STANDARDEINGABE geschlossen ist, entscheidet
        # das Token, nicht der Teilstring: '2>/dev/null' enthaelt '</dev/null'
        # und deckt trotzdem nur den Fehlerausgang (gemessen: damit meldete der
        # Pruefer die echte v0x-Haengerzeile als sauber, ein schlafender Pruefer).
        worte = befahl.split()
        eingabe = [w for w in worte if w.startswith("<") or w.startswith("0<")]
        argumente = [w for w in worte if not __import__("re").match(r"^[0-9*]*[<>]", w)]
        if not eingabe and not argumente:
            funde.append((leser, innen[:40], befahl.strip()[:24]))
        funde += leser_ohne_ziel(innen)          # dieselbe Klasse in der Suchseite
    return funde


SELBSTFELLE = [
    ("v0y-Zeile: der Leser haelt sein eigenes </dev/null>",
     'echo "modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null'
     ' | head -1) 2>/dev/null </dev/null)"', 0),
    ("v0x-Zeile: ungedeckt, das ist der echte Haenger",
     'echo "modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null'
     ' | head -1) 2>/dev/null)"', 1),
    ("nackte Schachtelung ohne jedes Geschuetz",
     'echo "wert=$(cat $(ls /leer))"', 1),
    ("ls mit Ordnerargument und Rohr: liest nie die Konsole",
     "echo \"d=$(ls /sys/kernel/debug 2>/dev/null | tr '\\n' ' ')\"", 0),
    ("zwei Leser in einer Zeile, einer gedeckt, einer nicht",
     'echo "a=$(cat $(ls /leer) </dev/null) b=$(cat $(ls /leer))"', 1),
]


def selbstmessung() -> int:
    """Misst den Pruefer an bekannten Formen, bevor er ein Bild prueft.

    Ein Pruefer, der eine echte Haengerzeile nicht findet, meldet den Lauf als
    gruen, ohne dass etwas fehlt. Die Formen hier sind die vier, die in diesem
    Bring-up Fehler entschieden haben.
    """
    fehler = 0
    for name, zeile, erwartet in SELBSTFELLE:
        fund = leser_ohne_ziel(zeile)
        if len(fund) == erwartet:
            print("ok - Pruefer selbst gemessen: %s" % name)
        else:
            print("not ok - Pruefer selbst gemessen: %s (erwartet %d Fund(e), gefunden %d: %s)"
                  % (name, erwartet, len(fund), fund))
            fehler += 1
    return fehler


def haupt() -> int:
    if len(sys.argv) != 2:
        print("usage: verify-v0z.py <firstlight.img von v0z>", file=sys.stderr)
        return 2
    # Der Vorgaenger ist noetig fuer den Diff, und sein Defaultpfad ist ein
    # Hostpfad: ein ad-hoc-Aufruf im Container ohne den Mount des Baurezepts
    # lief bisher in einen Traceback und sah aus wie ein Bildfehler (gemessen).
    # Ein fehlender Vorgaenger ist eine dunkle Pruefung, also eine Meldung.
    if not os.path.isfile(sys.argv[1]):
        print("nicht ok - Bild nicht erreichbar: " + sys.argv[1]); return 2
    if not os.path.isfile(V0Y):
        print("nicht ok - Vorgaengerbild nicht erreichbar: %s" % V0Y)
        print("nicht ok - ohne Vorgaenger gibt es keinen Diff, nur Anwesenheit; "
              "V0Y=<pfad> setzen wie im Baurezept")
        return 2
    neu = init_text(sys.argv[1])
    alt = init_text(V0Y)
    fehler = 0
    zahl = 0

    def pruef(cond: bool, meldung: str) -> None:
        nonlocal fehler, zahl
        zahl += 1
        if cond:
            print("ok - " + meldung)
        else:
            print("not ok - " + meldung)
            fehler += 1

    fehler += selbstmessung()

    # Das Nebenarchiv, an dem der Reihenfolgepruefer haengt, darf nicht gegen das
    # Bild veraltet sein: sonst misst ein Pruefer einen Stand, und ausgeliefert und
    # geflasht wird ein anderer. Der Vergleich fuehrt beide Hellen zum Init
    # zusammen - init_text() entpackt das Bild, newc ließt das Archiv.
    neben = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "new.cpio")
    if os.path.isfile(neben):
        ordner = tempfile.mkdtemp(prefix="v0z-archiv-")
        zielpfad = os.path.join(ordner, "a.cpio")
        with open(neben, "rb") as quelle, open(zielpfad, "wb") as ziel:
            ziel.write(quelle.read())
        archiv_init = {e["name"]: e for e in newc.read_cpio(zielpfad)}["init"]["content"].decode()
        pruef(archiv_init == neu,
              "Nebenarchiv und Bild fuehren denselben Init (beide %d B, bytegleich)" % len(neu)
              if archiv_init == neu else
              "Nebenarchiv und Bild fuehren verschiedenen Init (Bild %d B / Archiv %d B)"
              % (len(neu), len(archiv_init)))
    else:
        pruef(False, "Nebenarchiv nicht erreichbar, Reihenfolgepruefer misst einen "
                     "anderen Stand: " + neben)

    alts, neus = alt.splitlines(), neu.splitlines()
    diff = list(difflib.ndiff(alts, neus))
    geaendert = [z for z in diff if z.startswith("- ")]
    eingefuegt = [z for z in diff if z.startswith("+ ")]
    pruef(len(geaendert) == 1,
          "genau eine entfernte Zeile im Diff, es ist der Titel (gemessen: %d)" % len(geaendert))
    pruef(geaendert and "first-light v0y" in geaendert[0], "die entfernte Zeile traegt den alten Titel")
    pruef(any("first-light v0z" in z for z in eingefuegt),
          "der neue Titel v0z steht im Diff (%d Zeilen eingefuegt)" % len(eingefuegt))

    # Der Vorgaenger muss vollstaendig erhalten sein: jede seiner Zeilen steht
    # noch im neuen Bild, in derselben Reihenfolge (Diff ohne '-'-Zeilen).
    pruef(all(z in neu for z in alts if "first-light v0y" not in z),
          "jede Zeile des Vorgaengers steht noch drin (ausser dem Titel)")

    for msg in ("haengt: debugfs=$(grep -c ' - debugfs ' /proc/self/mountinfo)",
                "configfs=$(grep -c ' - configfs ' /proc/self/mountinfo)",
                "gadget: ordner=$(",
                "udcGadget=$(readlink /sys/class/udc/*/gadget 2>/dev/null)",
                "is_active=$(cat /sys/class/udc/*/is_active </dev/null 2>&1)",
                "speed=$(cat /sys/class/udc/*/current_speed </dev/null 2>&1)",
                "schritte: $(tail -6 /run/steps.log 2>/dev/null | tr '\\n' '|')",
                "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)",
                "v0z-Runde",
                "mkdir -p /sys/kernel/debug 2>/dev/null",
                "mount -t debugfs none /sys/kernel/debug 2>/dev/null; dfrc=$?",
                "mount -t configfs -o nodev,noexec,nosuid configfs /sys/kernel/config 2>/dev/null; cfrc=$?",
                "SC=$(ls /sys/class/udc/*/soft_connect 2>/dev/null | head -1)",
                "stext=$( { echo connect > ",
                "gebunden=$(cat \"/sys/kernel/config/usb_gadget/g1/UDC\" </dev/null 2>/dev/null)",
                "binden rc=$brc text=${btext:-ohne}",
                "connect rc=$src text=${stext:-ohne} pfad=$SC"):
        pruef(msg in neu, "Beweismal: %s" % msg[:78])

    pruef("first-light v0y" not in neu and "first-light v0x" not in neu,
          "keine aelteren Panel-Titel")
    # Die Messfelder des Vorgaengers, einzeln: ein Ersatz duerfte sie nicht
    # stumm entfernt haben; hier ist alles erhalten, weil nur eingefuegt wurde.
    for feld in ("debugfs=$(", "usb=$(", "modewert=$(", "controller-state=$(",
                 "udc-state=$(", "is_active=$(", "typc: state=$(", "pid1=$(",
                 "udcdateien=$(", "wdt bootstatus=$(", "letzter Schritt:"):
        pruef(feld in neu, "Messfeld des Vorgaengers erhalten: %s" % feld)

    blind = [(nr, fund) for nr, zeile in enumerate(neus, 1) for fund in leser_ohne_ziel(zeile)]
    pruef(len(blind) == 0, "kein Leser haelt die Standardeingabe offen (Fund: %s)" % blind[:4])
    pruef('echo connect > ' in neu and neu.count('echo connect > ') == 1,
          "das Wort connect steht genau einmal (der Handler kennt nur connect/disconnect)")
    pruef('echo 1 > "$SC"' not in neu or "v0s" in neu,
          "die alte 1 auf einen Phantomknoten ist nicht die einzige Setzung")
    pruef("mkdir -p /sys/kernel/config 2>/dev/null" in neu,
          "der configfs-Einhang hat sein Ziel (der Kernel legt es nicht an)")
    pruef(neu.count("mount -t debugfs") >= 3,
          "debugfs-Einhaenge: %d (frueh, in der v0s-Runde, in der v0z-Runde)" % neu.count("mount -t debugfs"))
    for w in ("done", "; do", "while"):
        pruef(neu.count(w) >= alt.count(w),
              "%s-Zaellung nicht kleiner (%d gegen %d im Vorgaenger)" % (w, neu.count(w), alt.count(w)))
    pruef(neu.isascii(), "fertige Init ist reines ASCII (Panel ohne UTF-Konsole)")
    pruef(sum(z.count("(") - z.count(")") for z in neus) == 0, "Klammer-Bilanz ueber alle Zeilen: 0")
    reihenfolge_ok = neu.index("mkdir -p /sys/kernel/config") < neu.index("SC=$(ls /sys/class/udc/*/soft_connect")
    pruef(reihenfolge_ok, "Reihenfolge: configfs-Einhang vor dem Knopfgriff")
    pruef(neu.index('gebunden=$(cat "/sys/kernel/config/usb_gadget/g1/UDC" </dev/null 2>/dev/null)')
          < neu.index("stext=$( { echo connect > "),
          "Reihenfolge: Bindung gelesen, bevor der Knopf gedrueckt wird")
    pruef(neu.index("echo connect > ") < neu.index("state=$(cat /sys/class/udc/*/state </dev/null 2>&1)"),
          "Reihenfolge: Knopf vor der Ruecklesung des Zustands")

    print("%d Beweismale, %d Fehler" % (zahl, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(haupt())
