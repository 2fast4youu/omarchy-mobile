#!/usr/bin/env python3
# Liest in der laufenden Referenz: Kernel-Conifg-Zeilen zu PSTORE, geladene
# Module, pstore-Details, RAM-Grenze. Entscheidet, ob Ramoops-Modul ueberhaupt
# ein Crash-Protokoll ueber einen Neustart retten kann.
import socket, time

def connect():
    s = socket.create_connection(("172.16.42.1", 23), timeout=10)
    s.settimeout(4); return s

def read_some(s, secs=1.2):
    s.settimeout(secs); buf=b""
    try:
        while True:
            d=s.recv(4096)
            if not d: break
            buf+=d
    except socket.timeout: pass
    return buf.decode(errors="replace")

def run(s, cmd, wait=1.5):
    s.sendall((cmd+"\r\n").encode()); time.sleep(wait)
    return read_some(s)

s=connect(); read_some(s)
for cmd in [
  "zcat /proc/config.gz 2>/dev/null | grep -E 'PSTORE|RAMOOPS|SYSRQ|CRASH|CMDLINE_PARTITION' ; echo FERTIG_CONFIG",
  "cat /proc/modules | awk '{print $1, $2, $3}' | head -40",
  "cat /proc/iomem | tail -8",
  "cat /proc/meminfo | head -3",
  "ls /sys/module/ | tr '\\n' ' '",
  "dmesg | grep -iE 'pstore|ramoops|reserved|Memory:' | head -20",
]:
    print("### " + cmd)
    print(run(s, cmd, 2.5))
