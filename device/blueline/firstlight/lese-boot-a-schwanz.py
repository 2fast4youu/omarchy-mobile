#!/usr/bin/env python3
"""Holt das OMAMOBILE-LOG vom Schwanz von boot_a (63 MiB) ueber die Referenz.

Weg, gemessen: 'fastboot fetch' kann das Geraet nicht. Die Referenz auf
ref/boot.img ist der einzige Kanal, der ein Gadget zeigt; von ihrem Telnet
aus ist boot_a eine lesbare Blockdatei. Der Referenz-Kern laeuft nur aus dem
RAM, boot_a wird ausschliesslich gelesen (dd ohne conv=notrunc, kein Write).

Kein Fall bleibt unbemerkt: kein Fastboot, RAM-Boot ohne Telnet, kein
by-partlabel-Knoten, kein Marker im Bereich. Jeder Ausgang steht im Protokoll.
"""
import datetime, re, socket, subprocess, sys, time

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
REF = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/boot-a-schwanz.txt"


def log(m):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + m
    print(line, flush=True)
    with open(EV, "a") as f:
        f.write(line + "\n")


def fb(args, timeout=60):
    return subprocess.run([FB] + args, capture_output=True, text=True, timeout=timeout)


def port_open(port=23):
    s = socket.socket(); s.settimeout(1.5)
    try:
        s.connect(("172.16.42.1", port)); return True
    except OSError:
        return False
    finally:
        s.close()


def telnet(cmds):
    """Eine Sitzung, jede Ausgabe einzeln ausgeworfen. Heredocs: nicht hier."""
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
    s.settimeout(3.0)
    try:
        s.sendall(b"\r\n"); s.recv(4096)
    except OSError:
        pass
    for c in cmds:
        s.sendall(c.encode() + b"\r\n")
        ende = time.time() + 40
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
            if stuck.count("\n") > 400:
                break
        log("### %s" % c)
        log(stuck.strip() or "(keine Ausgabe)")
    s.close()


log("=== boot_a-Schwanz: Referenz aus dem RAM, dann dd ===")
r = fb(["getvar", "current-slot"], timeout=8)
if r.returncode != 0:
    log("kein Fastboot — nichts gelesen. Naechster Schritt: Tastenaktion.")
    sys.exit(1)
log("Fastboot: " + (r.stdout + r.stderr).splitlines()[0])
# Slot b vor jedem Versuch auffuellen (Anweisung im Check-in, und die beiden
# belegten Gadget-Sichtungen der Referenz — 15:06 und 15:35 — liefen mit
# current-slot=b, wo dtbo_b voll ist). RAM-Boot schreibt nichts an Partitionen,
# --set-active aendert nur die Bootloader-Metadaten.
for v in ["slot-retry-count:b", "slot-unbootable:b"]:
    g = fb(["getvar", v], timeout=8)
    log("vorher: " + (g.stdout + g.stderr).splitlines()[0])
a = fb(["--set-active=b"], timeout=30)
log("set-active=b: " + (a.stdout + a.stderr).replace("\n", " ").strip()[-60:])
for v in ["current-slot", "slot-retry-count:b", "slot-unbootable:b"]:
    g = fb(["getvar", v], timeout=8)
    log("nachher: " + (g.stdout + g.stderr).splitlines()[0])
r = fb(["boot", REF], timeout=180)
log("fastboot boot ref: " + (r.stdout + r.stderr).replace("\n", " ")[-60:])
t0 = time.time()
while time.time() - t0 < 200 and not port_open():
    time.sleep(4)
if not port_open():
    log("Telnet in 200 s nicht offen — Referenz erreicht, Lesung entfaellt")
    sys.exit(1)
log("Telnet offen bei t=%.0fs" % (time.time() - t0))
telnet([
    "echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_geraet=${A:-KEINER}",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\0' | grep -c 'OMAMOBILE-LOG'",
    "A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head -150",
])
log("=== Lesung fertig ===")
