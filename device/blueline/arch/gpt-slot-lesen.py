#!/usr/bin/env python3
"""Liest die GPT eines UFS-LUN und zeigt die Attribute der boot-Partitionen.

Nur lesend. Die Slot-Flags von blueline liegen in den GPT-Attributen; ein
Schreibversuch (Erfolgsmarke) ist der dokumentierte "narrow exception"-Fall
und braucht vorher/nachher alle Header und CRCs. Dieses Werkzeug liefert
den Ist-Zustand: Sektorgroesse, Header-CRC, Eintraege, Attribute.
"""
from __future__ import annotations

import struct
import sys

SIG = b"EFI PART"


def header_at(f, off):
    f.seek(off)
    hdr = f.read(92)
    if len(hdr) < 92 or hdr[:8] != SIG:
        return None
    (rev, hsize, hcrc, _res, my_lba, alt_lba, first_use, last_use,
     disk_guid, entries_lba, num, esize, ecrc) = struct.unpack_from("<IIIIQQQQ16sQIII", hdr, 8)
    return {"rev": rev, "hsize": hsize, "hcrc": hcrc, "my_lba": my_lba,
            "alt_lba": alt_lba, "first_use": first_use, "last_use": last_use,
            "entries_lba": entries_lba, "num": num, "esize": esize, "ecrc": ecrc}


def main():
    if len(sys.argv) != 2:
        print("Gebrauch: gpt-slot-lesen.py /dev/sdX", file=sys.stderr)
        return 2
    path = sys.argv[1]
    with open(path, "rb") as f:
        for ssize in (512, 4096):
            hdr = header_at(f, ssize)
            if hdr:
                print("%s: Sektorgroesse %d, %d Eintraege a %d B, Eintraege bei LBA %d"
                      % (path, ssize, hdr["num"], hdr["esize"], hdr["entries_lba"]))
                f.seek(hdr["entries_lba"] * ssize)
                raw = f.read(hdr["num"] * hdr["esize"])
                for i in range(hdr["num"]):
                    e = raw[i * hdr["esize"]:(i + 1) * hdr["esize"]]
                    if len(e) < 128 or e[:16] == b"\0" * 16:
                        continue
                    first, last, attrs = struct.unpack_from("<QQQ", e, 32)
                    name = e[56:128].decode("utf-16-le", "replace").split("\0")[0]
                    if "boot" in name or name in ("misc", "metadata"):
                        print("  %-24s LBA %6d..%-6d Attribute 0x%016x" % (name, first, last, attrs))
                return 0
        print("keine GPT gefunden (weder 512- noch 4096-Byte-Sektoren)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
