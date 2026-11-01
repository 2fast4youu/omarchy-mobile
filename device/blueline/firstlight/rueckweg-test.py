#!/usr/bin/env python3
"""c) Rueckweg: aus der Referenz-Shell 'reboot bootloader' senden, dann am Mac
auf Fastboot (18d1:4ee0) warten. Kein Flash, nur RAM-Boot."""
import telnetlib
import time
import subprocess
import sys

tn = telnetlib.Telnet("172.16.42.1", 23, timeout=10)
tn.read_until(b"# ", timeout=10)
tn.write(b"reboot bootloader\n")
time.sleep(0.5)
tn.close()
print("reboot bootloader gesendet", flush=True)

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
deadline = time.time() + 120
seen = None
while time.time() < deadline:
    time.sleep(2)
    devs = subprocess.run([FB, "devices"], capture_output=True, text=True).stdout.strip()
    if devs:
        seen = devs
        break
print("fastboot devices: %r" % seen)
if seen:
    r = subprocess.run([FB, "getvar", "current-slot"], capture_output=True, text=True)
    print("getvar current-slot: %r" % r.stdout.splitlines()[:1])
