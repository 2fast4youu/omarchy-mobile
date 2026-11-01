#!/usr/bin/env python3
"""Sieht bei einem RAM-Start auf beide Seiten der Leitung.

Grund: um 20:27 meldete der Abgriff „Fenster nicht offen", obwohl dasselbe Bild
um 20:13 dreihundertsechzig Sekunden lang eine Shell gab. Zwei Erklaerungen sind
verschieden: das Telefon lief gar nicht, oder es lief und der Mac sah es nicht
— die Netzfunktion des Telefons ist eine eigene Schnittstelle (en8), und die ist
ohne Gegenstelle `inactive` und ohne Adresse. Ein Port-Test allein trennt die
beiden Faelle nicht, also wird hier jede Runde beides notiert: was der Bus
zeigt, was en8 meldet, und was der Port sagt.
"""
import re
import socket
import subprocess
import sys
import time

AUS = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/beobachte-leitung.txt"
DAUER = int(sys.argv[2]) if len(sys.argv) > 2 else 300
FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"


def sage(m):
    line = time.strftime("%H:%M:%S ") + m
    print(line, flush=True)
    with open(AUS, "a") as f:
        f.write(line + "\n")


def hole(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=40).stdout
    except Exception as e:
        return "FEHLER %s" % e


sage("=== Leitung beobachten, %ds ===" % DAUER)
t0 = time.time()
waehrend = []
while time.time() - t0 < DAUER:
    fb = hole([FB, "devices"]).count("fastboot")
    netz = hole(["ifconfig", "-a"])
    en8 = re.search(r"^en8:.*?(?=^\S+:)", netz, re.S | re.M)
    en8 = en8.group(0) if en8 else ""
    status = "kein-en8"
    if "status: active" in en8:
        status = "aktiv"
    elif "status: inactive" in en8:
        status = "inaktiv"
    ip = re.findall(r"inet (\S+)", en8)
    baum = hole(["ioreg", "-p", "IOUSB", "-l", "-w", "0"])
    prod = re.findall(r'"USB Product ID"\s*=\s*"?([^"\n]+)', baum)
    schnitt = [s.strip() for s in re.findall(r'"speed"\s*=\s*"?(\d+)', baum)]
    offen = "-"
    try:
        s = socket.create_connection(("172.16.42.1", 23), timeout=2)
        s.close()
        offen = "offen"
    except OSError:
        pass
    zeile = "fb=%d en8=%s ip=%s  ProductID=%s  speed=%s  telnet23=%s" % (
        fb, status, ",".join(ip) or "keine", ",".join(prod) or "keine",
        ",".join(schnitt) or "keine", offen)
    if not waehrend or waehrend[-1][1] != zeile:
        sage(zeile)
        waehrend.append((t0, zeile))
    time.sleep(6)
sage("=== Beobachtung fertig: %d wechselnde Zustande ===" % len(waehrend))
