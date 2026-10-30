#!/usr/bin/env python3
"""Schlusspruefung am fertigen v0q-Bild: zuruecklesen, nicht glauben.

    verify-v0q.py <firstlight.img> [modulverzeichnis]

Prueft den Kopf (page_size-Feld 0, Ramdisk seitenbuendig gzip), dann aus dem
Archiv: Module mit ELF-Magic und 0644 unter dem Referenzpfad, Init mit
insmod-Block vor dem configfs-Mount, und der Referenz-Gadget-Block unveraendert
(seine Pflichtzeilen, weil die Datei selbst Kommentare mit Umlauten traegt).
Exit 1 bei jedem Befund.
"""
import gzip
import os
import re
import struct
import sys

FL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FL)
import newc  # noqa: E402

VERSION = "7.1.0-rc1-sdm845"
MODBASE = "usr/lib/modules/" + VERSION + "/kernel/drivers/usb/gadget"
MODULES = [MODBASE + "/libcomposite.ko",
           MODBASE + "/function/u_ether.ko",
           MODBASE + "/function/usb_f_ncm.ko",
           MODBASE + "/function/u_serial.ko",
           MODBASE + "/function/usb_f_acm.ko",
           MODBASE + "/function/usb_f_rndis.ko"]
FAILS = []
COUNT = [0]


def check(cond, msg):
    COUNT[0] += 1
    if cond:
        print("ok - " + msg)
    else:
        print("not ok - " + msg)
        FAILS.append(msg)


def main():
    img = sys.argv[1]
    modsrc = sys.argv[2] if len(sys.argv) > 2 else "/m"
    d = open(img, "rb").read()
    page = struct.unpack_from("<I", d, 40)[0] or 4096
    if page < 512:
        page = 4096              # v0-Kopf: page_size-Feld 0, packt auf 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    rs = struct.unpack_from("<I", d, 16)[0]
    check(d[40:44] == bytes.fromhex("00000000"), "page_size-Feld steht auf 0 (v0-Kopf)")
    rd = 4096 + ((ks + page - 1) // page) * page
    check(d[rd:rd + 2] == bytes.fromhex("1f8b"), "Ramdisk beginnt seitenbuendig mit gzip")
    cpio = "/tmp/verify-v0q.cpio"
    open(cpio, "wb").write(gzip.decompress(d[rd:rd + rs]))
    ent = {e["name"]: e for e in newc.read_cpio(cpio)}
    check(list(ent)[-1] == "TRAILER!!!", "TRAILER!!! ist der letzte Eintrag")

    for path in MODULES:
        e = ent.get(path)
        if e is None or not e.get("content"):
            check(False, "Modul fehlt im fertigen Bild: " + path)
            continue
        src = os.path.join(modsrc, os.path.basename(path))
        same = os.path.isfile(src) and e["content"] == open(src, "rb").read()
        check(e["content"][:4] == bytes.fromhex("7f454c46")
              and (e["meta"]["mode"] & 0o777) == 0o644 and same,
              "Modul bytegleich mit der Quelle, ELF, 0644: " + os.path.basename(path))
        vm = re.search(rb"vermagic=([0-9.\-A-Za-z_]+)", e["content"])
        check(bool(vm) and vm.group(1).decode().startswith(VERSION),
              "vermagic = laufender Kernel %s: %s"
              % (VERSION, os.path.basename(path)))

    init = ent["init"]["content"].decode("utf-8")
    lines = init.splitlines()

    def first(needle):
        hits = [i for i, l in enumerate(lines) if needle in l]
        return hits[0] if hits else None

    a = first('insmod "$m"')
    b = first("mount -t configfs -o nodev,noexec,nosuid")
    c = first("functions/$netfunc")
    e2 = first("functions/acm.GS0")
    u = first('echo "$udc" > "$CONFIGFS/g1/UDC"')
    check(None not in (a, b, c, e2, u), "alle Pflichtzeilen vorhanden")
    idx = [x for x in (a, b, c, e2, u) if x is not None]
    check(len(idx) == 5 and idx == sorted(idx),
              "Reihenfolge insmod -> configfs-Mount -> ncm -> acm -> UDC (%s)" % idx)
    check("mark 'KEIN /usr/lib/modules/7.1.0-rc1-sdm845" in init
          and "/proc/modules" in init,
          "Init meldet Modul-Dunkelheit und Zaehlt /proc/modules")
    check(init.isascii(), "Init ist reines ASCII (Panel ohne UTF-Konsole)")
    # idProduct erwartet: aus dem Panel-Titel abgeleitet, nicht geraten. Der
    # Titel nennt die Bildversion, und jede Version ab v0s traegt bewusst eine
    # neue Produktzahl (0xD002), damit eine Enumeration am Bus keinem
    # frueheren Bild zugeordnet werden kann. Ein Pruefer, der beide Zahlen
    # akzeptiert, prueft nichts — deshalb steht hier genau eine Erwartung.
    titel = re.search(r"first-light (v0[0-9a-z]+)", init)
    erwartet = "echo 0xD001" if (titel and titel.group(1) in ("v0h", "v0n", "v0q", "v0r")) else "echo 0xD002"
    for probe in ("CONFIGFS=/sys/kernel/config/usb_gadget", "echo 0x18D1", erwartet,
                  "netfunc=ncm.usb0", "functions/rndis.usb0", "functions/acm.GS0",
                  'echo "" > "$CONFIGFS/g1/UDC"', "172.16.42.1"):
        check(probe in init, "Referenz-Gadget-Pflichtzeile: " + probe)
    check(not re.search(r"(?<!kernel)/config/usb_gadget", init),
          "keine erfundene zweite configfs-Lage unter /config")

    print("%d Pruempunkte, %d Fehler" % (COUNT[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
