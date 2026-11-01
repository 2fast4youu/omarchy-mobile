#!/usr/bin/env python3
"""Telnet-Leser fuer die Referenz-Shell (172.16.42.1:23), nur lesend bis auf den
letzten Schritt. b) pstore/ramoops pruefen, c) reboot-Rueckweg vorbereiten."""
import telnetlib
import sys
import time

HOST = "172.16.42.1"
PORT = 23

tn = telnetlib.Telnet(HOST, PORT, timeout=15)
# Begruessung/Prompt lesen (pmos_getty = /bin/sh -l)
try:
    init = tn.read_until(b"# ", timeout=15)
except EOFError:
    init = b""
sys.stdout.write("INIT: %r\n" % init[-300:])

cmds = [
    "id; uname -a",
    "ls -la /sys/fs/pstore 2>&1",
    "cat /sys/fs/pstore/* 2>&1 | head -80",
    "mount 2>/dev/null | grep -i pstore",
    "ls -la /dev/pmsg* 2>&1",
    "cat /proc/cmdline",
    "ls /sys/firmware/devicetree/base/reserved-memory 2>&1",
    "for d in /sys/firmware/devicetree/base/reserved-memory/*; do echo \"$d:\"; cat \"$d/compatible\" 2>/dev/null; echo; done",
    "cat /sys/kernel/config/usb_gadget/*/idProduct 2>/dev/null; cat /sys/kernel/config/usb_gadget/*/UDC 2>/dev/null",
    "cat /run/steps.log 2>/dev/null | tail -5",
]
for c in cmds:
    tn.write((c + "\n").encode())
    time.sleep(0.6)
    try:
        out = tn.read_until(b"# ", timeout=15)
    except EOFError:
        out = b""
    sys.stdout.write("=== %s ===\n%s\n" % (c, out.decode(errors="replace")[-3000:]))

tn.write(b"exit\n")
tn.close()
