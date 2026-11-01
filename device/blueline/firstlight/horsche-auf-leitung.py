#!/usr/bin/env python3
"""Horcht auf der Telnet-Leitung, was das Telefon tatsaechlich zurueckgibt.

Anlass (21:06): jeder Bereich meldete „keine Grunddaten", obwohl die Shell offen
war. Statt zu raten, wird ein Befehl nach dem anderen gesendet und der ROHTON
notiert — mit Zeitstempel und Bytezahl. Eine Parse-Regel, die man nicht am Ton
geprueft hat, ist eine Regel, die man sich ausdenkt.
"""
import socket
import sys
import time

VERSUCHE = [
    "echo @@AN${''}FANG rahmen-test",
    "echo groesse=$(wc -c < /dev/sda)",
    "dd if=/dev/sda bs=512 skip=0 count=64 of=/run/ab.bin 2>/dev/null; echo dd_rc=$? groe=$(wc -c < /run/ab.bin)",
    "gzip -9 -c /run/ab.bin > /run/ab.bin.gz 2>/dev/null; echo gz_rc=$? groe=$(wc -c < /run/ab.bin.gz)",
    "echo @@EN${''}DE rahmen-test",
    "which gzip sha256sum base64 dd awk",
    "ls /dev/disk 2>/dev/null | head -3; for u in /sys/block/sda/sda1/uevent /sys/block/sda/sda11/uevent; do grep -H . $u; done",
]

s = socket.create_connection(("172.16.42.1", 23), timeout=6)
s.settimeout(6.0)
s.sendall(b"\r\n")
time.sleep(0.6)
try:
    print("== Begrussung: %r" % s.recv(4096)[:200])
except socket.timeout:
    print("== Begrussung: nichts")

for b in VERSUCHE:
    s.sendall((b + "\r\n").encode())
    ende, ton = time.time() + 25, b""
    while time.time() < ende:
        try:
            d = s.recv(65536)
        except socket.timeout:
            continue
        if not d:
            break
        ton += d
        if b"\r\n~ # " in ton[-8:] or b"$ " in ton[-4:]:
            break
    print("---- %s  (%d B)" % (b[:70], len(ton)))
    print(ton.decode("utf-8", "replace").replace("\r\n", "\n")[:900])
s.close()
