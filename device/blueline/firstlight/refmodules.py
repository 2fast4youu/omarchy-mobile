#!/usr/bin/env python3
"""Die Gadget-Module aus dem Referenz-Initramfs hierher holen.

Grund: der Kernel, den unsere v0-Bilder tragen, ist byte-identisch der
Distro-Kernel aus pmos-ref-build/ref/boot.img. Dessen Config
(config-postmarketos-qcom-sdm845.aarch64) baut USB_LIBCOMPOSITE, USB_F_NCM,
USB_F_ACM, U_ETHER, U_SERIAL und USB_CONFIGFS als =m. Ohne diese Module in der
Ramdisk scheitert `mkdir functions/ncm.usb0` — egal wie korrekt die
Gadget-Sequenz ist. Das Referenz-Initramfs traegt genau diese Module als
.ko.zst; wir holen sie entpackt und mit der aus modules.dep gelesenen
Schliessung, nicht abgeschrieben.

Benutzung:  ./refmodules.py [zielverzeichnis]   (Standard: /private/tmp/refmod)
"""
import os
import re
import tempfile
import struct
import subprocess
import sys

REF_IMG = os.environ.get(
    "REF_IMG", "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import newc  # noqa: E402  (eigener cpio-Leser, liest auch .zst-Ramdisk nach Entpacken)

# Was das Gadget mindestens braucht, ist keine Vermutung: es steht in
# modules.dep des Referenz-Initramfs. Wir lesen die Schliessung dort.
SEEDS = ("usb_f_ncm.ko.zst", "usb_f_acm.ko.zst", "usb_f_rndis.ko.zst")


def ramdisk_cpio(img, work):
    d = open(img, "rb").read()
    page = struct.unpack_from("<I", d, 40)[0] or 4096
    rs = struct.unpack_from("<I", d, 16)[0]
    off = 4096 + ((struct.unpack_from("<I", d, 8)[0] + page - 1) // page) * page
    raw = d[off:off + rs]
    if raw[:3] == bytes.fromhex("1f8b"):
        import gzip
        return gzip.decompress(raw)
    z = os.path.join(work, "ramdisk.zst")
    open(z, "wb").write(raw)
    return subprocess.run(["zstd", "-df", "-c", z], stdout=subprocess.PIPE,
                          check=True).stdout


def closure(dep_txt):
    """Schliessung ueber modules.dep: Namen, die das Gadget anlegt."""
    graph = {}
    for line in dep_txt.splitlines():
        if ":" not in line:
            continue
        target, _, rest = line.partition(":")
        graph[os.path.basename(target)] = [w for w in rest.split() if w]
    want, stack = set(), list(SEEDS)
    while stack:
        n = stack.pop()
        if n in want:
            continue
        want.add(n)
        stack.extend(os.path.basename(w) for w in graph.get(n, []))
    return want, graph


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/private/tmp/refmod"
    os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="refmod-")
    cpio_path = os.path.join(work, "ref.cpio")
    open(cpio_path, "wb").write(ramdisk_cpio(REF_IMG, work))
    entries = {e["name"]: e for e in newc.read_cpio(cpio_path)}
    moddir = sorted({n.rsplit("/", 1)[0] for n in entries
                     if n.startswith("usr/lib/modules/") and n.endswith("modules.dep")})
    if len(moddir) != 1:
        raise SystemExit("kein eindeutiges Modulverzeichnis im Referenz-Initramfs: %r" % moddir)
    base = moddir[0]
    dep = entries[base + "/modules.dep"]["content"].decode()
    need, graph = closure(dep)
    found = {os.path.basename(n): (n, e["content"])
             for n, e in entries.items() if n.endswith(".ko.zst")}
    staged = 0
    for name in sorted(need):
        if name not in found:
            raise SystemExit("Modul %s in modules.dep genannt, aber nicht im "
                             "Referenz-Initramfs (%s)" % (name, base))
        path, blob = found[name]
        z = os.path.join(work, name)
        open(z, "wb").write(blob)
        raw = subprocess.run(["zstd", "-df", "-c", z], stdout=subprocess.PIPE,
                             check=True).stdout
        assert raw[:4] == bytes.fromhex("7f454c46"), "%s enthaelt kein ELF" % path
        dest = os.path.join(out, name[:-4])           # .ko.zst -> .ko
        open(dest, "wb").write(raw)
        print("gestaged %-22s %8d B  Quelle %s" % (os.path.basename(dest), len(raw), path))
        staged += 1
    open(os.path.join(out, "modules.dep"), "w").write(dep)
    ent_built = entries.get(base + "/modules.builtin")
    if ent_built:
        open(os.path.join(out, "modules.builtin"), "wb").write(ent_built["content"])
    insmod_order = [n for n in ["libcomposite.ko.zst", "u_ether.ko.zst"]
                    + list(SEEDS) + ["u_serial.ko.zst"] if n in need]
    print("Schliessung: %d Module, Reihenfolge fuer insmod: %s" % (staged, " ".join(insmod_order)))
    print("Ziel: %s   (Kernel-Version aus dem Pfad: %s)"
          % (out, base.rsplit("/", 1)[-1]))


if __name__ == "__main__":
    main()
