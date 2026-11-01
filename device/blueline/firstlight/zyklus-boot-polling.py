#!/usr/bin/env python3
# Bootet die Referenz per fastboot boot (RAM) und pollt alle 2 s auf
# Telnet 172.16.42.1:23 und ACM-Port. Protokoll mit Zeitstempeln.
import glob, socket, subprocess, sys, time, datetime

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
IMG = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
LOG = "/Users/gregor/.hermes/cache/scratch/zyklus-" + datetime.datetime.now().strftime("%H%M%S") + ".log"

def log(msg):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def fastboot(args, t=60):
    try:
        r = subprocess.run([FB] + args, capture_output=True, text=True, timeout=t)
        return (r.returncode, (r.stdout + r.stderr).strip())
    except subprocess.TimeoutExpired:
        return (124, "TIMEOUT (kein Fastboot-Geraet erreichbar)")

def telnet_up():
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect(("172.16.42.1", 23)); return True
    except OSError:
        return False
    finally:
        s.close()

def acm_up():
    return glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*")

def main():
    rc, out = fastboot(["getvar", "current-slot"], 15)
    log("vorher: " + out.replace("\n", " | "))
    rc, out = fastboot(["boot", IMG], 120)
    log("boot rc=%d out=%s" % (rc, out.replace("\n", " | ")))
    t0 = time.time()
    telnet_seen = acm_seen = fastboot_again = 0.0
    while time.time() - t0 < 150:
        if not telnet_seen and telnet_up():
            telnet_seen = time.time() - t0
            log("TELNET offen bei t=%.0fs" % telnet_seen)
        a = acm_up()
        if a and not acm_seen:
            acm_seen = time.time() - t0
            log("ACM da bei t=%.0fs: %s" % (acm_seen, a))
        if not telnet_seen:
            rc, out = fastboot(["getvar", "product"], 8)
            if rc == 0 and "blueline" in out:
                fastboot_again = time.time() - t0
                log("FASTBOOT wieder ansprechbar bei t=%.0fs" % fastboot_again)
                # noch 20 s beobachten, ob Telnet spaeter kommt
                for _ in range(10):
                    time.sleep(2)
                    if telnet_up():
                        telnet_seen = time.time() - t0
                        log("TELNET doch noch offen bei t=%.0fs" % telnet_seen)
                        break
                break
        time.sleep(2)
    log("Ergebnis: telnet=%.0fs acm=%.0fs fastback=%.0fs" % (telnet_seen, acm_seen, fastboot_again))

main()
