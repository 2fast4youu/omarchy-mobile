#!/usr/bin/env python3
"""Liest den boot_a-Schwanz ueber die schon laufende Referenz, ohne Neu-Start.

Die Referenz oeffnet ihr Telnet unregelmaessig (gemessen 78 s und 72 s offen,
17:25/17:31/18:22 nach 200 s zu). Dieses Skript startete keinen Neu-Boot,
sondern wartet bis zu `warteschritte` Anlaeufe auf die bestehende Sitzung und
liest, sobald sie antwortet. Die Netzsicht (ifconfig nach 172.16.42) steht
mit im Protokoll, weil die macreitseitige NCM-Schnittstelle erst mit ihrem
Adressangebot entsteht — eine Adresse, die spaet kommt, ist kein totes Bild.
"""
import re, socket, subprocess, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/boot-a-schwanz-direkt.txt"
FRIST = int(sys.argv[2]) if len(sys.argv) > 2 else 600


def log(m):
    print(datetime_str() + m, flush=True)
    with open(EV, "a") as f:
        f.write(datetime_str() + m + "\n")


def datetime_str():
    return time.strftime("%H:%M:%S ")


def netz():
    r = subprocess.run(["ifconfig", "-a"], capture_output=True, text=True)
    return len(re.findall(r"172\.16\.42\.\d", r.stdout))


def telnet(befehle):
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
    s.settimeout(3.0)
    try:
        s.sendall(b"\r\n")
        s.recv(4096)
    except OSError:
        pass
    for c in befehle:
        s.sendall(c.encode() + b"\r\n")
        ende = time.time() + 60
        stuck = ""
        while time.time() < ende:
            try:
                d = s.recv(65536)
            except (socket.timeout, OSError):
                break
            if not d:
                break
            stuck += d.decode("utf-8", "replace")
            if stuck.count("\n") > 400:
                break
        log("### " + c)
        log(stuck.strip() or "(keine Ausgabe)")
    s.close()


SUCH = [
    "echo up=$(cut -d. -f1 /proc/uptime)s",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); echo geraet=${A:-KEINER}",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | grep -ac OMAMOBILE",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\000' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head -140",
]
log("=== direkte Lesung, ohne Neu-Boot (Netz: %d Adressen) ===" % netz())
t0 = time.time()
offen = False
while time.time() - t0 < FRIST:
    try:
        probe = socket.create_connection(("172.16.42.1", 23), timeout=3)
        probe.close()
        offen = True
        break
    except OSError:
        time.sleep(10)
log("Telnet: %s nach %.0fs, Netz %d Adressen" % ("offen" if offen else "zu", time.time() - t0, netz()))
if not offen:
    log("Referenz antwortet nicht — naechster Schritt: Referenz neu aus dem RAM")
    sys.exit(1)
telnet(SUCH)
log("=== Lesung fertig ===")
