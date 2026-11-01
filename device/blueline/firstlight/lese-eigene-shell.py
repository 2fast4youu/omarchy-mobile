#!/usr/bin/env python3
"""Liest die Shell des EIGENEN Bildes, waehrend es laeuft.

Erster Anlass: der v0ae-Durchgang meldete um 20:11:25 (t=355s)
`telnet23=offen` auf 172.16.42.1 — das war nicht die Referenz, sondern unser
eigenes Bild mit gebundenem Gadget. Damit ist zum ersten Mal waehrend eines
eigenen Laufs lesbar, was der Kernel und die Init tun.

Reihenfolge: auf Port 23 warten (das Bild haelt die Verbindung, bis es sich per
restart2 selbst zurueckholt), dann pro Befehl eine Zeile lesen und mit
Zeitstempel und Kernel-Uptime ins Protokoll. Kein Befehl longer als ~60
Zeichen, weil die Shell bei ~80 Spalten umbricht und ein gerissener Befehl als
zwei Zeilen ankommt.
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/eigene-shell.txt"
FRIST = int(sys.argv[2]) if len(sys.argv) > 2 else 300
BEFEHLE = [
    "echo up=$(cut -d. -f1 /proc/uptime)s",
    "uname -a",
    "echo moduli=$(wc -l < /proc/modules)",
    "grep -c libcomposite /proc/modules",
    "ls /sys/class/udc",
    "cat /sys/class/udc/*/state 2>/dev/null",
    "ls /sys/kernel/config/usb_gadget",
    "cat /sys/kernel/config/usb_gadget/g1/UDC",
    "ls /sys/kernel/config/usb_gadget/g1/functions",
    "ls /sys/kernel/config/usb_gadget/g1/strings/0x1",
    "ip -o addr show 2>/dev/null | head -6",
    "echo module_da: $(ls /usr/lib/modules/*/kernel/drivers/usb/gadget/*.ko 2>/dev/null | wc -l)",
    "tail -24 /run/steps.log",
    "cat /run/steps.log | grep -c nonexistent",
    "ls /sys/fs/pstore",
]


def log(m):
    line = time.strftime("%H:%M:%S ") + m
    print(line, flush=True)
    with open(EV, "a") as f:
        f.write(line + "\n")


t0 = time.time()
offen = False
while time.time() - t0 < FRIST:
    try:
        s = socket.create_connection(("172.16.42.1", 23), timeout=3)
        s.close()
        offen = True
        break
    except OSError:
        time.sleep(5)
if not offen:
    log("Telnet in %ds nicht offen — Netz: %d Adressen" % (
        FRIST, sum(1 for _ in __import__("subprocess").run(
            ["ifconfig", "-a"], capture_output=True, text=True).stdout.splitlines()
            if "172.16.42" in _.replace("\n", ""))))
    sys.exit(1)
log("eigene Shell offen nach %.0fs" % (time.time() - t0))

s = socket.create_connection(("172.16.42.1", 23), timeout=8)
s.settimeout(4.0)
try:
    s.sendall(b"\r\n"); s.recv(4096)
except OSError:
    pass
for b in BEFEHLE:
    s.sendall(b.encode() + b"\r\n")
    ende, out = time.time() + 45, ""
    while time.time() < ende:
        try:
            d = s.recv(65536)
        except (socket.timeout, OSError):
            break
        if not d:
            break
        out += d.decode("utf-8", "replace")
    log("### " + b)
    log(out.strip() or "(keine Ausgabe)")
s.close()
log("=== Lesung der eigenen Shell fertig ===")
