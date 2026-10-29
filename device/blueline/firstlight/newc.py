#!/usr/bin/env python3
"""Replace init inside an initramfs, keeping every other entry byte for byte.

Why a own rewriter: neither bsdtar (macOS, unprivileged: it cannot create
device nodes and silently writes a short archive) nor Alpine's tar can round-trip
a newc cpio here. Newc puts a entry's data right behind its name padded to 4
bytes, which is what this does; reading the result back is what turns a silent
mis-rewrite into an error.
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
            raise SystemExit(f"not cpio at {off}: {data[off:off+6]!r} (file is {len(data)} bytes)")
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
    raise SystemExit("no TRAILER!!! entry")


def emit(entries):
    # read_cpio stops at TRAILER!!! and keeps it as the LAST entry; an added
    # file must sit BEFORE it. An append after the trailer emitted a still
    # readable archive whose restart2 entry no reader would ever reach -- the
    # v0m image on the phone (2026-10-29 02:49) carried an init that called a
    # /bin/restart2 the archive did not contain. Refuse the trap, and print
    # what was written so no build can claim a file it never shipped.
    names = [e["name"] for e in entries]
    if "TRAILER!!!" in names and names.index("TRAILER!!!") != len(names) - 1:
        raise SystemExit("TRAILER!!! must be the last entry")
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
    assert hits, f"no init entry in {src}"
    buf = emit(entries)
    open(dst, "wb").write(buf)
    back = [e for e in read_cpio(dst) if e["name"] in ("init", "./init")]
    assert len(back) == 1 and back[0]["content"] == want, "read-back check failed"
    print(f"{len(entries)} entries, init replaced ({len(want)} bytes), archive {len(buf)} bytes, read-back ok")
