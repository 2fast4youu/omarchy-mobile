#!/usr/bin/env python3
"""Ein Befehl ueber die ACM-Serielle-Konsole am Telefon (ttyGS0 -> /dev/cu.*).

Anlass: in der Nacht auf 2026-11-03 ist das Telefon auf USB sichtbar
(0x18d1:0xd002, Hersteller 'Omarchy Mobile'), aber ohne IP und ohne Fastboot.
Dafuer steht einshell auf der seriellen Konsole: /dev/cu.usbmodem103303
antwortet auf jede Zeile mit '~ #'. Diese Leitung war bisher nie benutzt.

Die Shell buegelt ihre Antwort mit CR LF und schickt die Cursor-Auskunft
ESC[6n — beides wird hier weggenommen, bevor gerahmt wird.
"""
import os
import re
import select
import sys
import termios
import time
import tty

KNOTEN = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem103303"
BEFEHLE = sys.argv[2:] or ["cat /proc/uptime"]


def oeffne(pfad):
    fd = os.open(pfad, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = termios.IGNBRK | termios.ICRNL          # rohe Leitung, aber CR -> LF
    a[1] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[2] &= ~termios.PARENB                                    # echtes 8N1, kein Paritaetsbit
    a[3] = 0
    a[4] = termios.B115200
    a[5] = termios.B115200
    a[6][termios.VMIN] = 0
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def lies(fd, frist):
    daten = bytearray()
    ende = time.time() + frist
    while time.time() < ende:
        if select.select([fd], [], [], 0.2)[0]:
            try:
                brocken = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if brocken:
                daten += brocken
        elif daten and daten.rstrip().endswith(b"#"):
            break
    return daten


def main():
    fd = oeffne(KNOTEN)
    try:
        lies(fd, 1.0)                              # Was auch immer anliegt, verwerfen
        for befehl in BEFEHLE:
            os.write(fd, (befehl + "\n").encode())
            antwort = lies(fd, 3.0).decode("utf-8", "replace")
            antwort = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", antwort)
            zeilen = [z.strip() for z in antwort.splitlines() if z.strip()]
            while zeilen and befehl[:20] in zeilen[0]:
                zeilen.pop(0)
            print("# %s" % befehl)
            for z in zeilen[:14]:
                print("   " + z[:150])
            if not zeilen:
                print("   (keine Antwort innerhalb der Frist)")
    finally:
        os.close(fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
