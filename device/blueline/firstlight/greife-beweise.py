#!/usr/bin/env python3
# UNTERBAUEN von abgreife-flash-system.py - bei leerem Ergebnis nicht glauben.
#
# Dieser Abgreifer redet die alte Sprache (echo-Markierungen). Am 2026-11-02 um
# 00:20 und 00:25 meldete er 'fertig' und schrieb 18 Dateien mit 0 Bytes, während
# abgreife-flash-system.py im ersten Lauf 57 842 B durch die printf-Rahmen brachte.
# Die Cursor-Auskunft (Wurzel #13) ist auch hier beantwortet, das Rahmenlesen
# bleibt aber unzuverlässig: neue Beweise immer mit dem Nachfolger holen, und ein
# Leer-Lauf hier ist kein Gerät, sondern das Protokoll.
"""Greift die Beweislage aus der eigenen Shell ab, solange das Fenster offen ist.

Grund fuer die Bauart: der Selbst-Rueckweg holt das Bild nach ~370 s zurueck,
das Fenster ist also knapp, und ein halber Abgriff ist wertloser als eine
kurze Datei. Jede Datei laeuft darum in einem Rahmen:

    @@ANFANG <name> <bytezahl>     (die Zahl holt sich das Telefon selbst)
    …Payload…
    @@ENDE <name>

Der Leser verwirft nur Zeilen, die dem Befehl exakt gleich sind, und nur
Prompt-Zeilen (`~ # …`) — die Zeile, die die Entscheidung enthaelt, enthaelt
oft dasselbe erste Wort wie der Befehl, und ein Filter auf das erste Wort frisst
genau sie (gemessen an einem frueheren Heber). Dann wird die Bytezahl des
Empfangs gegen die des Telefons geprueft, die Datei mit ihrem eigenen sha256 in
einen Ordner geschrieben, und die Pruefung steht in einer Manifestdatei. Ein
Abgriff ohne Pruefung ist ein Geruecht.
"""
import gzip
import hashlib
import os
import socket
import sys
import time

ZIEL = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/evidence/abgriff"
FRIST = int(sys.argv[2]) if len(sys.argv) > 2 else 320

# Name, Befehl. Kleinste Fassung zuerst: was beim Fenster passt, ist gesichert.
ARTIKEL = [
    ("uname.txt", "uname -a"),
    ("cmdline.txt", "cat /proc/cmdline"),
    ("uptime.txt", "cat /proc/uptime"),
    ("lsmod.txt", "lsmod"),
    ("proc-modules.txt", "cat /proc/modules"),
    ("udc-liste.txt", "ls -l /sys/class/udc"),
    ("udc-state.txt", "for f in /sys/class/udc/*/(state speed maximum_speed); do echo \"$f: $(cat $f 2>/dev/null)\"; done"),
    ("gadget-baum.txt", "find /sys/kernel/config/usb_gadget -maxdepth 3 2>/dev/null"),
    ("gadget-udc.txt", "cat /sys/kernel/config/usb_gadget/g1/UDC; echo; cat /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null"),
    ("netz.txt", "ip -o addr show; ip -o route show; ifconfig -a"),
    ("kernel-config.gz.b64", "zcat /proc/config.gz 2>/dev/null | gzip -9 | base64"),
    ("steps.log", "cat /run/steps.log"),
    ("dmesg.txt", "dmesg"),
    ("pstore-dmesg-ramoops.txt", "cat /sys/fs/pstore/dmesg-ramoops-0 2>/dev/null"),
    ("pstore-console-ramoops.txt", "cat /sys/fs/pstore/console-ramoops-0 2>/dev/null"),
    ("dtb-modell.txt", "cat /proc/device-tree/model 2>/dev/null; echo; cat /proc/device-tree/compatible 2>/dev/null"),
    ("storage-ro.txt", "for f in /sys/block/sd*/ro /sys/block/sd*/size; do echo \"$f=$(cat $f 2>/dev/null)\"; done"),
    ("ramdisk-inhalt.txt", "ls -R /usr/lib/modules 2>/dev/null | head -40"),
]



def wecke_shell(s, frist=6):
    """Die Cursor-Auskunft beantworten, sonst fuehrt die Shell nichts aus.

    Busybox-ash mit Zeilenbearbeitung schickt am Prompt 'ESC[6n' und wartet auf
    die Positions-Meldung. Ein Client, die nicht antwortet, sieht nur Echo: die
    Befehle gehen in die Warteschlange, als waere die Leitung kaputt. Um 00:20
    hat das einen ganzen Abgriff leer laufen lassen (18 Dateien, 0 Bytes).
    """
    ende, ton = time.time() + frist, b""
    while time.time() < ende:
        try:
            d = s.recv(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        if not d:
            break
        ton += d
        if b"\x1b[6n" in ton:
            s.sendall(b"\x1b[1;1R")
            try:
                ton += s.recv(4096)
            except (socket.timeout, OSError):
                pass
            break
        if b"#" in ton and b"\x1b[6n" not in ton:
            break
    return ton

def hole(verbinder, name, befehl, frist_s):
    """Eine Datei im Rahmen @@ANFANG/@@ENDE abholen. Gibt (bytes, text) zurueck."""
    # Der Rahmen wird gebaut, statt ihn zu schreiben: die Shell wiederholt jeden
    # Befehl im Echo, und ein geschriebenes `@@ANFANG` taucht damit ZWEI mal auf —
    # der Sammler hielt das Echo fuer die Antwort und alles verrutschte um eine
    # Datei (gemessen 20:45, sieben Artefakte verschoben). Mit der.Concatenation
    # steht im Echo `@@AN${''}FANG`, in der Ausgabe `@@ANFANG`.
    anfang = "@@AN${''}FANG"
    ende = "@@EN${''}DE"
    groesse = "echo %s %s $(%s | wc -c)" % (anfang, name, befehl)
    verbinder.sendall((groesse + "\r\n").encode())
    text = sammle(verbinder, "@@ANFANG %s" % name, frist_s)
    if text is None:
        return None
    teil = text.split("@@ANFANG %s" % name, 1)[1].strip().split()
    gesamt = int(teil[1]) if len(teil) > 1 and teil[1].isdigit() else -1
    verbinder.sendall((befehl + "\r\n").encode())
    verbinder.sendall(("echo %s %s\r\n" % (ende, name)).encode())
    payload = sammle(verbinder, "@@ENDE %s" % name, frist_s)
    if payload is None:
        return None
   # Echo des eigenen Befehls und Prompt-Zeilen abziehen, sonst alles behalten
    zeilen = payload.split("\n")
    halte = []
    for z in zeilen:
        z = z.rstrip("\r")
        if z.strip() == befehl.strip() or z.strip() == groesse.strip():
            continue
        if z.startswith("~ #"):
            continue
        halte.append(z)
    text = "\n".join(halte).strip("\n") + "\n"
    return gesamt, text


def sammle(verbinder, marke, frist_s):
    ende, out = time.time() + frist_s, ""
    while time.time() < ende:
        try:
            d = verbinder.recv(65536)
        except (socket.timeout, OSError):
            break
        if not d:
            break
        out += d.decode("utf-8", "replace")
        if marke in out:
            return out
    return None


def main():
    os.makedirs(ZIEL, exist_ok=True)
    manifest = os.path.join(ZIEL, "manifest-%s.txt" % time.strftime("%Y-%m-%d-%H%M"))
    notiz = open(manifest, "a")

    def sage(m):
        line = time.strftime("%H:%M:%S ") + m
        print(line, flush=True)
        notiz.write(line + "\n")
        notiz.flush()

    t0 = time.time()
    while time.time() - t0 < FRIST:
        try:
            s = socket.create_connection(("172.16.42.1", 23), timeout=3)
            break
        except OSError:
            time.sleep(4)
    else:
        sage("Fenster in %ds nicht offen" % FRIST)
        return 1
    wecke_shell(s)
    s.settimeout(6.0)
    try:
        s.sendall(b"\r\n")
        s.recv(4096)
    except OSError:
        pass
    sage("=== Abgriff beginnt, Fenster %ds ===" % FRIST)
    ganz = 0
    for name, befehl in ARTIKEL:
        rest = max(25, int(FRIST - (time.time() - t0)) - 40)
        r = hole(s, name, befehl, rest)
        if r is None:
            sage("ACHTUNG leer: %s (kein Rahmen in %ds)" % (name, rest))
            continue
        gesamt, text = r
        dat = text.encode()
        if name.endswith(".b64"):
            import base64
            try:
                dat = gzip.decompress(base64.b64decode("".join(text.split()).encode()))
            except Exception as e:
                sage("ACHTUNG dekodieren fehlgeschlagen: %s (%s)" % (name, e))
                dat = text.encode()
        pfad = os.path.join(ZIEL, (name[:-4] + ".gz") if name.endswith(".b64") else name)
        with open(pfad, "wb") as f:
            f.write(dat)
        sha = hashlib.sha256(dat).hexdigest()
        gemessen = len(dat)
        # Die Bytezahl des Telefons zaehlt ohne die Rahmen-Zeichen; ein
        # Unterschied von ein paar Zeilenenden ist kein Fehler, ein Faktor wohl.
        note = "" if gesamt < 0 else ("  tel: %d" % gesamt)
        zustand = "ok" if (gesamt < 0 or abs(gemessen - gesamt) <= 4 * max(1, text.count("\n"))) else "ABWEICHUNG"
        sage("%-32s %8d B  %s  sha %s%s" % (os.path.basename(pfad), gemessen, zustand, sha[:16], note))
        ganz += gemessen
    sage("=== Abgriff fertig: %d Bytes in %s ===" % (ganz, ZIEL))
    try:
        s.sendall(b"echo ABGRIFF-FERTIG\r\n")
        s.close()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
