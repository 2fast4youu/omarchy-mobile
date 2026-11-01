#!/usr/bin/env python3
# Zyklus mit USB-Mautprotokoll: pollt alle 2 s die ioreg-Product-ID des Pixel,
# dazu Telnet/ACM. Bootet die Referenz per fastboot boot (RAM, kein Flash).
import re, socket, subprocess, time, datetime

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
IMG = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
LOG = "/Users/gregor/.hermes/cache/scratch/maut-" + datetime.datetime.now().strftime("%H%M%S") + ".log"

def log(msg):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def fastboot(args, t=15):
    try:
        r = subprocess.run([FB] + args, capture_output=True, text=True, timeout=t)
        return (r.returncode, (r.stdout + r.stderr).strip())
    except subprocess.TimeoutExpired:
        return (124, "TIMEOUT")

def pixel_present():
    # billig: ioreg -n ohne -l, nur Baumknoten
    try:
        out = subprocess.run(["ioreg", "-p", "IOUSB", "-n", "Pixel 3"],
                             capture_output=True, text=True, timeout=6).stdout
    except subprocess.TimeoutExpired:
        return "ioreg-TIMEOUT"
    return "Pixel da" if "Pixel 3" in out else "kein Pixel"

def telnet_up():
    s = socket.socket(); s.settimeout(1.5)
    try:
        s.connect(("172.16.42.1", 23)); return True
    except OSError:
        return False
    finally:
        s.close()

rc, out = fastboot(["getvar", "current-slot"])
log("vorher: " + out.replace("\n", " | ") + " | usb=" + pixel_present())
rc, out = fastboot(["boot", IMG], 120)
log("boot rc=%d" % rc)
t0 = time.time()
while time.time() - t0 < 120:
    t = time.time() - t0
    log("t=%3.0fs usb=%s telnet=%s fastboot=%s" % (t, pixel_present(), "offen" if telnet_up() else "zu", "an" if fastboot(["getvar","product"],4)[0]==0 else "aus"))
    time.sleep(1)
log("Fenster zu")
