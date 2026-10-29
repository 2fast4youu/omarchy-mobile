#!/usr/bin/env python3
"""Kernel-Blob (Kernel + DTB-Anhang) aus einem Android-boot.img herausloesen.

Der Blob liegt auf der ersten Seite nach dem Kopf und endet mit kernel_size.
Benutzung: kernel-blob-from-image.py <boot.img> <ziel>
"""
import struct
import sys

img, dest = sys.argv[1], sys.argv[2]
d = open(img, "rb").read()
page = struct.unpack_from("<I", d, 40)[0] or 4096
if page < 512:
    page = 4096          # v0-Kopf: das page_size-Feld ist 0, packt wird auf 4096
ks = struct.unpack_from("<I", d, 8)[0]
blob = d[page:page + ks]
GZIP = bytes.fromhex("1f8b08")
assert blob[:3] == GZIP, "Kernel-Blob beginnt nicht mit gzip-Magic (%s)" % blob[:3].hex()
open(dest, "wb").write(blob)
print("Kernel-Blob %d B (%s) -> %s" % (len(blob), img, dest))
