#!/usr/bin/env python3
r"""v0ap -> v0aq: den blueline-eigenen ZAP-Shader an seinen Pfad legen.

Der Treiber fragt qcom/sdm845/Google/blueline/a630_zap.mbn an. v0ap hatte nur
qcom/a630_zap.mbn (aus sdm845/) - der Ladeversuch endete mit -2. Der Shader
ist signiert und wird von TrustZone geprueft; die Datei kommt aus dem
pmOS-Chroot (chroot_rootfs_google-blueline), also aus Googles Firmware.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

QUELLE = os.environ.get("FW", "/fw/qcom")
ZIEL = "lib/firmware/qcom/sdm845/Google/blueline/a630_zap.mbn"
DIRS = ("lib/firmware/qcom/sdm845", "lib/firmware/qcom/sdm845/Google",
        "lib/firmware/qcom/sdm845/Google/blueline")
TITEL_ALT = "Omarchy Mobile first-light v0ap"
TITEL_NEU = "Omarchy Mobile first-light v0aq"


def eintrag(name, mode, content, ino):
    return {"name": name, "content": content,
            "meta": {"ino": ino, "mode": mode, "uid": 0, "gid": 0, "nlink": 1,
                     "mtime": 1762266000, "datasize": len(content),
                     "devmajor": 0, "devminor": 0, "rdevmajor": 0, "rdevminor": 0,
                     "namesize": len(name) + 1, "check": 0}}


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0aq-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
        return 2
    ein, aus = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein)
    namen = [e["name"] for e in es]
    assert ZIEL not in namen, "ZAP liegt schon im Archiv"
    assert any(TITEL_ALT in (e["content"] or b"").decode("utf-8", "replace")
               for e in es if e["name"] == "init"), "v0ap-Titel fehlt"

    for e in es:
        if e["name"] == "init":
            txt = e["content"].decode()
            e["content"] = txt.replace(TITEL_ALT, TITEL_NEU).encode()

    neue = []
    ino = 910000
    for d in DIRS:
        if d not in namen:
            ino += 1
            neue.append(eintrag(d, 0o40755, b"", ino))
    pfad = os.path.join(QUELLE, "sdm845/Google/blueline/a630_zap.mbn")
    assert os.path.isfile(pfad), "ZAP fehlt: %s" % pfad
    inhalt = open(pfad, "rb").read()
    neue.append(eintrag(ZIEL, 0o100644, inhalt, ino + 1))

    pos = namen.index("TRAILER!!!")
    es[pos:pos] = neue
    blob = newc.emit(es)
    open(aus, "wb").write(blob)
    os.chmod(aus, 0o644)
    zurueck = newc.read_cpio(aus)
    namen2 = [e["name"] for e in zurueck]
    assert ZIEL in namen2, "ZAP fehlt nach round-trip"
    for d in DIRS:
        assert d in namen2, "Ordner fehlt: %s" % d
    assert namen2.index("lib/firmware/qcom/sdm845/Google/blueline") < namen2.index(ZIEL)
    init = next(e["content"] for e in zurueck if e["name"] == "init")
    assert TITEL_NEU.encode() in init, "Titel nach round-trip weg"
    print("baue-v0aq: %d Eintraege, ZAP %d B sha %s"
          % (len(zurueck), len(inhalt), hashlib.sha256(inhalt).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
