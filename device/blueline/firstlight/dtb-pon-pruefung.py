#!/usr/bin/env python3
"""Referenz-DT: PON-Knoten und reboot-mode/mode-bootloader statisch pruefen.
Header v0: magic(8) kernel_size(4) ramdisk_size(4) second_size(4) page_size(4)
os_version(4) header_version(4) reserved[4]; Kernel ab Offset 44."""
import struct, zlib, sys

IMG = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
data = open(IMG, "rb").read()
assert data[:8] == b"ANDROID!"
ks, rs, ss = struct.unpack("<III", data[8:20])
print("kernel_size=%d ramdisk_size=%d second_size=%d" % (ks, rs, ss))
# Header v0 = 44 B; Kernel beginnt bei 44
kernel = data[44:44 + ks]
print("kernel erste 8B:", kernel[:8].hex())
if kernel[:2] == b"\x1f\x8b":
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    kdec = d.decompress(kernel)
    dtb = d.unused_data
    print("gzip: kernel=%d B, DTB=%d B" % (len(kdec), len(dtb)))
else:
    # Kein gzip: DTB direkt am Ende des Kernel-Blobs suchen (FDT magic d00dfeed)
    dtb = None
    pos = kernel.find(b"\xd0\x0d\xfe\xed")
    print("FDT-Magic im Kernel-Blob @", pos)
    if pos >= 0:
        dtb = kernel[pos:]
        print("DTB ab Magic: %d B" % len(dtb))
if not dtb:
    print("KEIN DTB gefunden")
    sys.exit(1)
for n in [b"pon", b"reboot-mode", b"mode-bootloader", b"bootloader", b"mode-fastboot", b"reboot_mode"]:
    idx = dtb.find(n)
    print("%-16s -> %s" % (n.decode(), "gefunden @%d" % idx if idx >= 0 else "NICHT gefunden"))
for n in [b"pon", b"reboot-mode"]:
    idx = dtb.find(n)
    if idx >= 0:
        print("--- Kontext %s ---" % n.decode())
        print(dtb[max(0, idx - 160): idx + 320])
