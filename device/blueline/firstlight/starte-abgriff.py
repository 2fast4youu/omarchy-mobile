#!/usr/bin/env python3
"""Startet den Kalibrier-Abgriff in einem Durchgang: Fastboot, RAM-Start, Leser.

Warum ein eigenes Startskript: die Shell-Tanzerei mit `fastboot devices` in einer
for-Schleife und nacktem `getvar` blieb schon stehen — fastboot blockiert, wenn
kein Geraet da ist, und ein leer zurückkommendes getvar laesst den Slot-Schutz
still durchfallen. Hier hat jeder Fastboot-Griff eine eigene Frist, und der
Slot-Schutz bricht ab, statt zu raten, wenn er die Antwort nicht lesen kann.

Aufruf:  python3 starte-abgriff.py [bild] [ziel]
"""
import os
import socket
import subprocess
import sys
import time

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
BILD = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/hermes-workspace/images/fl-v0af/firstlight.img"
ZIEL = sys.argv[2] if len(sys.argv) > 2 else "evidence/kalibrier"
HIER = os.path.dirname(os.path.abspath(__file__))


def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


def fb(*args, frist=15):
    try:
        p = subprocess.run([FB] + list(args), capture_output=True, text=True, timeout=frist)
        return ((p.stdout or "") + (p.stderr or "")).replace("\r", "")
    except subprocess.TimeoutExpired:
        return "FESTGEFAHREN nach %ds" % frist


def sichtbar():
    for _ in range(3):
        if "fastboot" in fb("devices", frist=6):
            return True
        time.sleep(2)
    return False


def offen():
    try:
        s = socket.create_connection(("172.16.42.1", 23), timeout=4)
        s.close()
        return True
    except OSError:
        return False


if not offen():
    t0 = time.time()
    while not sichtbar() and time.time() - t0 < 240:
        time.sleep(3)
    if not sichtbar():
        notiz("kein Fastboot-Geraet in 240s — nichts gerampt")
    if sichtbar():
        stand = fb("getvar", "current-slot", frist=10)
        notiz("Slot-Antwort: " + (stand.strip().splitlines()[-1] if stand.strip() else "leer"))
        if "current-slot: b" in stand:
            notiz("Slot b aktiv — zurueck auf a setzen (Wurzel #11)")
            notiz(fb("--set-active=a", frist=20).strip().splitlines()[-1])
        elif "current-slot:" not in stand:
            notiz("Slot nicht gelesen — setzen erzwungen, damit der Zaehler nicht leer bleibt")
            fb("--set-active=a", frist=20)
        notiz("starte aus dem RAM: " + fb("boot", BILD, frist=120).strip().splitlines()[-1])
    t0 = time.time()
    while time.time() - t0 < 180 and not offen():
        time.sleep(2)
notiz("Port 23 offen" if offen() else "Port 23 bleibt zu")

r = subprocess.run([sys.executable, "-u", os.path.join(HIER, "greife-kalibrier.py"), ZIEL, "120"],
                   cwd=HIER)
notiz("Abgriff-Exit %d" % r.returncode)
sys.exit(r.returncode)
