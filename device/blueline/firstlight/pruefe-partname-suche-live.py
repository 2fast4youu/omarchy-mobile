#!/usr/bin/env python3
"""Prueft an der laufenden Referenz, ob v0acs Partitionssuche ueberhaupt
funktionieren kann, und liest die Marker-Stelle mit od (ohne tr-Klassen).

Alles hier ist eine Messung am laufenden Kernel, keine Annahme:
  1. Zeigt /sys/block/*/uevent ueberhaupt PARTNAME? v0ac verlaesst sich darauf.
  2. Wenn ja: liefert dieselbe Stelle auch die Major:Minor fuer mknod?
  3. Was steht an 66060288 (hex), damit die tr-Ausgabe nicht getaeuscht hat?
  4. Ist der Kernel der Referenz ueberhaupt der, der die Partitionen benennt?
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/v0ac-suche-am-leib.txt"
BEFEHLE = [
    "grep -c PARTNAME /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null | grep -v ':0' | head -8",
    "echo PARTNAME-Zeilen in sda-Tree: $(grep -h PARTNAME /sys/block/sda*/uevent 2>/dev/null | wc -l)",
    "cat /sys/block/sda/uevent 2>/dev/null | head -5",
    "grep -l 'PARTNAME=boot_a' /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null",
    "for u in /sys/block/*/uevent /sys/block/*/*/uevent; do grep -qx 'PARTNAME=boot_a' $u && echo TREFFER=$u cat=$(cat $u/dev 2>/dev/null); done",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=1 skip=66060288 count=64 2>/dev/null | od -c | head -6",
    "readlink /sys/block/sda/device 2>/dev/null; ls /sys/block/",
]


def log(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)
    with open(EV, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")


try:
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
except OSError as e:
    log("Telnet zu: %s" % e); sys.exit(1)
s.settimeout(4.0)
try:
    s.sendall(b"\r\n"); s.recv(4096)
except OSError:
    pass
for b in BEFEHLE:
    s.sendall(b.encode() + b"\r\n")
    ende, out = time.time() + 60, ""
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
log("=== fertig ===")
