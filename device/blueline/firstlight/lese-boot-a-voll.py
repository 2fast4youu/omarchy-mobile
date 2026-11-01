#!/usr/bin/env python3
"""Wirft den ganzen boot_a-Schwanz raus und zerlegt ihn, ohne Bereichsfilter.

Grund: die vorige Lesung filterte mit sed auf OMAMOBILE-LOG..ENDOF-LOG und gab
nichts aus, obwohl ein Treffer da war — der Treffer war der eigene
Schreibtest. Ein Bereichsfilter auf ein Marker-Wort, das moeglicherweise gar
nicht geschrieben wurde, ist eine Behauptung, keine Messung. Diese Fassung
zaehlt jede Marker-Art und gibt den lesbaren Rest aus, ungefiltert.
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/boot-a-voll.txt"
BEFEHLE = [
    "echo up=$(cut -d. -f1 /proc/uptime)s kernel=$(uname -r)",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\000' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | uniq -c",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -cd '[:print:]\\n' | head -c 4000",
    "ls -l /dev/disk/by-partlabel/ 2>&1 | head -30",
]


def log(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)
    with open(EV, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")


s = socket.create_connection(("172.16.42.1", 23), timeout=8)
s.settimeout(4.0)
try:
    s.sendall(b"\r\n"); s.recv(4096)
except OSError:
    pass
for b in BEFEHLE:
    s.sendall(b.encode() + b"\r\n")
    ende = time.time() + 90
    out = ""
    while time.time() < ende:
        try:
            d = s.recv(65536)
        except (socket.timeout, OSError):
            break
        if not d:
            break
        out += d.decode("utf-8", "replace")
        if len(out) > 200000:
            break
    log("### " + b)
    log(out.strip() or "(keine Ausgabe)")
s.close()
log("=== fertig ===")
