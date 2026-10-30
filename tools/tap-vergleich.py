#!/usr/bin/env python3
"""Legt zwei TAP-Texte nebeneinander, ohne dass Maßzahlen den Vergleich trügen.

Anlass, gemessen: der Textvergleich in suite-auf-zwei-staenden.sh meldete
Prüfungen als 'nur in Stand 1' und 'nur in Stand 2', die in Wahrheit dieselben
Prüfungen mit verschiedenen Maßzahlen waren ('12 Erwartungszeilen nachgewiesen
(Bild 19775528 B entpackt...)' gegen dieselbe Prüfung mit einer anderen Zahl).
Ein Vergleich, der eine Umbenennung von einer Abwesenheit nicht unterscheidet,
erzeugt Differenzen, die keine sind - und uebersieht dabei die eine, die eine ist.

Dieses Programm normalisiert vor dem Vergleich: Hashes, Zahlen mit und ohne
Tausenderpunkte, Byteangaben. Dann vergleicht es die Nummer im TAP-Plan, nicht
die Zeile im Text. Eine Pruefung, die in einem Stand fehlt, ist eine Zahl, die
fehlt - nicht ein Wort, das anders dasteht.
"""
from __future__ import annotations

import re
import sys

def normalisiere(text: str) -> str:
    text = re.sub(r"\b[0-9a-f]{6,}\b", "<hash>", text)
    text = re.sub(r"\b\d[\d ]*\d\s*(B|B/s|s|ms)\b", "<zahl>", text)
    text = re.sub(r"\b\d+\b", "<z>", text)
    return text.strip()

def lese(pfad: str) -> dict[int, str]:
    pruefungen: dict[int, str] = {}
    nummer = 0
    with open(pfad, encoding="utf-8", errors="replace") as datei:
        for zeile in datei:
            zeile = zeile.rstrip("\n")
            if not zeile:
                continue
            if zeile.startswith(("ok ", "not ok ", "ok -", "not ok -")):
                nummer += 1
                rest = re.sub(r"^(not )?ok\s*(\d+\s*-\s*)?", "", zeile)
                pruefungen[nummer] = normalisiere(rest)
            elif not zeile.startswith(("1..", "#")):
                # Fliesstext einer Pruefung: der Name traegt ihn, Zahl bleibt gleich.
                continue
    return pruefungen

if __name__ == "__main__":
    a, b = lese(sys.argv[1]), lese(sys.argv[2])
    print("Stand 1: %d Pruefungen, Stand 2: %d Pruefungen" % (len(a), len(b)))
    nur1 = sorted(set(a) - set(b))
    nur2 = sorted(set(b) - set(a))
    for n in nur1:
        print("  NUR IN STAND 1, Nummer %d: %s" % (n, a[n][:140]))
    for n in nur2:
        print("  NUR IN STAND 2, Nummer %d: %s" % (n, b[n][:140]))
    # Gleiche Nummer, anderer Text = umbenannt, nicht fehlend.
    umbenannt = [n for n in sorted(set(a) & set(b)) if a[n] != b[n]]
    print("\nGleiche Nummer, anderer Text (%d):" % len(umbenannt))
    for n in umbenannt[:12]:
        print("  Nummer %d:\n    Stand 1: %s\n    Stand 2: %s" % (n, a[n][:132], b[n][:132]))
    # Skip-Zahlen, weil eine schlafende Pruefung keine grüne Zahl ist.
    for name, sammlung in (("Stand 1", a), ("Stand 2", b)):
        skips = [n for n, t in sammlung.items() if "# skip" in t.lower()]
        print("%s: %d Pruefungen, davon %d mit skip" % (name, len(sammlung), len(skips)))
