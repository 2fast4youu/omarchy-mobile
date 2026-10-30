#!/usr/bin/env python3
"""v0x-Beweismale am fertigen Bild: debugfs frueh, kein Phantom, der modus gemessen.

Gebaut auf verify-v0w.py, dem die drei neuen Befunde eingearbeitet sind (alle an
android-mainline/kernel-pmos gemessen, 2026-10-30 abends):

1. soft_connect als Datei existiert in diesem Kernel nicht (grep ueber den
   ganzen Baum: 0 Dateien mit "soft_connect" als String). Der v0w-Fallback
   '[ -n "$SC" ] || SC=...' setzte trotzdem unbedingt auf den Phantompfad.
   v0x setzt ohne Fund auf '' und laesst den Test aus (SCRCA=9).
2. Der modus-Knopf ist real (drivers/usb/dwc3/debugfs.c:1029, 0644, unter dem
   Geraetenamen in usb_debug_root, common.c:422). v0x sucht ihn, liest ihn und
   meldet modepfad=/modewert= in beiden Beweiszeilen und im Herzschlag.
3. debugfs wurde in v0w erst mitten in der Bind-Runde einghaengt; die
   Herzschlaege davor waren dunkel. v0x haengt es direkt nach dem PATH ein.

Der modus wird gelesen, NICHT geschrieben: 'peripheral' hineinzudruecken ist
ein eigener Versuch und gehoert nicht in ein Bild, das erst messen soll.
"""
from __future__ import annotations

import importlib.util
import os
import struct
import sys
import gzip

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("newc", os.path.join(HERE, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

# Anwesenheit: die Felder, die Herzschlag und Beweiszeilen melden muessen.
DA = ("first-light v0x", "SCDATEIEN=$(find", 'SC=$(printf', '[ -n "$SC" ] ||',
      "test -w ", "SCRCA=$?", "gefunden=$SZAHL", "suche=$SCLISTE", "scrca=$SCRCA",
      "debugfs=$(ls", "usb=$(ls", "mount -t debugfs", "write rc=", "vorher=$scvor",
      "rc0=$sc0rc", "rc1=$sc1rc", "spaeter 5s", "pfad=$SC", "typc: state=",
      "kein Knopf", "echo 0xD002 >", "debug shell armed", "telnetd -l /bin/sh",
      'SC=""', "MODEPFAD=$(find", "MODE=$(printf", "MODW=$( { cat",
      "modepfad=$MODENEUGEFUNDEN", "modewert=$MODW",
      "find /sys/kernel/debug -name mode")
# Abwesenheit: die Annahmen frueherer Bilder, unbedingt gesetzt, und ihre Titel.
WEG = ("first-light v0w", "first-light v0v", "first-light v0u", "first-light v0t",
       "first-light v0s", "first-light v0r", "first-light v0q", "SC2=",
       "beide Knoten:", '[ -n "$SC" ] || SC=/sys')
suche_vor_annahme = 1
ZEILEN_MIN = 3
QUOTE_MAX = 2


def init_text(bild: str) -> str:
    d = open(bild, "rb").read()
    page = 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = page + ((ks + page - 1) // page) * page
    raw = gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]])
    with open("/tmp/v0x-pruef.cpio", "wb") as offen:
        offen.write(raw)
    return {e["name"]: e for e in newc.read_cpio("/tmp/v0x-pruef.cpio")}[
        "init"]["content"].decode()


def zeilennummer(init: str, teil: str) -> int:
    for nr, zeile in enumerate(init.splitlines(), 1):
        if teil in zeile:
            return nr
    return 0


def reihenfolge(init: str) -> int:
    fehler = 0
    z = init.splitlines()
    suche = zeilennummer(init, "SCDATEIEN=$(find")
    annahme = zeilennummer(init, '[ -n "$SC" ] ||')
    test = zeilennummer(init, "test -w ")
    erster = zeilennummer(init, "sc0rc=$?")
    zweiter = zeilennummer(init, "sc1rc=$?")
    probe = zeilennummer(init, "$SCRCA -eq 0")
    mount = zeilennummer(init, "mount -t debugfs")
    modus = zeilennummer(init, "MODEPFAD=$(find")
    modew = zeilennummer(init, "MODW=$( { cat")
    for name, wert in (("Suche", suche), ("Annahme", annahme), ("Beschreibbar-Test", test),
                       ("erster Write", erster), ("zweiter Write", zweiter),
                       ("Write-Bedingung", probe), ("debugfs-Mount", mount),
                       ("modus-Suche", modus), ("modus-Lesung", modew)):
        if not wert:
            print("not ok - %s: keine Zeile im fertigen Init" % name)
            fehler += 1
    if fehler:
        return fehler
    # Der FRUEHE Mount muss vor dem ersten Herzschlag-Satz liegen, der den
    # Zaehlkanal liest ( Herzschlag-Zeile 'debugfs=$(ls'), und vor der ersten
    # Bind-Runde. Der spaetere Mount in der Runde darf bleiben (idempotent).
    herz = zeilennummer(init, 'echo "debugfs=$(ls /sys/kernel/debug')
    binds = zeilennummer(init, "weicher-bind $rb:")
    if mount < herz and mount < binds:
        print("ok - debugfs-Mount in Zeile %d, vor Herzschlag (%d) und Bind-Runde (%d)"
              % (mount, herz, binds))
    else:
        print("not ok - Mount Zeile %d, Herzschlag %d, Bind-Runde %d"
              % (mount, herz, binds)); fehler += 1
    if suche < annahme:
        print("ok - Suche in Zeile %d, Annahme in Zeile %d" % (suche, annahme))
    else:
        print("not ok - die Annahme (Zeile %d) steht vor der Suche (Zeile %d)"
              % (annahme, suche)); fehler += 1
    if annahme < test < erster and annahme < test < zweiter:
        print("ok - Beschreibbar-Test (Zeile %d) liegt vor beiden Writes (%d, %d)"
              % (test, erster, zweiter))
    else:
        print("not ok - Reihenfolge falsch: Test %d, Writes %d und %d"
              % (test, erster, zweiter)); fehler += 1
    # Der modus wird erst gesucht, dann gelesen, dann gemeldet.
    berichte = [n for n, x in enumerate(z, 1) if "modewert=$MODW" in x and ">" in x]
    if modus < modew and modew < min(berichte):
        print("ok - modus: suchen %d, lesen %d, melden %s" % (modus, modew, berichte))
    else:
        print("not ok - modus-Reihenfolge: %d, %d, melden %s"
              % (modus, modew, berichte)); fehler += 1
    # Der Platzhalter darf nirgends unbedingt auf einen Pfad gesetzt werden.
    unbedingt = [n for n, x in enumerate(z, 1)
                 if "soft_connect" in x and "/sys/kernel/debug/usb/" in x
                 and "||" not in x and "find" not in x and not x.lstrip().startswith("#")]
    if unbedingt:
        print("not ok - soft_connect-Pfad unbedingt gesetzt in Zeile(n) %s" % unbedingt); fehler += 1
    else:
        print("ok - soft_connect wird nirgends unbedingt auf einen Pfad gesetzt")
    # Der nackte test -w des Vorgaengers darf nicht neben dem bedingten stehen
    # bleiben: am ersten v0x-Bau gemessen schrieb er SCRCA=9 (kein Fund) zu
    # SCRCA=1 um, unterhalb jedes Beweises. Ein Test ohne 'if' ist eine Messung,
    # die ein nachfolgender nackter Test still schreibend ueberschreibt.
    kahl = [n for n, x in enumerate(z, 1)
            if "test -w " in x.lstrip() and "if [" not in x and "then" not in x]
    gesamt = sum(1 for x in z if "test -w " in x)
    if not kahl and gesamt == 1:
        print("ok - der einzige Beschreibbar-Test steht in seiner Bedingung, kein nackter Duplikat")
    else:
        print("not ok - test -w: %d Zeile(n) insgesamt, %d nackt (erwartet 1, 0)" % (gesamt, len(kahl))); fehler += 1
    # Der modus-Pfad darf ebenso nirgends unbedingt gesetzt sein (suche statt annahme).
    moduspfad_unbedingt = [n for n, x in enumerate(z, 1)
                           if "/sys/kernel/debug/usb/" in x and "/mode" in x
                           and not x.lstrip().startswith("#")]
    if moduspfad_unbedingt:
        print("not ok - modus-Pfad in Zeile(n) %s als festes Wissen gesetzt"
              % moduspfad_unbedingt); fehler += 1
    else:
        print("ok - der modus-Pfad wird nur gefunden, nie gesetzt")
    return fehler


def quote_pruefung(init: str) -> int:
    fehler = 0
    gezaehlt = 0
    for nr, zeile in enumerate(init.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        anfang = zeile.find(chr(34))
        ende = zeile.rfind(chr(34))
        if not (0 <= anfang < ende):
            continue
        gezaehlt += 1
        if zeile.count(chr(34)) % 2:
            print("not ok - Zeile %d: %d Double-Quotes, die Zeile endet offen"
                  % (nr, zeile.count(chr(34)))); fehler += 1
        if zeile.count(chr(34)) > QUOTE_MAX + 2:
            print("nicht ok - Zeile %d traegt %d Double-Quotes (erwartet hoechstens %d)"
                  % (nr, zeile.count(chr(34)), QUOTE_MAX + 2))
    print("ok - %d Echo-Zeilen auf geschlossene Double-Quotes geprueft" % gezaehlt)
    return fehler


def klammer_pruefung(init: str) -> int:
    fehler = 0
    if init.count("(") == init.count(")"):
        print("ok - globale Klammerbilanz: %d offen, %d zu"
              % (init.count("("), init.count(")")))
    else:
        print("not ok - globale Klammerbilanz: %d offen, %d zu"
              % (init.count("("), init.count(")")))
        fehler += 1
    for nr, zeile in enumerate(init.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        anfang = zeile.find(chr(34))
        ende = zeile.rfind(chr(34))
        if not (0 <= anfang < ende):
            continue
        text = zeile[anfang + 1:ende].replace(chr(92) + "(", "(").replace(chr(92) + ")", ")")
        if text.count("(") != text.count(")"):
            print("not ok - Zeile %d: Echo-Kette mit %d ( gegen %d )"
                  % (nr, text.count("("), text.count(")")))
            fehler += 1
    return fehler


def main() -> int:
    init = init_text(sys.argv[1])
    fehler = 0
    for m in DA:
        if m in init:
            print("ok - Beweismal vorhanden: " + m)
        else:
            print("not ok - Beweismal fehlt im fertigen Bild: " + m); fehler += 1
    for w in WEG:
        if w in init:
            print("not ok - Rest eines frueheren Bildes: " + w); fehler += 1
        else:
            print("ok - kein Rest: " + w)
    ist = init.count("bDeviceState")
    if ist == 0:
        print("ok - blinde Lesungen: bDeviceState 0 mal")
    else:
        print("not ok - bDeviceState %d mal, erwartet 0" % ist); fehler += 1
    n = sum(1 for x in init.splitlines() if "> /dev/kmsg" in x and "omamobile-blueline:" in x)
    if n >= ZEILEN_MIN:
        print("ok - Beweiszeilen nach /dev/kmsg: %d" % n)
    else:
        print("not ok - nur %d Beweiszeilen, erwartet mindestens %d" % (n, ZEILEN_MIN)); fehler += 1
    if "sc0rc=$?" in init and "sc1rc=$?" in init:
        print("ok - beide soft_connect-Writes halten ihren Rueckgabewert")
    else:
        print("not ok - ein soft_connect-Write haelt keinen Rueckgabewert"); fehler += 1
    mounts = [nr for nr, x in enumerate(init.splitlines(), 1) if "mount -t debugfs" in x]
    if len(mounts) == 2:
        print("ok - debugfs-Mounts: %d (der fruehe und der idempotente in der Runde)" % len(mounts))
    else:
        print("not ok - debugfs-Mounts %d, erwartet 2 (frueh + idempotent)" % len(mounts)); fehler += 1
    fehler += reihenfolge(init)
    fehler += quote_pruefung(init)
    fehler += klammer_pruefung(init)
    if init.isascii():
        print("ok - fertige Init ist reines ASCII")
    else:
        print("not ok - fertige Init traegt Nicht-ASCII"); fehler += 1
    print("%d Beweismale, %d Fehler" % (len(DA) + len(WEG) + 12, fehler))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
