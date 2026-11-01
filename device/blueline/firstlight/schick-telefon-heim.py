#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schickt das Telefon heim in den Fastboot-Bildschirm: restart2 ueber die offene Leitung.

Der Haltekreis von v0af wartet auf eine Verbindung. Busyboxes telnetd haelt das
Pseudo-TTY aber auch, nachdem der Cliente gegangen ist — ohne dieses Skript
bleibt das Telefon bis zur Obergrenze (60 min) stehen, wo eine Minute reicht.
restart2 ist der belegte Selbst-Rueckweg (0xa1b2c3d4, Grund 'bootloader'): kein
Knopf, kein Kabel, kein Write.

Aufruf:  python3 schick-telefon-heim.py
"""
import socket
import subprocess
import sys
import time

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
SERIAL = "PIXEL3-SERIAL"


def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


def fb_sichtbar():
    try:
        p = subprocess.run([FB, "devices"], capture_output=True, text=True, timeout=8)
    except subprocess.TimeoutExpired:
        return False
    return "fastboot" in (p.stdout or "") + (p.stderr or "")


if fb_sichtbar():
    notiz("Telefon sitzt schon im Fastboot — nichts zu schicken")
    sys.exit(0)
s = socket.create_connection(("172.16.42.1", 23), timeout=10)
s.settimeout(6)
try:
    time.sleep(1.0)
    try:
        notiz("Annahme: " + repr(s.recv(200).decode("utf-8", "replace")[-60:]))
    except socket.timeout:
        pass
    s.sendall(b"/usr/bin/restart2 bootloader\r\n")
    notiz("restart2 bootloader gesendet")
    ende = time.time() + 12
    while time.time() < ende:
        try:
            d = s.recv(200)
        except socket.timeout:
            continue
        except OSError:
            break
        if not d:
            notiz("Leitung zu — das Telefon geht")
            break
except OSError as e:
    notiz("Leitungannahme fehlgeschlagen: %s" % e)
    sys.exit(2)
finally:
    try:
        s.close()
    except OSError:
        pass

t0 = time.time()
while time.time() - t0 < 180 and not fb_sichtbar():
    time.sleep(5)
notiz("Fastboot %s nach %ds" % ("sichtbar" if fb_sichtbar() else "NICHT sichtbar",
                                int(time.time() - t0)))
sys.exit(0 if fb_sichtbar() else 3)
