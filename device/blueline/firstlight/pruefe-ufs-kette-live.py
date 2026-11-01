#!/usr/bin/env python3
"""Holt an der laufenden Referenz die Treiberkette, die die UFS-Platte erzeugt.

Unsere Bilder enthalten sechs Module, alle USB-Gadget, und keinen
Plattentreiber. Die Referenz zeigt sda..sdf — also muss sie die UFS-Kette
laden. Gesucht: Name, Reihenfolge, Abhaengigkeiten, und wo die .ko-Dateien auf
ihrem Dateisystem liegen, damit wir sie ins eigene Ramdisk legen koennen.
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/ufs-kette-live.txt"
BEFEHLE = [
    "grep -E 'ufs|scsi|sd_mod|ice|qcom' /proc/modules",
    "ls /sys/block/",
    "for f in /proc/modules; do echo moduli=$(wc -l <$f); done",
    "ls -l /sys/block/sda/device 2>/dev/null | head -3; readlink -f /sys/block/sda/device/of_node 2>/dev/null",
    "echo --- ko-pfade ---; for d in /os /root /new_root /mnt; do [ -d \"$d/usr/lib/modules\" ] && echo Fundort=$d; done; ls /usr/lib/modules/*/kernel/drivers/ufs 2>/dev/null | head",
    "find / -xdev -name '*ufs*.ko' 2>/dev/null | head -12",
    "find / -xdev -name 'scsi_*.ko' -o -xdev -name 'sd_mod.ko' 2>/dev/null | head -6",
]


def log(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)
    with open(EV, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")


try:
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
except OSError as e:
    log("Telnet zu: %s" % e); sys.exit(1)
s.settimeout(5.0)
try:
    s.sendall(b"\r\n"); s.recv(4096)
except OSError:
    pass
for b in BEFEHLE:
    s.sendall(b.encode() + b"\r\n")
    ende, out = time.time() + 90, ""
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
