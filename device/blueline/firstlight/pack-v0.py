#!/usr/bin/env python3
"""v0-Boot-Image-Packer fuer ABOOT (Pixel 3 / blueline) — Layout gespiegelt.

Warum ein eigener Packer: unsre bisherigen Bilder tragen den Wert 2 im Feld bei
Offset 40.  Nach AOSP-layout (v0/v1/v2 identisch) steht dort page_size; die
distro-eigenen, bootenden Bilder haben dort 0 (= Default 2048) und ihre cmdline
bei Offset 64, also v0-Layout.  Ein value 2 als Seitengröße bedeutet: ABOOT
berechnet die Section-Offsets falsch, der Kernel laedt nie — und der
Bootloader landet nach wenigen Sekunden in Fastboot, ohne dass eine einzige
Kernel-Logzeile faellt.  Dieses Skript schreibt das v0-Feld fuer Feld, wie am
Referenzbild abgelesen, und prueft jede Zahl nach dem Schreiben nach.

Kopf-Felder (Bytes, little-endian, AOSP boot_img_hdr / v0):
   0 magic(8) | 8 kernel_size | 12 kernel_addr | 16 ramdisk_size | 20 ramdisk_addr
  24 second_size | 28 second_addr | 32 tags_size | 36 tags_addr | 40 page_size
  44 os_version | 48 name(16) | 64 cmdline(512) | 576 id(32) | 608 extra_cmdline(1024)
Danach: Padding auf die Ausrichtungsseite, dann kernel, ramdisk, second
(jeweils seitendig aufgefuellt).

Nutze so:
  pack-v0.py --kernel <kernel+dtb> --ramdisk <initramfs.cpio.gz> \
             --cmdline '...' --kernel-addr 0x8000 --ramdisk-addr 0x1000000 \
             --tags-addr 0x1000 --pagesize-field 0 --pagesize-align 2048 \
             [--reference <boot.img>] -o <boot.img>
"""
import argparse
import hashlib
import os
import struct
import sys

FIELDS = (
    ("kernel_size", 8), ("kernel_addr", 12), ("ramdisk_size", 16),
    ("ramdisk_addr", 20), ("second_size", 24), ("second_addr", 28),
    ("tags_size", 32), ("tags_addr", 36), ("page_size", 40),
    ("os_version", 44),
)
NAME_OFF, CMDLINE_OFF, ID_OFF, EXTRA_OFF = 48, 64, 576, 608
HEADER_BYTES = 1632  # 608 + 1024, danach Padding auf die Seite


def dword(blob, off):
    return struct.unpack_from("<I", blob, off)[0]


def build(args):
    kernel = open(args.kernel, "rb").read()
    ramdisk = open(args.ramdisk, "rb").read()
    second = open(args.second, "rb").read() if args.second else b""
    align = args.pagesize_align
    if align not in (512, 1024, 2048, 4096, 8192, 16384):
        sys.exit(f"Ausrichtung {align} ist keine gueltige Boot-Image-Seitengroesse")

    head = bytearray(b"\x00" * align)
    head[0:8] = b"ANDROID!"
    values = {
        "kernel_size": len(kernel), "kernel_addr": args.kernel_addr,
        "ramdisk_size": len(ramdisk), "ramdisk_addr": args.ramdisk_addr,
        "second_size": len(second), "second_addr": args.second_addr,
        "tags_size": args.tags_size, "tags_addr": args.tags_addr,
        "page_size": args.pagesize_field, "os_version": args.os_version,
    }
    for name, off in FIELDS:
        struct.pack_into("<I", head, off, values[name])
    head[NAME_OFF:NAME_OFF + 16] = args.name.encode()[:16].ljust(16, b"\0")
    cmd = args.cmdline.encode()
    if len(cmd) > 511:
        sys.exit(f"cmdline ist {len(cmd)} Bytes, das v0-Feld traegt max. 511")
    head[CMDLINE_OFF:CMDLINE_OFF + len(cmd) + 1] = cmd + b"\0"
    sha = hashlib.sha1()
    for blob in (kernel, ramdisk, second):
        sha.update(blob)
    head[ID_OFF:ID_OFF + 20] = sha.digest()
    extra = args.extra_cmdline.encode()
    head[EXTRA_OFF:EXTRA_OFF + len(extra) + 1] = extra + b"\0"

    def padded(blob):
        return blob + b"\xff" * (-len(blob) % align)

    if args.pad_sections:
        body = padded(kernel) + padded(ramdisk) + padded(second)
    else:
        # Spiegel-Modus (gemessen am Referenzbild, sha256 ed2c225f...): die
        # Sektionen liegen byte-auf-byte hintereinander, ohne Seiten-
        # Auffuellung. Nur der Kopf ist auf 4096 gepolstert, hinter der
        # ramdisk folgen 1693 Nullbytes. ABOOT nutzt die Groessen aus dem Kopf
        # und rechnet die Section-Offsets aus dem page_size-Feld — dieses Feld
        # ist dort 0, also gibt es fuer ABOOT keine Auffuellung, und beides
        # passt zusammen. Unsere alten Bilder polsterten auf 4096, schrieben
        # aber den header_version-Wert 2 in genau dieses Feld: ABOOT sucht die ramdisk dann an einem Offset, den
        # unsere Datei nicht liefert.
        body = kernel + ramdisk + second
    out = bytes(head) + body
    if args.tail_align:
        # Das Referenzbild endet auf einer 2048er-Grenze (1693 Nullbytes hinter
        # der ramdisk). Fuer ABOOT aendert die Auffuellung nichts, aber wer das
        # bekannt-gute Packing spiegelt, sollte es bis auf die Bytes spiegeln,
        # die er absichtlich aendert.
        out += b"\x00" * (-len(out) % args.tail_align)
    tmp = args.output + ".part"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, args.output)
    return len(out)


def verify(args, size):
    align = args.pagesize_align
    blob = open(args.output, "rb").read(align_read(args.output))
    problems = []
    if blob[:8] != b"ANDROID!":
        problems.append("magic fehlt")
    want = {
        "kernel_size": os.path.getsize(args.kernel),
        "kernel_addr": args.kernel_addr,
        "ramdisk_size": os.path.getsize(args.ramdisk),
        "ramdisk_addr": args.ramdisk_addr,
        "second_size": os.path.getsize(args.second) if args.second else 0,
        "second_addr": args.second_addr,
        "tags_size": args.tags_size,
        "tags_addr": args.tags_addr,
        "page_size": args.pagesize_field,
        "os_version": args.os_version,
    }
    for name, off in FIELDS:
        got = dword(blob, off)
        flag = "ok" if got == want[name] else f"ABWEICHEND (soll {want[name]})"
        print(f"  {name}@{off}: {got} ({hex(got)}) {flag}")
        if got != want[name]:
            problems.append(f"{name} geschrieben als {got}, gewollt {want[name]}")
    cmd = blob[CMDLINE_OFF:CMDLINE_OFF + 512].split(b"\0")[0].decode(errors="replace")
    print(f"  cmdline@{CMDLINE_OFF}: {cmd}")
    if cmd != args.cmdline:
        problems.append("cmdline nicht wie uebergeben")
    if args.reference:
        ref = open(args.reference, "rb").read(2048)
        print(f"  --- Vergleich zum Referenzbild {os.path.basename(args.reference)} ---")
        for name, off in FIELDS:
            g, r = dword(blob, off), dword(ref, off)
            if g != r:
                print(f"    {name}@{off}: wir {g} (0x{g:x}) | Referenz {r} (0x{r:x})")
                # Genau diese Klasse von Abweichung hat den ganzen Bring-up blind
                # gemacht: ein Wert im page_size-Feld, den niemand mit dem
                # bekannt-guten Bild verglichen hat. --strict-reference macht sie
                # zum Abbruch.
                if args.strict_reference:
                    problems.append(f"{name}@{off} weicht von der Referenz ab "
                                    f"(wir {g}, Referenz {r})")
        rcmd = ref[CMDLINE_OFF:CMDLINE_OFF + 512].split(b"\0")[0].decode(errors="replace")
        if rcmd != cmd:
            print(f"    cmdline unterscheidet sich:\n      Referenz: {rcmd}\n      wir:      {cmd}")
    expected = align
    for path in (args.kernel, args.ramdisk, args.second):
        if path:
            sz = os.path.getsize(path)
            expected += -(-sz // align) * align if args.pad_sections else sz
    if args.tail_align:
        expected = -(-expected // args.tail_align) * args.tail_align
    if size != expected:
        problems.append(f"Dateigroesse {size} != erwartet {expected}")
    print(f"  Dateigroesse: {size} Bytes (erwartet {expected})")
    if problems:
        sys.exit("Packen pruefgeschlagen: " + "; ".join(problems))
    print("Packen gepackt und nachgeprueft: alle Felder am Platz.")


def align_read(path):
    import os as _os
    return min(_os.path.getsize(path), 4096)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kernel", required=True, help="Kernel-Blob, DTB schon angehaengt")
    p.add_argument("--ramdisk", required=True, help="initramfs.cpio.gz")
    p.add_argument("--second", default=None)
    p.add_argument("--cmdline", required=True)
    p.add_argument("--extra-cmdline", default="")
    p.add_argument("--name", default="omamobile")
    p.add_argument("--kernel-addr", type=lambda s: int(s, 0), default=0x8000)
    p.add_argument("--ramdisk-addr", type=lambda s: int(s, 0), default=0x01000000)
    p.add_argument("--second-addr", type=lambda s: int(s, 0), default=0)
    p.add_argument("--tags-size", type=lambda s: int(s, 0), default=256)
    p.add_argument("--tags-addr", type=lambda s: int(s, 0), default=0x1000)
    p.add_argument("--os-version", type=lambda s: int(s, 0), default=0)
    p.add_argument("--pagesize-field", type=lambda s: int(s, 0), default=0,
                   help="was ins Feld page_size@40 geschrieben wird (die Distro schreibt 0)")
    p.add_argument("--pagesize-align", type=lambda s: int(s, 0), default=4096,
                   help="Kopf-Polsterung und Seitenweite (Referenzbild: 4096)")
    p.add_argument("--pad-sections", action="store_true",
                   help="Sektionen seitig auffuellen (Standard: wie die Distro "
                        "byte-auf-byte ohne Auffuellung)")
    p.add_argument("--tail-align", type=lambda s: int(s, 0), default=2048,
                   help="Dateiende auf diese Grenze auffuellen (Referenzbild: 2048; "
                        "0 schaltet die Auffuellung aus)")
    p.add_argument("--strict-reference", action="store_true",
                   help="jede Kopf-Feld-Abweichung vom --reference-Bild abbrechen lassen "
                        "(die cmdline bleibt frei, die aendern wir absichtlich)")
    p.add_argument("--reference", default=None, help="bekannt-gutes Bild zum Feldvergleich")
    p.add_argument("-o", "--output", required=True)
    args = p.parse_args()
    size = build(args)
    print(f"geschrieben: {args.output}")
    verify(args, size)
    with open(args.output, "rb") as f:
        print("sha256:", hashlib.sha256(f.read()).hexdigest())


if __name__ == "__main__":
    main()
