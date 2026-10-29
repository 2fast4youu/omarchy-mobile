#!/usr/bin/env python3
"""Orakel: Beweise aus der lebenden pmOS-Debug-Shell ins Repo sichern.

Warum ein eigenes Skript: die Shell hat Echo an, also wiederholt jede Antwort
das Kommando, und lange Kommandos brechen mitten im Wort um. Einreader, der
das nicht abschneidet, speichert Prompt-Müll als Beweis. Dieses Skript wirft
die Bannerzeile und jede Kommando-Echozeile weg und schreibt nur die Antwort.
"""
from __future__ import annotations

import os
import socket
import sys
import time

HOST = os.environ.get("PMOS_HOST", "172.16.42.1")
PORT = int(os.environ.get("PMOS_PORT", "23"))
IAC, WILL, WONT, DO, DONT, SB, SE = 255, 251, 252, 253, 254, 250, 240
PROMPT = "~ # "


def deny_telnet(buf: bytes) -> bytes:
    """Subnegotiation ablehnen, IAC-Befehle entfernen, Daten halten."""
    out = bytearray()
    i = 0
    while i < len(buf):
        if buf[i] == IAC and i + 2 < len(buf):
            cmd, opt = buf[i + 1], buf[i + 2]
            if cmd in (WILL, WONT):
                out += bytes([IAC, DONT if cmd == WILL else WONT, opt])
                i += 3
                continue
            if cmd in (DO, DONT):
                out += bytes([IAC, WONT, opt])
                i += 3
                continue
            if cmd == SB:
                end = buf.find(bytes([IAC, SE]), i)
                if end == -1:
                    break
                out += bytes([IAC, WONT, buf[i + 1]])
                i = end + 2
                continue
        out.append(buf[i])
        i += 1
    return bytes(out)


class Shell:
    def __init__(self, host=HOST, port=PORT, timeout=25):
        self.s = socket.create_connection((host, port), 10)
        self.s.settimeout(timeout)

    def _drain(self, stop_on_prompt: bool) -> str:
        buf = bytearray()
        t0 = time.time()
        try:
            while True:
                c = self.s.recv(65536)
                if not c:
                    break
                buf += c
                if stop_on_prompt and PROMPT in buf.decode(errors="replace")[
                        len(PROMPT):] and time.time() - t0 > 0.6:
                    break
        except socket.timeout:
            pass
        return deny_telnet(bytes(buf)).decode(errors="replace")

    def hello(self) -> str:
        self.s.sendall(b"\r\n")
        time.sleep(1.0)
        return self._drain(False)

    def run(self, cmd: str, timeout: float | None = None) -> str:
        if timeout:
            self.s.settimeout(timeout)
        self.s.sendall((cmd + "\r\n").encode())
        time.sleep(0.4)
        raw = self._drain(True)
        self.s.settimeout(25)
        return strip_echo(cmd, raw)

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


def strip_echo(cmd: str, raw: str) -> str:
    """Echo und Prompt entfernen; umbrochene Kommandozeilen zusammensetzen."""
    joined = raw.replace("\r\r\n", "\r\n").replace("\r\n", "\n")
    lines = joined.split("\n")
    # das echo der eigeen Kommandozeile kann umbrochen sein: alles abziehen,
    # was zeichenweise (ohne Leerzeichen-Am-Zeilenanfang-Klarheit) dem Kommando
    # entspricht, bis die erste Zeile, die damit nichts mehr zu tun hat
    out, skip = [], True
    flat = cmd.replace(" ", "")
    for ln in lines:
        s = ln.strip()
        if skip:
            probe = s.replace(" ", "")
            if probe and flat.startswith(probe[:40]):
                flat = flat[len(probe):] if probe == flat[:len(probe)] else flat
                if not flat:
                    skip = False
                continue
            if s.startswith("~ #"):
                continue
            skip = False
        if s.startswith("~ #"):
            continue
        out.append(ln)
    return "\n".join(out).strip("\n") + "\n"


MEASURES = [
    # (dateiname, kommando)
    ("cmdline.txt", "cat /proc/cmdline"),
    ("modules.txt", "cat /proc/modules"),
    ("lsmod.txt", "lsmod"),
    ("udc-list.txt", "ls -l /sys/class/udc"),
    ("udc-state.txt", "for f in /sys/class/udc/*/state; do echo \"== $f\"; cat \"$f\"; done"),
    ("udc-soft-bus.txt", "for f in /sys/class/udc/*/soft_bus_speed /sys/class/udc/*/maximum_speed /sys/class/udc/*/is_active; do echo \"== $f\"; cat \"$f\" 2>/dev/null; done"),
    ("gadget-tree.txt", "find /sys/kernel/config/usb_gadget -maxdepth 4"),
    ("gadget-values.txt", "for f in $(find /sys/kernel/config/usb_gadget -maxdepth 4 -type f 2>/dev/null | grep -v '/parameters/' | sort); do echo \"== $f\"; cat \"$f\" 2>/dev/null; done"),
    ("gadget-links.txt", "find /sys/kernel/config/usb_gadget -maxdepth 4 -type l -printf '%p -> %l\\n' 2>/dev/null || ls -l /sys/kernel/config/usb_gadget/g1/configs/c.1/"),
    ("configfs-mount.txt", "mount | grep -iE 'configfs|function'"),
    ("ncm-iface.txt", "ip addr show usb0; echo --; cat /sys/class/net/usb0/operstate; echo --; ls -l /sys/class/net/usb0/device 2>/dev/null"),
    ("typec.txt", "for d in /sys/class/typec/*; do echo \"== $d\"; for f in $d/*; do [ -f \"$f\" ] && echo \"-- ${f##*/}\" && cat \"$f\" 2>/dev/null; done; done"),
    ("dwc3.txt", "ls -l /sys/bus/platform/devices/ | grep -iE 'usb|dwc' ; echo --; cat /sys/bus/platform/devices/a600000.usb/mode 2>/dev/null; echo --; cat /sys/kernel/debug/usb/*/*/registers 2>/dev/null | head -20"),
    ("ttyGS.txt", "ls -l /dev/ttyGS0 /dev/ttyGS1 2>&1; echo --; ls -l /dev/gadget* 2>&1"),
    ("serial-getty.txt", "ps | grep -iE 'getty|telnetd|udhcpd|buffy' | grep -v grep"),
    ("pmOS-init-log.txt", "cat /pmOS_init.log"),
    ("uname.txt", "uname -a; echo --; cat /etc/os-release 2>/dev/null | head -5; echo --; cat /etc/alpine-release 2>/dev/null"),
    ("fb.txt", "ls -l /dev/fb0 /dev/tty0 2>&1; echo --; cat /sys/class/vtconsole/vtcon*/name 2>/dev/null; echo --; cat /sys/class/graphics/fb0/virtual_size 2>/dev/null; echo --; cat /sys/class/drm/card*/status 2>/dev/null"),
    ("partitions.txt", "cat /proc/partitions"),
    ("init-find.txt", "ls -l /init /init_functions.sh /usr/share/postmarketos-initramfs/ 2>&1 | head -30"),
    ("dtb-board.txt", "cat /proc/device-tree/model 2>/dev/null; echo; cat /proc/device-tree/compatible 2>/dev/null | tr '\\0' ' '; echo"),
    ("net-config-scripts.txt", "ls -l /usr/share/udhcpc/ 2>&1; echo --; cat /usr/share/udhcpc/default.script 2>/dev/null"),
]


def main() -> int:
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    only = sys.argv[2:]
    sh = Shell()
    banner = sh.hello()
    if "postmarketOS debug shell" not in banner:
        print("not ok - Shell antwortet nicht wie erwartet: %r" % banner[:120])
        return 1
    print("ok - Orakel erreichbar (%s)" % PROMPT.strip())
    n = 0
    for name, cmd in MEASURES:
        if only and name not in only:
            continue
        if name == "dmesg.txt":
            continue
        text = sh.run(cmd)
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        first = text.splitlines()[0] if text else "(leer)"
        print("ok - %-24s %5d B  erste zeile: %s" % (name, len(text), first[:70]))
        n += 1
    sh.close()
    print("MESSAGE: %d Beweise gesichert nach %s" % (n, out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
