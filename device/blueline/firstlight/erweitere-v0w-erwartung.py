#!/usr/bin/env python3
"""Gibt dem v0w-Block die zwei Zeilen, die drei Pruefungen des Blockwarts wecken.

Befund, gemessen mit tools/tap-vergleich.py gegen den v0u-Stand (145 ok, skip=4):
dem v0w-Block fehlten die Zeilen, die mit 'EINFANG' und 'ERWARTUNG' beginnen.
Ohne sie meldet der Wart zweimal 'skip' (Sammeldateien, Erwartungszeilen) und
eine dritte Pruefung faellt weg - der Stand ist 'gruen' mit 144 statt 145, und
die Zahlalone verrät das nicht.

Die zweite Ursache ist ein Satzzeichen, nicht ein Text: der Wart wirft jedes
Backtick-Paar, das einen Gedankenstrich enthaelt (tests/flash-block, Zeile 293),
still fort. Ein Block, der mit Gedankenstrichen schreibt, hat damit weniger
Beweislast als einer mit Bindestrichen, ohne dass eine Meldung das sagt. Dieser
Umbau schreibt die beiden Zeilen deshalb in rein ASCII und prueft jedes Paar
vor dem Eintragen gegen das ausgelieferte Bild - nicht gegen meine Erinnerung.
"""
from __future__ import annotations

import gzip
import importlib.util
import os
import re
import struct
import sys

WS = "/Users/gregor/hermes-workspace"
FL = WS + "/omarchy-mobile/device/blueline/firstlight"
PROTOKOLL = WS + "/omarchy-mobile/device/blueline/BRINGUP-M1.md"
BILD = WS + "/images/fl-v0w/firstlight.img"
RUNNER = FL + "/run-flash-observe.sh"

# Die Dateien, die der Runner nach dem Flash einsammelt, aus seiner Befehlsliste
# geschnitten (Zeile 147-156), nicht aus dem Vorgaengerblock abgeschrieben.
laeufer = open(RUNNER, encoding="utf-8").read()
SAMMELDATEIEN = re.findall(r'\("([a-z0-9._-]+\.(?:log|txt))"', laeufer)
assert len(SAMMELDATEIEN) == 10, "%d Sammeldateien in der Befehlsliste" % len(SAMMELDATEIEN)

d = open(BILD, "rb").read()
ks = struct.unpack_from("<I", d, 8)[0]
rd = 4096 + ((ks + 4095) // 4096) * 4096
pfad = "/tmp/erwartung-naeher.cpio"
with open(pfad, "wb") as offener:
    offener.write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
spec = importlib.util.spec_from_file_location("newc", FL + "/newc.py")
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)
init = {e["name"]: e for e in newc.read_cpio(pfad)}["init"]["content"].decode()

EINFANG = ("EINFANG nach dem Flash: der Runner sammelt die Belege selbst ueber Telnet "
           "ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der "
           "Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, "
           "`v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, "
           "`v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; "
           "alle in der Ausgabe-Ordner des Laufens. Fuer v0w kommt nichts dazu und "
           "faellt nichts weg: die Namen traegt der Runner, nicht das Bild, und der "
           "Block nennt sie, damit der Wart sie gegen die Befehlsliste halten kann.")
ERWARTUNG = ("ERWARTUNG v0w (20:5x, vor dem Flash festgelegt; jede Backtick-Zeichenkette "
             "ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel "
             "`Omarchy Mobile first-light v0w - RAM only, der Knopf wird gesucht` und in "
             "jedem Herzschlag-Block die Zeile `debugfs=$(ls` mit dem Inhalt des "
             "haengenden Zaehlkanals und `usb=$(ls` mit dem Inhalt seines usb-Zweigs. "
             "Die Nachbind-Runde nennt `write rc=` - dieselbe Messgroesse wie bei den "
             "Vorfaehrern, absichtlich unter demselben Wort -, dazu `vorher=$scvor`, "
             "`pfad=$SC`, `gefunden=$SZAHL`, `suche=$SCLISTE` und `scrca=$SCRCA`. Die "
             "Fuenf-Sekunden-Zeile nennt `spaeter 5s:` mit `sc1rc=$sc1rc` und "
             "`scrca=$SCRCA`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, "
             "`is_active=`, `controller-state=`, `letzter Schritt:`. Zwei Messgroessen, "
             "die in der Referenz vorkommen, liefert dieses Bild nicht und verspricht es "
             "auch nicht: die dwc3-Rolle und ein vbus-Feld, ihre Abwesenheit ist Bauart "
             "und kein Befund. Die Faelle, die dieses Bild ohne jeden Bus trennt, stehen "
             "in der Aufzaehlung darunter.")
# Paare, die der Wart fortwirft und die deshalb nichts versprechen duerfen:
# der Vergleich bleibt, damit das nicht wieder unbemerkt passiert.
for name, text in (("EINFANG", EINFANG), ("ERWARTUNG", ERWARTUNG)):
    paare = re.findall(r"`([^`]*)`", text)
    verworfen = [p for p in paare if "\u2014" in p]
    print("%s: %d Paare, %d davon mit Gedankenstrich (wuergen still fort)"
          % (name, len(paare), len(verworfen)))
    assert not verworfen
    assert text.isascii(), "%s traegt Nicht-ASCII" % name
    kurze = [p for p in paare if not (6 <= len(p) <= 140)]
    assert not kurze, "Paare ausserhalb der Laengengrenze: %s" % kurze

# Jede angesagte Zeichenkette muss im Bild stehen (derselbe Massstab wie der
# Wart, Zeile 336-341: Bild zuerst, Runner als zweite Quelle).
fehlend = []
for text in re.findall(r"`([^`]*)`", ERWARTUNG):
    if text not in init and text not in laeufer:
        fehlend.append(text)
for datei in re.findall(r"`([a-z0-9._-]+\.(?:log|txt))`", EINFANG):
    if datei not in laeufer:
        fehlend.append("Sammeldatei " + datei)
if fehlend:
    print("NICHT NACHWEISBAR: %s" % "; ".join(fehlend))
    raise SystemExit(1)
print("alle %d angesagten Zeichenketten sind im Bild oder im Runner nachgewiesen"
      % (len(re.findall(r"`([^`]*)`", ERWARTUNG)) + len(SAMMELDATEIEN)))

roh = open(PROTOKOLL, encoding="utf-8").read()
blockanfang = roh.index("## FLASH-BEREIT v0w")
blockende = roh.index("## FLASH-BEREIT v0v", blockanfang)
block = roh[blockanfang:blockende]
assert "EINFANG" not in block, "die EINFANG-Zeile steht schon im Block"
alt = next(z for z in block.splitlines() if z.startswith("ERWARTUNG v0w"))
assert block.count(alt) == 1
neu_text = block.replace(alt, ERWARTUNG + "\n\n" + EINFANG, 1)
assert "ERWARTUNG v0w" in neu_text and "EINFANG nach dem Flash" in neu_text
assert len(neu_text) - len(block) == len(ERWARTUNG) + len(EINFANG) - len(alt) + 2
ergebnis = roh[:blockanfang] + neu_text + roh[blockende:]
assert ergebnis.count("## FLASH-BEREIT v0w") == 1
if __name__ == "__main__":
    open(PROTOKOLL, "w", encoding="utf-8").write(ergebnis)
    print("eingetragen: ERWARTUNG ersetzt, EINFANG neu (%d B)" % (len(ergebnis) - len(roh)))
