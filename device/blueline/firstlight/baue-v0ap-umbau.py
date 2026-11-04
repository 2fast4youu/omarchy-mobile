#!/usr/bin/env python3
r"""v0an -> v0ap: qcom-Firmware ins Initramfs.

Gemessen am 2026-11-04: der Kernel laedt a630_sqe.fw um 5,1 s, also VOR
switch_root. msm/adreno sind built-in und proben im Initramfs; dort gab es
/lib/firmware/qcom nicht, und der Ladeversuch endete mit error -2, obwohl die
Firmware im Rootfs liegt.

Diese Fassung legt a630_sqe.fw, a630_gmu.bin und a630_zap.mbn unter
lib/firmware/qcom in das cpio und stellt den Panel-Titel auf v0ap.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

QUELLE = os.environ.get("FW", "/fw/qcom")
DATEIEN = (("a630_sqe.fw", "a630_sqe.fw"),
           ("a630_gmu.bin", "a630_gmu.bin"),
           ("a630_zap.mbn", "sdm845/a630_zap.mbn"))
TITEL_ALT = "Omarchy Mobile first-light v0an"
TITEL_NEU = "Omarchy Mobile first-light v0ap"


def eintrag(name, mode, content, ino):
    return {"name": name,
            "content": content,
            "meta": {"ino": ino, "mode": mode, "uid": 0, "gid": 0, "nlink": 1,
                     "mtime": 1762266000, "datasize": len(content),
                     "devmajor": 0, "devminor": 0, "rdevmajor": 0, "rdevminor": 0,
                     "namesize": len(name) + 1, "check": 0}}


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0ap-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
        return 2
    ein, aus = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein)
    namen = [e["name"] for e in es]
    assert "lib/firmware" in namen, "lib/firmware fehlt im Initramfs"
    assert "lib/firmware/qcom" not in namen, "qcom-Ordner ist schon da"
    assert any(TITEL_ALT in (e["content"] or b"").decode("utf-8", "replace")
               for e in es if e["name"] == "init"), "v0an-Titel fehlt"

    for e in es:
        if e["name"] == "init":
            txt = e["content"].decode()
            e["content"] = txt.replace(TITEL_ALT, TITEL_NEU).encode()
            assert TITEL_NEU in e["content"].decode()

    neue = [eintrag("lib/firmware/qcom", 0o40755, b"", 900001)]
    for i, (ziel, quelle) in enumerate(DATEIEN, 2):
        pfad = os.path.join(QUELLE, quelle)
        assert os.path.isfile(pfad), "Firmware fehlt: %s" % pfad
        neue.append(eintrag("lib/firmware/qcom/" + ziel, 0o100644,
                            open(pfad, "rb").read(), 900000 + i))
    pos = namen.index("TRAILER!!!")
    es[pos:pos] = neue

    blob = newc.emit(es)
    open(aus, "wb").write(blob)
    os.chmod(aus, 0o644)
    zurueck = newc.read_cpio(aus)
    namen2 = [e["name"] for e in zurueck]
    for n in ("lib/firmware/qcom",) + tuple("lib/firmware/qcom/" + z for z, _ in DATEIEN):
        assert n in namen2, "fehlt nach round-trip: %s" % n
    assert namen2.index("lib/firmware/qcom") < namen2.index("lib/firmware/qcom/a630_sqe.fw")
    init = next(e["content"] for e in zurueck if e["name"] == "init")
    assert TITEL_NEU.encode() in init, "Titel nach round-trip weg"
    print("baue-v0ap: %d Eintraege, Firmware %d Dateien, %d Bytes"
          % (len(zurueck), len(DATEIEN), sum(len(e["content"]) for e in neue)))
    for ziel, _ in DATEIEN:
        e = next(x for x in zurueck if x["name"] == "lib/firmware/qcom/" + ziel)
        print("  %s %d B sha %s" % (ziel, len(e["content"]),
                                    hashlib.sha256(e["content"]).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
