#!/usr/bin/env python3
"""Liest ein AOSP-Boot-Image aus und BELEGT, wo die Sektionen wirklich liegen.

Kopf (little-endian): 0 magic(8) | 8 kernel_size | 12 kernel_addr |
16 ramdisk_size | 20 ramdisk_addr | 24 second_size | 28 second_addr |
32 tags_size | 36 tags_addr | 40 page_size | 44 os_version/header_version |
48 name(16) | 64 cmdline(512) | 576 id(32) | 608 extra_cmdline(1024)

Der Kopf behauptet Groessen; ob die Sektionen an den Offsets stehen, die sich
daraus ergeben, steht nicht drin. Dieses Werkzeug prueft das, indem es den
komprimierten Kernel-Strom bis zu seinem echten Ende verfolgt und den DTB
dahinter vermisst: endet der Strom zusammen mit dem DTB byte-genau an
kernel_size, ist append_dtb belegt und die ramdisk beginnt dort, wohin ein
Bootloader nach dem Kopf sucht. Exit 1 bei einem page_size-Feld, das keine
Seitengroesse sein kann, oder wenn die Sektionen nicht an den berechneten
Offsets liegen — genau die beiden Fehlerklassen, die diesen Bring-up blind
gemacht haben.

Nutze so:  unpack-bootimg.py <boot.img> [Zielverzeichnis]
"""
import os, struct, sys, zlib

FIELD = (("kernel_size", 8), ("kernel_addr", 12), ("ramdisk_size", 16),
         ("ramdisk_addr", 20), ("second_size", 24), ("second_addr", 28),
         ("tags_size", 32), ("tags_addr", 36), ("page_size", 40),
         ("os_version", 44))
NAME_OFF, CMDLINE_OFF, ID_OFF, EXTRA_OFF = 48, 64, 576, 608
GZIP, DTB, CPIO = b"\x1f\x8b\x08", b"\xd0\x0d\xfe\xed", b"070701"
ZSTD = b"\x28\xb5\x2f"  # die Referenz-Initramfs ist zstd-komprimiert
PAGE_CANDIDATES = (2048, 4096, 8192, 16384)


def text(blob, off, size):
    return blob[off:off + size].split(b"\0")[0].decode(errors="replace")


def is_page(n):
    return n and n >= 512 and not (n & (n - 1))


def gzip_span(blob, off):
    """(entpackte Groesse, verbrauchte Bytes) des gzip-Stroms ab off."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = d.decompress(blob[off:])
    return len(out), len(blob) - off - len(d.unused_data) - len(d.unconsumed_tail)


def section_base(blob):
    """Die erste Kandidatenseite, hinter der ein gepackter Kernel beginnt."""
    for cand in PAGE_CANDIDATES:
        if blob[cand:cand + 3] == GZIP:
            return cand
    return -1


def main(img, out=None):
    blob = open(img, "rb").read()
    if blob[:8] != b"ANDROID!":
        sys.exit(f"{img}: kein AOSP boot image (magic fehlt)")
    d = {name: struct.unpack_from("<I", blob, off)[0] for name, off in FIELD}
    page, problems = d["page_size"], []
    print(f"datei: {os.path.basename(img)}  {len(blob)} Bytes")
    for name, off in FIELD:
        print(f"  {name}@{off}: {d[name]} ({hex(d[name])})")
    print(f"  name@{NAME_OFF}: {text(blob, NAME_OFF, 16)!r}")
    print(f"  cmdline@{CMDLINE_OFF}: {text(blob, CMDLINE_OFF, 512)}")
    print(f"  id@{ID_OFF}: {blob[ID_OFF:ID_OFF + 20].hex()}")
    print(f"  extra_cmdline@{EXTRA_OFF}: {text(blob, EXTRA_OFF, 1024)!r}")
    if page and not is_page(page):
        problems.append(f"page_size-Feld = {page}: keine Seitengroesse (0 oder "
                        f"512/1024/2048/4096/…). Wer danach rechnet, sucht die "
                        f"ramdisk am falschen Offset")

    base = section_base(blob)
    print(f"  Sektionsanfang (gemessen): {base}")
    if base < 0:
        sys.exit("kein gepackter Kernel hinter dem Kopf gefunden — unbekanntes Layout")
    pad = page if is_page(page) else base
    end = base + d["kernel_size"]
    if blob[base:base + 3] == GZIP:
        raw_len, used = gzip_span(blob, base)
        print(f"  kernel-Strom: gzip, {used} Bytes komprimiert -> {raw_len} Bytes entpackt")
        after = base + used
        dtb_len = struct.unpack_from(">I", blob, after + 4)[0] if blob[after:after + 4] == DTB else 0
        if dtb_len:
            print(f"  DTB direkt dahinter bei {after}: {dtb_len} Bytes (append_dtb)")
        accounted = used + dtb_len
        print(f"  accounted {accounted} Bytes gegen kernel_size {d['kernel_size']} "
              f"({d['kernel_size'] - accounted} Bytes Rest)")
        if accounted != d["kernel_size"]:
            problems.append(f"kernel-Sektion schaetzt nicht exakt: Strom + DTB = "
                            f"{accounted}, kernel_size = {d['kernel_size']}")
    ram_off = base + d["kernel_size"]
    ram_pad_off = base + -(-d["kernel_size"] // pad) * pad

    MAGIC_KIND = {GZIP[:3]: "gzip", ZSTD: "zstd", CPIO: "cpio (unkomprimiert)"}
    k_plain = MAGIC_KIND.get(blob[ram_off:ram_off + 3])
    k_pad = MAGIC_KIND.get(blob[ram_pad_off:ram_pad_off + 3])
    print(f"  ramdisk bei {ram_off} (ohne Auffuellung): {k_plain or 'kein Magic'}; "
          f"bei {ram_pad_off} (Seitengrenze {pad}): {k_pad or 'kein Magic'}")
    # Massgeblich ist, was der Bootloader uebergibt: der rechnet den
    # ramdisk-Offset aus kernel_size und Seitengroesse und liest ab der
    # Seitengrenze. Das Referenzbild (sha256 ed2c225f...) legt die ramdisk
    # genau dort hin (zstd-Magic auf der 4096er-Grenze, 372 Nullbytes davor).
    # Liegt der Magic NUR mitten in der Seite, bekommt der Kernel den Blob
    # verschoben — genau der Fehler, der am 2026-10-28 um 22:14 als
    # "Initramfs unpacking failed" und Panic
    # "VFS: Unable to mount root fs on unknown-block(0,0)" auf dem Panel stand.
    if k_pad:
        ramdisk_at = ram_pad_off
        print(f"  Lage: seitenbuendig wie das Referenzbild; ramdisk ab {ramdisk_at}")
    elif k_plain:
        ramdisk_at = ram_off
        if ram_pad_off != ram_off:
            problems.append(
                f"ramdisk-Magic nur bei {ram_off}, das ist NICHT die Seitengrenze "
                f"({ram_pad_off}): der Bootloader uebergibt {ram_pad_off} + "
                f"{d['ramdisk_size']} Bytes und der Kernel sieht mittendrin "
                f"keinen Strom -> Initramfs unpacking failed, Panic unknown-block(0,0)")
    else:
        ramdisk_at = ram_off
        print("  Hinweis: die ramdisk traegt keinen known-Kompressions-Magic am "
              "Anfang (die postmarketOS-Distro schreibt so); geladen wird sie "
              "nach Groesse.")
    tail_end = ramdisk_at + d["ramdisk_size"] + d["second_size"]
    print(f"  Ende der Sektionen: {tail_end}, Datei: {len(blob)}, Schweif: {len(blob) - tail_end} Bytes")
    for p in problems:
        print(f"  ACHTUNG: {p}")
    if out:
        os.makedirs(out, exist_ok=True)
        ramdisk_ziel = ramdisk_at if d["ramdisk_size"] else ram_off
        for name, off in (("kernel", base), ("ramdisk", ramdisk_ziel), ("second", ram_pad_off)):
            if d[name + "_size"]:
                raw = blob[off:off + d[name + "_size"]]
                open(os.path.join(out, name), "wb").write(raw)
                print(f"  geschrieben: {os.path.join(out, name)} ({len(raw)} Bytes) bei {off}")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
