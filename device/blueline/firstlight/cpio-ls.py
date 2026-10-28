#!/usr/bin/env python3
"""Listet newc-cpio-Eintraege eines (gzip-)Archivs so, wie der Kernel sie liest.

Warum ein eigenes Werkzeug: der Kernel justiert die Daten- und die
Naechstart-Adresse relativ zum Eintragsanfang (calc_pad off = (off-sizeof(hdr))
+ sizeof(hdr) + namesize, dann gerundet). Ein Walk, der -- wie bei mir zuerst --
absolute Grenzen rechnet, steigt nach dem ersten Eintrag aus und behauptet dann
es gaebe nur einen. Dieses Skript rechnet relativ und meldet, was PID 1 braucht:
ein 'init' im Archivgrund mit ausfuehrbarem Modus.
"""
import gzip
import sys

MAGIC = b"070701"


def fields(chunk):
    def f(off):
        return int(chunk[off:off + 8].decode("ascii"), 16)
    return {
        "mode": f(14), "uid": f(22), "gid": f(30), "nlink": f(38),
        "mtime": f(46), "filesize": f(54), "devm": f(62), "devc": f(70),
        "namesz": f(94),
    }


def walk(raw):
    off = 0
    n = 0
    entries = []
    while raw[off:off + 6] == MAGIC:
        h = fields(raw[off:off + 110])
        namesz = h["namesz"]
        name = raw[off + 110:off + 110 + namesz].split(b"\0")[0].decode("latin1")
        # Kernel-Rechnung: Datenoffset relativ zum Eintragsanfang
        data = off - (off & 3) + 110 + namesz
        data = (data + 3) & ~3
        entries.append((n, name, oct(h["mode"]), h["filesize"], h["devm"], h["devc"]))
        n += 1
        off = data + h["filesize"]
        off = (off + 3) & ~3
        if n > 500000:
            raise SystemExit("Abbruch nach 500k Eintraegen")
    trailer = raw[off:off + 110]
    return entries, trailer, off


def main(path):
    blob = open(path, "rb").read()
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    print(f"{path}: entpackt {len(blob)} Bytes")
    entries, trailer, off = walk(blob)
    print(f"Eintraege: {len(entries)}  Trailer ab {off}: {trailer[:46]!r}")
    names = {e[1]: e for e in entries}
    for want in (".", "init", "bin/busybox", "bin/sh"):
        if want in names:
            print("  ", names[want])
    for n, name, mode, size, devm, devc in entries[:8]:
        print(f"   #{n} {name!r} mode={mode} size={size} dev={devm:x},{devc:x}")
    bad = [e for e in entries if not trailer.startswith(b"070701TRAILER")]
    if "init" not in names:
        print("FEHLT: kein init im Archivgrund -> Kernel faellt auf mount_rootzurueck")
        return 1
    mode = int(names["init"][2], 8)
    if not mode & 0o111:
        print("FEHLT: init hat kein Ausfuehrbit:", oct(mode))
        return 1
    print("ok - init vorhanden, modus", oct(mode), "groesse", names["init"][3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
