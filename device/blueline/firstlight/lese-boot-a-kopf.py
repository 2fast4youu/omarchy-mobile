#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Beweis, dass boot_a wirklich das eigene Bild traegt: Kopf-Hash am Telefon.

Ein fastboot-Write meldet nur seine eigene Uebertragung. Geprüft wird deshalb am
Gerät: die ersten N Bytes von /dev/sda11 (boot_a) werden auf dem Telefon selbst
gehasht und mit dem lokalen Bild verglichen. ueber die Leitung kommt nur eine
einzige Zeile — kein Blocktransport, keine Prompt-Fallerei.

Aufruf:  python3 lese-boot-a-kopf.py [megabytes]
"""
import hashlib
import os
import re
import socket
import sys
import time

GERAET = "/dev/sda11"
BILD = "/Users/gregor/hermes-workspace/images/fl-v0af/firstlight.img"
MEBI = int(sys.argv[1]) if len(sys.argv) > 1 else 8



def wecke_shell(s, frist=6):
    """Die Cursor-Auskunft beantworten, sonst fuehrt die Shell nichts aus.

    Busybox-ash mit Zeilenbearbeitung schickt am Prompt 'ESC[6n' und wartet auf
    die Positions-Meldung. Ein Client, die nicht antwortet, sieht nur Echo: die
    Befehle gehen in die Warteschlange, als waere die Leitung kaputt. Um 00:20
    hat das einen ganzen Abgriff leer laufen lassen (18 Dateien, 0 Bytes).
    """
    ende, ton = time.time() + frist, b""
    while time.time() < ende:
        try:
            d = s.recv(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        if not d:
            break
        ton += d
        if b"\x1b[6n" in ton:
            s.sendall(b"\x1b[1;1R")
            try:
                ton += s.recv(4096)
            except (socket.timeout, OSError):
                pass
            break
        if b"#" in ton and b"\x1b[6n" not in ton:
            break
    return ton

def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


lokal = hashlib.sha256(open(BILD, "rb").read(MEBI * 1024 * 1024)).hexdigest()
notiz("lokaler Kopf (%d MiB von %s): %s" % (MEBI, os.path.basename(BILD), lokal[:16]))

s = socket.create_connection(("172.16.42.1", 23), timeout=10)
s.settimeout(20)
wecke_shell(s)
# Erst die Shell wecken: busybox telnetd gibt ein Pseudo-TTY aus, aber erst ein
# Zeilensprung bringt den Prompt. Ohne diesen Schritt frisst der Login den Befehl
# und die Leitung geht zu — um 00:20:07 genau so passiert.
weck = b""
wachen = time.time() + 25
while time.time() < wachen:
    s.sendall(b"\r\n")
    try:
        weck += s.recv(4096)
    except socket.timeout:
        continue
    if b"#" in weck:
        break
ton = b""
s.sendall(b"printf '@@%s\\n' $(dd if=%s bs=1M count=%d 2>/dev/null | sha256sum | cut -d' ' -f1)\r\n"
          % (b"KOPF", GERAET.encode(), MEBI))
ende = time.time() + 180
while time.time() < ende:
    try:
        d = s.recv(4096)
    except socket.timeout:
        continue
    if not d:
        break
    ton += d
    if b"@@KOPF" in ton:
        break
s.close()
text = ton.decode("utf-8", "replace")
m = [z for z in text.splitlines() if z.startswith("@@KOPF")]
if not m:
    notiz("keine Antwortzeile — Rohton-Anfang: " + repr(text[:120]))
    sys.exit(2)
wert = re.search(r"@@KOPF\s+([0-9a-f]{64})", m[-1])
if not wert:
    notiz("Antwort unlesbar: " + m[-1][:90])
    sys.exit(2)
notiz("Telefon meldet boot_a-Kopf: " + wert.group(1)[:16])
notiz("bytegleich zum Bild: %s" % (wert.group(1) == lokal))
sys.exit(0 if wert.group(1) == lokal else 4)
