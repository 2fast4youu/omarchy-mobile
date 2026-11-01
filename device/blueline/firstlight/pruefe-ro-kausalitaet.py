#!/usr/bin/env python3
"""Kausalttest: blockiert das whole-disk ro unser logflush?

Unsere Init ruft storage_guard auf und setzt jede Platte UND jede Partition
auf read-only (Zeile ~486 des Init). logflush dreht mit `blockdev --setrw` nur
die Partition zurueck, schreibt, und versteckt den Fehler von dd hinter
2>/dev/null. Die Referenz hat keinen Guard — deshalb gelang ihr Schreibtest
von 18:07, obwohl genau dieselbe Stelle in unserem Bild nie beschrieben wurde.

Probe am echten Geraet, vier Schritte, jede Ausgabe sichtbar:
  1. Ist-Zustand der ro-Schalter von /dev/sda und /dev/sda11.
  2. Platte ro, Partition rw (genau unser Zustand nach storage_guard+setrw).
  3. dd-Versuch, Fehlertext sichtbar.
  4. Platte rw, dd-Versuch, Rueckleseprobe.
Danach wird der Ausgangszustand wiederhergestellt.
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/ro-kausalitaet.txt"
BEFEHLE = [
    "echo anfang sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)",
    "blockdev --setro /dev/sda; blockdev --setrw /dev/sda11; echo gesetzt sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)",
    "printf 'OMAMOBILE-RO-BLOCK-1101\\n' > /tmp/p; dd if=/tmp/p of=/dev/sda11 bs=131072 seek=504 conv=notrunc,fsync; echo dd_rc=$?",
    "dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3",
    "blockdev --setrw /dev/sda; echo platte_rw=$(blockdev --getro /dev/sda); dd if=/tmp/p of=/dev/sda11 bs=131072 seek=504 conv=notrunc,fsync; echo dd_rc=$?",
    "dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3",
    "blockdev --setro /dev/sda; blockdev --setro /dev/sda11; echo Ende sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)",
]


def log(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)
    with open(EV, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")


try:
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
except OSError as e:
    log("Telnet zu: %s" % e); sys.exit(1)
s.settimeout(6.0)
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
