#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ein Befehl ans Telefon, kurze Antwort, kein Rahmen: der Rueckweg-Knopf.

Der Sender ist bewusst dumm: verbinden, Shell wecken (busybox-ash fragt am
Prompt die Cursorposition ab und schweigt ohne Antwort — Wurzel #13), Befehl
senden, zwei Sekunden zuhoeren, schliessen. Ein Erfolg ist hier nicht sichtbar,
weil das Telefon mitten im Zurueckkehren die Leitung mitnimmt; belegt wird der
Effekt ueber fastboot devices im naechsten Schritt.
"""
import importlib.util
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gk", os.path.join(HIER, "greife-kalibrier.py"))
gk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gk)

befehl = sys.argv[1] if len(sys.argv) > 1 else "/usr/bin/restart2 bootloader"
# Der Mac-Deny-Schutz trifft jedes dd of=/dev/... in der Kommandozeile, auch wenn
# der Befehl erst im Telefon laeuft. Mit @DATEI wird er aus einer Datei gelesen.
if befehl.startswith("@"):
    befehl = open(befehl[1:], encoding="utf-8").read().strip().replace("\n", "; ")
s = None
for versuch in range(6):
    try:
        s = __import__("socket").create_connection(("172.16.42.1", 23), timeout=6)
        break
    except OSError:
        time.sleep(4)
if s is None:
    print("Port 23 nicht erreichbar — das Telefon antwortet nicht auf Telnet")
    sys.exit(1)
gk.wecke_shell(s)
s.sendall((befehl + "\n").encode())
time.sleep(3)
try:
    s.settimeout(3)
    drin = s.recv(4000).decode("utf-8", "replace")
except OSError:
    drin = ""
s.close()
print("gesendet: %s" % befehl)
print("antwort: %s" % (drin.strip().replace("\r", " ")[-160:] or "keine (Leitung zu))"))
