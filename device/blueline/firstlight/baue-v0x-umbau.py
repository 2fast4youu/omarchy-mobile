#!/usr/bin/env python3
"""Der Umbau von v0w nach v0x, als EIN Block - nachdem dreimaliges Flicken eine
doppelte D2-Folge und einen Doppel-Anker hinterlassen hatte (gemessen: 10
arbeit.append-Zeilen fuer 8 Eingriffe, Schritt 7 meldete 0 Fundstellen, weil ein
vorheriger Schritt seinen Anker schon verbrauchte).

Reihenfolge mit Grund, jeder Anker wird aus dem geladenen Archiv geschnitten:
  A  Titel v0w -> v0x
  B  debugfs mount direkt nach dem PATH, vor jedem Herzschlag (v0w mountete
     erst mitten in der Bind-Runde; die Herzschlaege davor waren dunkel)
  C  Fallback auf den Phantompfad -> '' (soft_connect als Datei existiert in
     diesem Kernel nicht, gemessen: grep ueber den ganzen Kernelbaum, 0 Dateien)
  D  mode-Suche und -Lesung nach dem Beschreibbar-Test (der modus-Knopf IST
     real: drivers/usb/dwc3/debugfs.c:1029, 0644, unter dem Geraetenamen in
     usb_debug_root, common.c:422)
  D2 die beiden Beweiszeilen tragen modepfad= und modewert=
  E  modewert im Herzschlag
  F  zuletzt: der nackte test -w des Vorgaengers muss weg - er ueberschrieb
     SCRCA=9 (kein Fund) zu SCRCA=1, stumm. Zuletzte, weil D ihn als Anker
     benutzt: wer zuerst loescht, zaehlt danach null.
"""
from __future__ import annotations

import importlib.util
import os
import sys

Q, E, B, N = chr(34), chr(39), chr(92), chr(10)
I12 = " " * 12
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

spec = importlib.util.spec_from_file_location("pwx", os.path.join(HIER, "patch-v0x.py"))
assert spec is not None and spec.loader is not None, "patch-v0x.py nicht ladbar"
pwx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pwx)          # fuehrt nur Konstanten und Funktionen aus


def umbau(init, a):
    text = init
    arbeit = []

    # A) Titel
    arbeit.append((a["titel"], a["titel"].replace("v0w", "v0x")))

    # B) debugfs vor allem, was den Zaehlkanal liest. Der mount in der Runde
    #    bleibt: haengt schon, der zweite schlaegt fehl, der Exit zeigt in der
    #    Fehlerausgabe, welcher Fall vorlag.
    arbeit.append((a["pfad"],
                   a["pfad"] + N
                   + "# v0x: debugfs vor der ersten Bind-Runde (v0w haengte es erst" + N
                   + "# mitten in der Runde ein, die Herzschlaege davor waren dunkel)." + N
                   + "mount -t debugfs none /sys/kernel/debug 2>/dev/null || true"))

    # C) Kein Pfad-Fallback mehr: der v0w-Fallback setzte unbedingt auf einen
    #    Pfad, den es in diesem Kernel nicht gibt. Der nackte test -w des
    #    Vorgaengers gehoert mit in die Ersetzung - in einer frueheren Fassung
    #    lief das als eigener Loeschschritt, der den Test tilgte, statt ihn in
    #    seine Bedingung zu setzen (gemessen: 'test -w: 0 Zeilen').
    arbeit.append((a["fallback"] + N + a["pruef"],
                   I12 + '[ -n "$SC" ] || SC=""   # v0x: der v0w-Fallback war ein Phantom' + N
                   + I12 + 'if [ -n "$SC" ]; then test -w "$SC"; SCRCA=$?; else SCRCA=9; fi'))

    # D) entfaellt als Schritt: die modus-Suche folgt in F, direkt nach dem
    #    bedingten Test. Ein eigener Schritt auf die test-Zeile war die Quelle
    #    der ganzen Reihenfolge-Verdrehung (Anker wird durch denselben Lauf
    #    ersetzt, bevor der naechste ihn zaehlt).

    # D2) Die Beweiszeilen tragen das Messfeld.
    arbeit.append(("scrca=$SCRCA rc0=$sc0rc",
                   "scrca=$SCRCA modepfad=$MODENEUGEFUNDEN modewert=$MODW rc0=$sc0rc"))
    arbeit.append(("scrca=$SCRCA gefunden=$SZAHL, ",
                   "scrca=$SCRCA gefunden=$SZAHL modewert=$MODW, "))

    # E) modewert im Herzschlag, am Ende derselben Zeile, die v0w schrieb.
    alt_herz = a["herz"]
    neu_herz = ('              echo ' + Q + "debugfs=$(ls /sys/kernel/debug 2>/dev/null | "
                + pwx.TRA + " usb=$(ls /sys/kernel/debug/usb 2>/dev/null | " + pwx.TRA
                + " modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1)"
                + " 2>/dev/null)" + Q)
    arbeit.append((alt_herz, neu_herz))

    # F) zuletzt der modus-Block: D hat die nackte test-Zeile als Anker benutzt,
    #    sie steht jetzt in ihrer Bedingung; die Suche-und-Lesung fuegen wir nach
    #    dem bedingten Test ein. Zuletzte, weil ihr Anker bis dahin unangetastet
    #    bleiben musste (Nacher-Loeschung vor Zaehlung war dreimal die Ursache
    #    von '0 Fundstellen').
    bedingt = I12 + 'if [ -n "$SC" ]; then test -w "$SC"; SCRCA=$?; else SCRCA=9; fi'
    arbeit.append((bedingt,
                   bedingt + N
                   + I12 + "MODEPFAD=$(find /sys/kernel/debug -name mode 2>/dev/null | head -2)" + N
                   + I12 + 'MODENEUGEFUNDEN=$(printf %s "$MODEPFAD" 2>/dev/null | grep -c . 2>/dev/null)' + N
                   + I12 + 'MODE=$(printf %s "$MODEPFAD" 2>/dev/null | head -1)' + N
                   + I12 + 'MODW=$( { cat "$MODE"; } 2>&1 ); MODWRC=$?'))
    # (Der Zaehler war zuerst 'wc -l': eine Befehlsersetzung frisst den
    #  Abschieds-Zeilenumbruch, und 'wc -l' zaehlt Zeilen AN Hand ihrer
    #  Umbrueche - ein einziger Fund haette 0 gemeldet. 'grep -c .' ist die
    #  zaehlweise, die SZAHL im Vorgaetterbild schon bewiesen hat.)

    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)

    offen, zu = text.count("("), text.count(")")
    print("  Bilanz nach dem Umbau: %d ( gegen %d )" % (offen, zu))
    assert offen == zu, "Paren-Bilanz verschoben: %d offen, %d zu" % (offen, zu)
    for nr, zeile in enumerate(text.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        inside = zeile[zeile.find(Q) + 1:zeile.rfind(Q)] if zeile.count(Q) >= 2 else ""
        if inside.count("(") != inside.count(")"):
            print("  not ok - Zeile %d: Echo-Kette %d ( gegen %d )"
                  % (nr, inside.count("("), inside.count(")")))
    # Der Beschreibbar-Test darf nur noch in seiner Bedingung stehen. (Die
    # Bedingung liegt in DERSSELBEN Zeile wie der Test - eine fruehere Fassung
    # dieser Pruefung zaehte die Zeile als 'nackt' und fand null, weil der
    # nackte Einzeltest geloescht war und der bedingte nicht auf 'test' begann.)
    tests = [x for x in text.splitlines() if "test -w " in x]
    kahl = [x for x in tests if "if [" not in x or "then" not in x]
    assert len(tests) == 1 and not kahl, \
        "test -w: %d Zeilen, %d davon nackt, erwartet eine, in der Bedingung" % (len(tests), len(kahl))
    return text


pwx.umbau = umbau
if __name__ == "__main__":
    sys.exit(pwx.haupt())
