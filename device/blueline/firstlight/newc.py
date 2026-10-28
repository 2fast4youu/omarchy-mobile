#!/usr/bin/env python3
"""Newc-cpio round-trip: init in einer Initramfs ersetzen, Rest byte-treu.

Warum ein eigener Umbauer: Alpine edge hat weder bsdtar noch einen cpio-faehigen
tar, und macOS-bsdtar kann als User keine Device-Knoten anlegen (still kaputtes
Archiv, bootet nicht). Newc legt die Daten direkt hinter den (auf 4 Bytes
aufgefuellten) Namen, das ist hier eins zu eins so implementiert; die
 Rueckleseprobe nach dem Schreiben faengt einen sonst still falschen Umbau.
"""
import sys

MAGIC = b"070701"
HDR = 110
FIELDS = ("ino", "mode", "uid", "gid", "nlink", "mtime", "datasize",
          "devmajor", "devminor", "rdevmajor", "rdevminor", "namesize", "check")


def read_cpio(path):
    data = open(path, "rb").read()
    off, entries = 0, []
    while off < len(data):
        if data[off:off + 6] != MAGIC:
            raise SystemExit(f"neue cpio-magic bei {off}: {data[off:off+6]!r} (Datei {len(data)} Bytes)")
        m = {n: int(data[off + 6 + i * 8: off + 14 + i * 8], 16) for i, n in enumerate(FIELDS)}
        off += HDR
        name = data[off:off + m["namesize"] - 1].decode("utf-8", "surrogateescape")
        off += m["namesize"]
        off = (off + 3) & ~3
        content = data[off:off + m["datasize"]]
        off += m["datasize"]
        off = (off + 3) & ~3
        entries.append({"meta": m, "name": name, "content": content})
        if name == "TRAILER!!!":
            return entries
    raise SystemExit("kein TRAILER!!! gefunden")


def emit(entries):
    out = bytearray()
    for e in entries:
        m = dict(e["meta"])
        name = e["name"].encode("utf-8", "surrogateescape") + b"\0"
        m["namesize"] = len(name)
        m["datasize"] = len(e["content"])
        hdr = MAGIC + b"".join(b"%08X" % m[k] for k in FIELDS)
        assert len(hdr) == HDR, len(hdr)
        out += hdr + name
        out += b"\0" * ((-len(out)) % 4)
        out += e["content"]
        out += b"\0" * ((-len(out)) % 4)
    return bytes(out)


if __name__ == "__main__":
    src, dst, replace = sys.argv[1], sys.argv[2], sys.argv[3]
    entries = read_cpio(src)
    want = open(replace, "rb").read()
    hits = 0
    for e in entries:
        if e["name"] in ("init", "./init"):
            e["content"] = want
            e["meta"]["mode"] = (e["meta"]["mode"] & ~0o7777) | 0o755
            hits += 1
    assert hits, f"kein init-Eintrag in {src}"
    buf = emit(entries)
    open(dst, "wb").write(buf)
    back = [e for e in read_cpio(dst) if e["name"] in ("init", "./init")]
    assert len(back) == 1 and back[0]["content"] == want, "Rueckleseprobe fehlgeschlagen"
    print(f"{len(entries)} Eintraege, init ersetzt ({len(want)} Bytes), Archiv {len(buf)} Bytes, Rueckleseprobe ok")
