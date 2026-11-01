#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holt die Gerate-Beweise aus dem laufenden System — mit dem bewaehrten Rahmenleser.

greife-beweise.py redet noch die alte Sprache (echo-Markierungen) und laeuft seit
der Cursor-Auskunft (Wurzel #13) ins Leere: 18 Dateien, 0 Bytes. Statt das umzu-
bauen, holt dieses Skript die selben Beweise durch `abfrage()` aus
greife-kalibrier.py — den Leser, der die LUN-Karte mit 24 550 B sauber ueber die
Leitung gebracht hat: Rahmen als printf, Antwortzeilen mit @@, Echo-tolerant.

Aufruf:  python3 abgreife-flash-system.py [zielordner]
"""
import os
import socket
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import importlib.util

spec = importlib.util.spec_from_file_location("gk", os.path.join(HIER, "greife-kalibrier.py"))
gk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gk)

ZIEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HIER, "evidence", "aus-flash")
BEWEISE = [
    ("uname.txt", "uname -a"),
    ("cmdline.txt", "cat /proc/cmdline"),
    ("uptime.txt", "cat /proc/uptime"),
    ("boot-slot.txt", "cat /proc/cmdline | tr ' ' '\\n' | grep androidboot.slot"),
    ("lsmod.txt", "lsmod"),
    ("module.txt", "cat /proc/modules"),
    ("udc-liste.txt", "ls /sys/class/udc"),
    ("udc-state.txt", "for u in /sys/class/udc/*; do echo $u $(cat $u/state); done"),
    ("gadget-baum.txt", "ls -l /sys/kernel/config/usb_gadget/ 2>/dev/null"),
    ("netz.txt", "ip -o addr 2>/dev/null || ifconfig -a"),
    ("dtb-modell.txt", "cat /proc/device-tree/model /proc/device-tree/compatible 2>/dev/null | tr '\\0' ' '"),
    ("speicher-ro.txt", "for d in /sys/block/sd*; do echo $d ro=$(cat $d/ro); done"),
    ("init-schritte.txt", "cat /run/steps.log 2>/dev/null | tail -40"),
    ("kernel-config.txt", "zcat /proc/config.gz 2>/dev/null | head -400"),
    ("dmesg.txt", "dmesg | tail -300"),
]


def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


os.makedirs(ZIEL, exist_ok=True)
s = socket.create_connection(("172.16.42.1", 23), timeout=8)
s.settimeout(20)
gk.wecke_shell(s)
notiz("Leitung offen, Shell geweckt")
gesamt = 0
for name, befehl in BEWEISE:
    text = gk.abfrage(s, befehl, name.replace(".", "-"))
    if text is None:
        notiz("  %-22s KEINE Antwort im Rahmen" % name)
        continue
    text = text.strip("\r\n") + "\n"
    with open(os.path.join(ZIEL, name), "w", encoding="utf-8", errors="replace") as f:
        f.write(text)
    gesamt += len(text)
    notiz("  %-22s %d B" % (name, len(text)))
try:
    s.close()
except OSError:
    pass
notiz("=== fertig: %d Bytes in %s ===" % (gesamt, ZIEL))
sys.exit(0 if gesamt > 0 else 4)
