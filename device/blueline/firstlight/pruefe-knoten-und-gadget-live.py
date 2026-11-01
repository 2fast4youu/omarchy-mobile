#!/usr/bin/env python3
"""Sucht am laufenden Kernel den wirklichen Weg zu Major:Minor und zum Gadget.

Anlass (19:35, gemessen): /sys/block/sda/sda11/uevent traegt PARTNAME=boot_a,
aber die daneben erwartete Datei `dev` ist leer — v0acs mknod-Quelle fehlt.
Ohne Major:Minor kein Knoten, ohne Knoten kein dd, ohne dd kein Log. Also:
wo steht die Nummer wirklich, und wie sieht die Gadget-Seite aus?
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/knoten-und-gadget-live.txt"
BEFEHLE = [
    "ls -l /sys/class/block/sda11/ 2>&1 | head -20",
    "echo class-dev=$(cat /sys/class/block/sda11/dev 2>/dev/null) block-dev=$(cat /sys/block/sda/sda11/dev 2>/dev/null) stat=$(stat -c '%t %T' /dev/sda11 2>/dev/null)",
    "for p in sda11 sde11; do echo $p uevent:; cat /sys/block/sda/$p/uevent 2>/dev/null || cat /sys/block/sde/$p/uevent 2>/dev/null; done | head -20",
    "echo ueventd=$(ls /sys/class/uevent 2>/dev/null | head -2) mdev=$(which mdev) ueventd_p=$(which ueventd) hotplug=$(cat /proc/sys/kernel/hotplug 2>/dev/null)",
    "echo init=$(cat /proc/1/cmdline | tr '\\0' ' ') pid1=$(readlink /proc/1/exe)",
    "echo --- GADGET ---; ls /sys/kernel/config 2>&1 | head -3; mount | grep -E 'config|debugfs' ; ls /sys/kernel/config/usb_gadget 2>&1 | head -5; ls /sys/class/udc 2>&1",
    "echo --- libcomposite ---; grep -c libcomposite /proc/modules; lsmod 2>/dev/null | grep -E 'libcomposite|udc|ncm|mass_storage|g_ether' | head -8",
    "cat /sys/kernel/debug/devices_deferred 2>&1 | head -8",
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
