#!/usr/bin/env python3
# Ramoops (pstore-RAM-Konsole) in der laufenden Referenz setzen, Umgebungs-
# beweise einsammeln, dann per RESTART2 "bootloader" zurueck nach Fastboot.
# Danach kann ein RAM-Boot (fastboot boot) gestartet und seinconsole-Log hier
# ausgelesen werden. Nur RAM — kein Partitions-Write.
import socket, subprocess, time, sys

HOST = "172.16.42.1"; PORT = 23
FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"

def connect():
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.settimeout(5)
    return s

def read_some(s, secs=1.0):
    s.settimeout(secs)
    buf = b""
    try:
        while True:
            d = s.recv(4096)
            if not d: break
            buf += d
    except socket.timeout:
        pass
    return buf.decode(errors="replace")

def run(s, cmd, wait=2.0):
    s.sendall((cmd + "\r\n").encode())
    time.sleep(wait)
    return read_some(s, 1.5)

def wait_ref(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = connect()
            read_some(s, 1.0)
            return s
        except OSError:
            time.sleep(3)
    return None

phase = sys.argv[1] if len(sys.argv) > 1 else "setzen"

if phase == "setzen":
    s = connect(); read_some(s, 1.0)
    print(run(s, "uname -r"))
    print(run(s, "modprobe ramoops mem_address=0x9f000000 mem_size=0x100000 record_size=0x20000 console_size=0x40000 pmsg_size=0 ftrace_size=0", 4))
    print(run(s, "mount -t pstore pstore /sys/fs/pstore 2>&1; ls /sys/module/ramoops 2>&1"))
    print(run(s, "cat /sys/module/ramoops/parameters/mem_address 2>&1"))
    print(run(s, "dmesg > /dev/kmsg 2>&1; echo DMESG_ABGEGEBEN"))
    print(run(s, "cat /proc/cmdline | tr ' ' '\\n' | grep -E 'slot_suffix|dtbo_idx|dtb_idx|ramdump|suzyq|bootreason|force_normal' 2>&1"))
    print(run(s, "ls -l /dev/disk/by-name/ 2>&1 | head -30", 3))
    print(run(s, "ls /lib/modules/$(uname -r)/kernel/fs/pstore/ 2>&1; ls /lib/modules/$(uname -r)/ 2>&1 | head -5"))
    print(run(s, "echo 1 > /proc/sys/kernel/panic 2>&1; cat /proc/sys/kernel/panic", 2))
    print(run(s, "echo b > /proc/sysrq-trigger", 3))
    print("RESTART2 gesendet — naechster Schritt: RAM-Boot + lesen")
elif phase == "lesen":
    s = wait_ref()
    if not s:
        print("Referenz nicht erreichbar"); raise SystemExit(1)
    print(run(s, "ls -la /sys/fs/pstore/"))
    for f in ["console-ramoops-0", "console-ramoops-1", "pmsg-ramoops-0",
              "dmesg-ramoops-0"]:
        out = run(s, "tail -c 12000 /sys/fs/pstore/%s 2>&1" % f, 2.5)
        if "No such" not in out:
            print("===== %s =====" % f)
            print(out)
    read_some(s, 0.5)
