#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft den Slot-Block in starte-abgriff.py gegen einen falschen fastboot.

Warum es diese Datei gibt: die Suite parst nur tests/*, sie erreicht also kein
einziges Skript aus diesem Ordner — "Suite gruen" (148 ok, 4 skip, 0 not-ok,
Stand 2026-11-02) sagt ueber starte-abgriff.py nichts aus.

Der Laeufer laeuft in zwei Zustaenden gegen einen falschen fastboot:
antwortend und schweigend. In beiden erwartet: genau ein --set-active=a, davor
fuenf getvar in der Reihenfolge der Doku, danach zwei, der Start erst nach dem
Setzen, kein Traceback.

Der antwortende Nachbau haelt die Reihenfolge, die an diesem Geraet gemessen
ist: Wert, dann OKAY, dann finished auf dem Fehlerkanal; der Slot-Anhaengsel
bleibt im Text ("slot-retry-count:a: 3"). Nur deshalb fiel der Fehler auf, den
dieser Pruefer gefunden hat: stand() nahm die LETZTE Zeile und protokollierte
bei jedem getvar die Zeit statt des Wertes. Der schweigende Zustand gehoert
dazu — die Halteschleife muss genau dann weiterlaufen, wenn das Telefon nicht
antwortet.

Haengt noch nicht in tests/all; wer ihn einhaengt, bekommt einen Punkt mehr und
zieht die kanonische Zahl in BRINGUP-M1.md nach.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
LAUFER = os.path.join(HIER, "starte-abgriff.py")
GPT = os.path.join(HIER, "pruefe-gpt.py")
WERTE = 7                                   # 5 Abfragen vorher + 2 nachher
FEHLER = 0


def sage(text, ok):
    global FEHLER
    print("%s - %s" % ("ok" if ok else "not ok", text), flush=True)
    if not ok:
        FEHLER += 1


def fake_shreib(pfad, protokoll, zustand):
    """Der falsche fastboot: protokolliert jeden Aufruf, antwortet wie ABOOT.

    Drei Zustaende, weil das Geraet alle drei schon geliefert hat: Wert plus
    OKAY plus finished (normal), nur OKAY plus finished (Antwort ohne Wert), und
    garnichts (brachliegende Leitung im Fastboot).
    """
    zeilen = ['#!/bin/sh', 'echo "$@" >> "%s"' % protokoll, 'case "$1" in',
              '  devices) echo "PIXEL3-SERIAL\\t fastboot" ;;']
    if zustand == "antwortend":
        zeilen += ['  getvar) echo "$2: wert-gemessen"; echo "OKAY [  0.001s]" ;;',
                   "  --set-active=a) echo \"Setting current slot to 'a' OKAY\" ;;",
                   '  boot) echo "OKAY [  1.000s]" ;;', '  *) echo "OKAY" ;;', 'esac',
                   'echo "finished. total time: 0.010s" >&2']
    elif zustand == "nur Zeit":
        zeilen += ['  getvar) echo "OKAY [  0.001s]" ;;', '  *) echo "OKAY" ;;', 'esac',
                   'echo "finished. total time: 0.010s" >&2']
    else:                                   # schweigend: keine Antwort, auch keine Zeit
        zeilen += ['  boot) echo "OKAY" ;;', '  *) ;;', 'esac']
    open(pfad, "w").write("\n".join(zeilen) + "\n")
    os.chmod(pfad, 0o755)


def laeufer_kopiere(text, fake):
    """Den Laeufer bis kurz vor den echten Abgriff uebernehmen, Portfragen stellen."""
    text = text.split("greife-kalibrier.py")[0]
    text = text[:text.rfind("subprocess.run(")] + 'print("STUB: Abgriff nicht gerufen")\n'
    out = []
    for zeile in text.splitlines(True):
        if zeile.startswith(("FB =", "FB=")):
            out.append("FB = %r\n" % fake)
        elif zeile.strip() == "def offen():":
            # Erste Antwort zu (der Zyklus startet bei zuem Telefon), danach offen —
            # sonst ueberspringt der Laeufer seinen eigenen Slot-Block.
            out += [zeile, '    offen.n = getattr(offen, "n", 0) + 1\n',
                    "    return offen.n > 1\n"]
        else:
            out.append(zeile)
    return "".join(out)


ordner = tempfile.mkdtemp(prefix="pruefe-slotzyklus-")
try:
    FAKE = os.path.join(ordner, "fastboot")
    PROTOKOLL = os.path.join(ordner, "anrufe.log")
    KOPIE = os.path.join(ordner, "starte-abgriff.py")
    quelltext = open(LAUFER, encoding="utf-8").read()
    for pfad in (LAUFER, GPT):
        try:
            compile(open(pfad, encoding="utf-8").read(), pfad, "exec")
            sage("Syntax: %s" % os.path.relpath(pfad, REPO), True)
        except SyntaxError as warum:
            sage("Syntax: %s — %s" % (os.path.relpath(pfad, REPO), warum), False)

    kopie_text = laeufer_kopiere(quelltext, FAKE)
    compile(kopie_text, "kopie", "exec")
    sage("Nachbau vollstaendig (Slot-Block, Hafen-Stub, falscher fastboot)",
         "offen.n = getattr" in kopie_text and FAKE in kopie_text
         and "--set-active=a" in kopie_text)
    open(KOPIE, "w", encoding="utf-8").write(kopie_text)

    for zustand in ("antwortend", "nur Zeit", "schweigend"):
        fake_shreib(FAKE, PROTOKOLL, zustand)
        open(PROTOKOLL, "w").close()
        lauf = subprocess.run([sys.executable, "-u", KOPIE], capture_output=True,
                              text=True, timeout=180, cwd=ordner)
        anrufe = [z.strip() for z in open(PROTOKOLL, encoding="utf-8") if z.strip()]
        aus = lauf.stdout + lauf.stderr
        setzte = [i for i, a in enumerate(anrufe) if a.startswith("--set-active=a")]
        wo = setzte[0] if setzte else -1
        sage("[%s] Exit 0, kein Traceback" % zustand,
             lauf.returncode == 0 and "Traceback" not in aus)
        sage("[%s] genau ein Slot-Setzen im Zyklus" % zustand, len(setzte) == 1)
        # Vor dem Setzen steht ausser den fuenf Abfragen noch das Sichtbarmachen
        # des Geraets — verglichen wird nur die Abfrageliste, sonst findet die
        # Pruefung ihre eigene Reihenfolge nicht (gemessen: 'devices' im Vorlauf).
        davor = [a for a in anrufe[:wo] if a.startswith("getvar")]
        sage("[%s] fuenf getvar VOR dem Setzen, in der Reihenfolge der Doku" % zustand,
             davor == ["getvar current-slot", "getvar slot-retry-count:a",
                       "getvar slot-retry-count:b", "getvar slot-successful:a",
                       "getvar slot-successful:b"])
        sage("[%s] danach zwei getvar, erst dann der Start" % zustand,
             [a for a in anrufe[wo + 1:] if a.startswith("getvar")]
             == ["getvar current-slot", "getvar slot-retry-count:a"]
             and any(a.startswith("boot ") for a in anrufe[wo + 1:]))
        abgelesen = [z for z in aus.splitlines()
                     if "vorher current" in z or "vorher slot" in z or "nachher " in z]
        sage("[%s] fuenf Klemmen vorher und zwei nachher abgeschrieben (%d/%d)"
             % (zustand, len(abgelesen), WERTE), len(abgelesen) == WERTE)
        erwartet = {"antwortend": "wert-gemessen", "nur Zeit": "kein Wert in der Antwort",
                    "schweigend": "keine Antwort"}[zustand]
        # schaedig ist nicht das Wort, sondern eine Abfrage, deren Text MIT
        # der Zeitzeile anfaengt — die Benennung "kein Wert (letzte Zeile: …)"
        # nennt die Zeit, ohne sie als Wert auszugeben.
        verfuelscht = [z for z in abgelesen
                       if z.split(": ", 1)[-1].strip().lower().startswith("finished")]
        sage("[%s] alle sieben Abfragen melden '%s', keine meldet eine Zeit als Wert "
             "(%d verdaechtig)" % (zustand, erwartet, len(verfuelscht)),
             all(erwartet in z for z in abgelesen) and not verfuelscht)
        if zustand == "antwortend":
            sage("[%s] das Setzen steht mit fastboot-Antwort im Text" % zustand,
                 "setze a" in aus)
finally:
    shutil.rmtree(ordner, ignore_errors=True)

print("\nSlot-Zyklus-Pruefung: fehler=%d" % FEHLER)
sys.exit(1 if FEHLER else 0)
