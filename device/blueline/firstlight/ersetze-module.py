#!/usr/bin/env python3
"""v0aq-Initramfs auf einen neuen Kernel-Release umschreiben.

Die Init laedt die Gadget-Module aus /usr/lib/modules/<Release>/...; der
Release steht als Zeichenkette in der Init. Dieses Skript ersetzt die sechs
.ko-Eintraege durch die Module aus dem neuen Bau, benennt die Pfade auf den
neuen Release um und zieht die Init-Zeichenkette nach.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

ALT = "7.1.0-rc1-sdm845"
MODULE = ("libcomposite.ko", "u_ether.ko", "usb_f_ncm.ko",
          "u_serial.ko", "usb_f_acm.ko", "usb_f_rndis.ko")


def finde(bau, name):
    for root, _dirs, files in os.walk(bau):
        if name in files:
            return os.path.join(root, name)
    raise SystemExit("Modul fehlt im Bau: %s" % name)


def main():
    if len(sys.argv) != 4:
        print("Gebrauch: ersetze-module.py EIN.cpio NEUER_RELEASE BAU_DIR", file=sys.stderr)
        return 2
    ein, neu, bau = sys.argv[1], sys.argv[2], sys.argv[3]
    es = newc.read_cpio(ein)
    ersetzt = 0
    for e in es:
        name = e["name"]
        if ALT in name:
            if name.endswith(".ko"):
                base = os.path.basename(name)
                assert base in MODULE, "unerwartetes Modul: %s" % base
                e["content"] = open(finde(bau, base), "rb").read()
                e["meta"]["datasize"] = len(e["content"])
                ersetzt += 1
            e["name"] = name.replace(ALT, neu)
        elif name == "init":
            txt = e["content"].decode()
            if ALT not in txt:
                raise SystemExit("Init nennt den alten Release nicht")
            txt = txt.replace(ALT, neu)
            e["content"] = txt.encode()
            e["meta"]["datasize"] = len(e["content"])
    assert ersetzt == len(MODULE), "nur %d Module ersetzt" % ersetzt
    blob = newc.emit(es)
    open(sys.argv[1] + ".neu", "wb").write(blob)
    zurueck = newc.read_cpio(sys.argv[1] + ".neu")
    namen = [x["name"] for x in zurueck]
    assert not any(ALT in n for n in namen), "alter Release noch im Archiv"
    assert any(n.endswith("usb_f_ncm.ko") and "/" + neu + "/" in n for n in namen)
    init = next(x["content"] for x in zurueck if x["name"] == "init").decode()
    assert neu in init and ALT not in init
    print("ok - %d Module auf %s umgestellt, %d Eintraege" % (ersetzt, neu, len(zurueck)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
