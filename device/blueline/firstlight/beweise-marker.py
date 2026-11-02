#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Liest die Marker-Messung: legt ABOOT sein GPT in userdata wirklich selbst hin?

Behauptung (aus v0ag, 17:0x): auf userdata stehe bei 4096 'EFI PART' statt der
Gruppenbeschreiber, die unser Bild dort hin schreibt. Belegt ist nur der Fund.
Zwei Erklaerungen sind moeglich, und die eine sagt, dass der 1-MiB-Vorlauf noetig
ist, die andere, dass er ueberfluessig ist:

  a) ABOOT legt seinen Partitionssatz bei jedem Start dorthin zurueck.
  b) Der erste Write (17:01, fastboots eigene Sparse-Umrechnung, die 4096 und 8192
     als Locher liess) hat den alten Satz einfach stehen lassen.

Gemessen wird mit einem eigenen Muster: images/userdata-alpine/marker-4mib.bin
traegt MK0000-, MK4096- und MK8192-Zeilen, der Rest Null (sha256 39cb098d...,
4 194 304 B, als Sparse mit einem Block = 4 MiB). Nach dem Write wird vor dem
Neustart gelesen (Zustand 'sofort') und nach einem Neustart noch einmal
(Zustand 'nach-boot'). Bleibt das Muster, ist b) richtig und der Vorlauf fortan
ueberfluessig. Verschwindet es genau bei 4096 und 8192, ist a) belegt.

Aufruf:  beweise-marker.py [zustand] [zielordner]
"""
import importlib.util
import os
import socket
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gk", os.path.join(HIER, "greife-kalibrier.py"))
gk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gk)

ZUSTAND = sys.argv[1] if len(sys.argv) > 1 else "sofort"
ZIEL = (sys.argv[2] if len(sys.argv) > 2
        else os.path.join(HIER, "evidence", "marker-" + ZUSTAND))
BEWEISE = [
    ("zeit.txt", "cat /proc/uptime"),
    ("geruest.txt", "D=/sys/block/sda; S=16547840"),
    ("UD-finden.txt", "for p in $D/sda*; do [ $(cat $p/start) = $S ] && UD=/dev/${p##*/}; done"),
    ("UD.txt", "echo UD=$UD; cat $UD/size 2>/dev/null; blockdev --getro $UD 2>/dev/null"),
    ("feld-0-sofort.txt", "dd if=$UD bs=1 skip=0 count=48 2>/dev/null | hexdump -C | head -3"),
    ("feld-4096.txt", "dd if=$UD bs=1 skip=4096 count=48 2>/dev/null | hexdump -C | head -3"),
    ("feld-8192.txt", "dd if=$UD bs=1 skip=8192 count=48 2>/dev/null | hexdump -C | head -3"),
    ("feld-1mib.txt", "dd if=$UD bs=1 skip=1048576 count=48 2>/dev/null | hexdump -C | head -3"),
    ("feld-65536.txt", "dd if=$UD bs=1 skip=65536 count=48 2>/dev/null | hexdump -C | head -3"),
    ("satz-4096-lesbar.txt", "dd if=$UD bs=1 skip=4096 count=32 2>/dev/null | tr -dc '0-9A-Za-z-'"),
    ("satz-8192-lesbar.txt", "dd if=$UD bs=1 skip=8192 count=32 2>/dev/null | tr -dc '0-9A-Za-z-'"),
    ("gpt-pruefung.txt", "dd if=$UD bs=1 skip=4096 count=8 2>/dev/null | hexdump -C"),
    ("dmesg-ende.txt", "dmesg | tail -4 | tr '\\n' ';' | cut -c1-70"),
]


def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


os.makedirs(ZIEL, exist_ok=True)
s = socket.create_connection(("172.16.42.1", 23), timeout=8)
s.settimeout(25)
gk.wecke_shell(s)
notiz("Leitung offen, Shell geweckt — Zustand %s" % ZUSTAND)
gesamt = 0
for name, befehl in BEWEISE:
    text = gk.abfrage(s, befehl, name.replace(".", "-"))
    if text is None:
        notiz("  %-22s KEINE Antwort im Rahmen" % name)
        continue
    with open(os.path.join(ZIEL, name), "w", encoding="utf-8") as datei:
        datei.write(text if text.endswith("\n") else text + "\n")
    gesamt += len(text)
    erste = text.strip().splitlines()[0][:58] if text.strip() else ""
    notiz("  %-22s %5d B  %s" % (name, len(text), erste))
s.close()
leer = [n for n, _ in BEWEISE
        if not os.path.exists(os.path.join(ZIEL, n))
        or os.path.getsize(os.path.join(ZIEL, n)) == 0]
notiz("Zustand %s: %d Beweise, %d Bytes, %d leer: %s"
      % (ZUSTAND, len(BEWEISE), gesamt, len(leer), ", ".join(leer) or "keine"))
sys.exit(1 if leer else 0)
