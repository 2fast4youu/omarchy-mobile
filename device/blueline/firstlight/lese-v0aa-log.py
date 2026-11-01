#!/usr/bin/env python3
"""Liest das OMAMOBILE-LOG, das v0aa an seinen eigenen Bildschwanz schrieb.

Weg, gemessen: 'fastboot fetch' kann das Geraet nicht. Die Referenz auf
boot_b hat Telnet, und von dort ist boot_a eine blockdatei. Der Lesebereich
ist der letzte MiB (logflush schreibt seek=504 * 128 KiB), also wird dort
nach den Markern gesucht. Die Zeichenkette 'OMAMOBILE-LOG' traegt keine
Shell-Zeichen, die eine Heredoc-Expansion angreifen koennten; der Heredoc
ist trotzdem quotiert (Regel vom 2026-11-01: unquotiert zerstoert $/@ den
Base64-Koerper).
"""
import socket, subprocess, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/v0aa-logauszug.txt"
BEFEHLE = [
    "ls -l /dev/disk/by-partlabel/ 2>/dev/null | head -20",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_geraet=$D",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\0' | grep -a -A200 'OMAMOBILE-LOG' | head -120",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\0' | grep -c 'OMAMOBILE-LOG'",
    "uname -a; cat /proc/uptime",
]


def log(m):
    print(m, flush=True)
    with open(EV, "a") as f:
        f.write(m + "\n")


def telnet(cmds, warteschritt=1.2):
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
    s.settimeout(warteschritt)
    try:
        s.sendall(b"\r\n")
        s.recv(4096)
    except OSError:
        pass
    ausgabe = []
    for c in cmds:
        s.sendall(c.encode() + b"\r\n")
        ende = time.time() + 25
        stuck = ""
        while time.time() < ende:
            try:
                d = s.recv(65536)
            except socket.timeout:
                break
            except OSError:
                break
            if not d:
                break
            stuck += d.decode("utf-8", "replace")
        ausgabe.append("### %s\n%s" % (c, stuck.strip()))
    s.close()
    return "\n".join(ausgabe)


log("=== v0aa-Lesung: boot_a-Schwanz ueber die laufende Referenz ===")
try:
    out = telnet(BEFEHLE)
    log(out)
    log("=== Lesung fertig ===")
except OSError as e:
    log("Telnet nicht erreichbar: %s" % e)
    sys.exit(1)
