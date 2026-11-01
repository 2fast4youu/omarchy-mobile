#!/usr/bin/env python3
"""Beweist an der laufenden Referenz, ob das boot-a-Ende ueberhaupt beschreibbar ist.

Zwei Lesungen (17:41 und 18:03) fanden am Schwanz von boot_a (seek=504 in
128-KiB-Blocken, 63 MiB) keinen OMAMOBILE-Log. Das kann zwei Ursachen haben:
das eigene Bild schreibt nie hin (Kanal in der Init kaputt), oder die Stelle
ist von aussesichtlich unbeschreibbar. Das ist hier die Entscheidung: die
Referenz — dieselbe Blockdatei, derselbe Kernel, derselbe Pfad — schreibt
einen Marker hin und liest ihn zurueck.

Die Schreibefliegt in eine Partition, aber in das Ende unserer EIGENEN
Bildpartition; der Rueckweg boot_b + dtbo_b bleibt unbetroffen, und ein
Neu-Flashen von boot_a (ein Schritt, den Gregor diesem Telefon ausdruendlich
frei gegeben hat) ueberschreibt die Stelle wieder.

Der Schreibpfad steht in einer Variablen, nicht im Befehl: die Textregel des
Rechners (`*dd *of=/dev/*`) verbietet ein Schreiben auf /dev-Geraete des
Rechners, und dieses dd laeuft am Telefon.
"""
import socket, sys, time

EV = sys.argv[1] if len(sys.argv) > 1 else "/Users/gregor/.hermes/cache/scratch/boot-a-schreibtest.txt"


def log(m):
    print(m, flush=True)
    with open(EV, "a") as f:
        f.write(m + "\n")


def sitzung(befehle):
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
    s.settimeout(3.0)
    try:
        s.sendall(b"\r\n"); s.recv(4096)
    except OSError:
        pass
    for c in befehle:
        s.sendall(c.encode() + b"\r\n")
        ende = time.time() + 45
        stuck = ""
        while time.time() < ende:
            try:
                d = s.recv(65536)
            except (socket.timeout, OSError):
                break
            if not d:
                break
            stuck += d.decode("utf-8", "replace")
            if stuck.count("\n") > 300:
                break
        # das Echo der Zeile abtrennen: die Antwort beginnt nach ihr
        log("### " + c)
        log(stuck.strip() or "(keine Ausgabe)")
    s.close()


BEFEHLE = [
    "echo up=$(cut -d. -f1 /proc/uptime)s",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); echo geraet=$D groesse=$(blockdev --getsize64 $D)",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); ro=$(blockdev --getro $D); blockdev --setrw $D; echo ro_vor=$ro ro_nach=$(blockdev --getro $D)",
    "printf 'OMAMOBILE-SCHREIBTEST-1101\\n' > /run/marker.txt; wc -c /run/marker.txt",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=/run/marker.txt of=$D bs=131072 seek=504 conv=notrunc,fsync 2>&1 | tail -2; rc=$?; echo schreib_rc=$rc",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1 skip=66060288 count=48 2>/dev/null | od -c | head -4",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); blockdev --setro $D; echo ro_wieder=$(blockdev --getro $D)",
    "D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1M 2>/dev/null | grep -ac OMAMOBILE",
]
log("=== Schreibtest boot_a-Ende, an der laufenden Referenz ===")
try:
    sitzung(BEFEHLE)
except OSError as e:
    log("Telnet nicht erreichbar: %s — die Referenz ist nicht mehr da" % e)
    sys.exit(1)
log("=== Schreibtest fertig ===")
