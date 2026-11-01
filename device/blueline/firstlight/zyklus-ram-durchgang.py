#!/usr/bin/env python3
"""RAM-Boot + Protokoll, bis das Bild sich selbst zurueckbringt.

Aufruf: zyklus-ram-durchgang.py <evidence-pfad> [bildpfad]
Das Bild ist mitgebbbar, weil der Durchgang die Messung ist, nicht das Bild:
  python3 zyklus-ram-durchgang.py evidence/v0ab-ram-2026-11-01.log \
      /Users/gregor/hermes-workspace/images/fl-v0ab/firstlight.img

Was gemessen wird: der Augenblick, in dem das Gadget am Mac erscheint
(USB-Produkt-Nummer am ioreg-Baum), und der Augenblick, in dem das Bild
per reboot(2) RESTART2 'bootloader' von selbst in Fastboot zurueckkommt.
Beides erscheint im Protokoll, keiner der zwei Faelle wird uebergangen:
  * Selbst-Rueckweg: Produkt 0x4EE0 nach einer Phase mit Gadget oder Telnet.
  * Ausbleibende Enumeration: nach dem Fenster Tastenaktion (von Hand).
"""
import datetime, re, socket, subprocess, sys, time

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
IMG = sys.argv[2] if len(sys.argv) > 2 else "/Users/gregor/hermes-workspace/images/fl-v0ab/firstlight.img"
EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/v0aa-ram.log"


def log(m):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + m
    print(line, flush=True)
    with open(EV, "a") as f:
        f.write(line + "\n")


def usb_state():
    out = subprocess.run(["ioreg", "-p", "IOUSB", "-l", "-w0"],
                         capture_output=True, text=True, timeout=10).stdout
    hits = set()
    for b in out.split("+-o ")[1:]:
        if '"USB Vendor Name" = "Google"' in b:
            m = re.search(r'"idProduct"\s*=\s*(\d+)', b)
            if m:
                hits.add("0x%04X" % int(m.group(1)))
    return ",".join(sorted(hits)) or "kein-Geraet"


def port_open(port):
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect(("172.16.42.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def fb_ready():
    try:
        return subprocess.run([FB, "getvar", "current-slot"],
                              capture_output=True, text=True, timeout=6).returncode == 0
    except subprocess.TimeoutExpired:
        return False


log("=== RAM-Zyklus beginnt: %s (boot_b + dtbo_b bleiben die Referenz) ===" % IMG)
if not fb_ready():
    log("kein Fastboot — Abbruch, nichts gerampt")
    sys.exit(1)
r = subprocess.run([FB, "boot", IMG], capture_output=True, text=True, timeout=180)
log("fastboot boot: " + (r.stdout + r.stderr).replace("\n", " ")[-70:])
t0 = time.time()
zuletzt = ""
while time.time() - t0 < 420:
    t = time.time() - t0
    g = usb_state()
    tn = port_open(23)
    if g != zuletzt or tn:
        log("t=%3.0fs usb=%s telnet23=%s" % (t, g, "offen" if tn else "zu"))
        zuletzt = g
    if g == "0x4EE0" and t > 60:
        log("TREFFER: Selbst-Rueckweg — Fastboot bei t=%.0fs ohne Tastenaktion" % t)
        break
    time.sleep(5)
else:
    log("420s ohne Selbst-Rueckweg; letzter Zustand oben")
log("Fastboot-Abruf: %s | letzte USB-Sicht: %s" % (fb_ready(), usb_state()))
