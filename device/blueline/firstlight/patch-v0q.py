#!/usr/bin/env python3
"""v0q-Bauplatz: Gadget-Module in die Ramdisk, Init lädt sie vor dem Gadget.

Wird von build-v0q.sh im Container aufgerufen (Argumente sind Container-Pfade):

    patch-v0q.py <v0p-erstes-firstlight.img> <modulverzeichnis> <v0p-new.cpio> <ziel.cpio>

Der Kernel im v0p-Bild ist byte-identisch der Distro-Kernel (gzip-Anteil,
sha256 7112decbddcbe235..., gegen pmos-ref-build/ref/boot.img gemessen). Seine
Config setzt die Gadget-Funktionen als Module. Ohne sie in der Ramdisk scheitert
`mkdir functions/ncm.usb0` - egal wie korrekt die Gadget-Sequenz ist. Deshalb:
Module aus dem Referenz-Initramfs (über refmodules.py, Schliessung aus dessen
modules.dep) ins Archiv, und init ruft insmod in Abhaengigkeitsreihenfolge vor
dem configfs-Mount. Geglaubt wird erst dem Zuruecklesen aus dem fertigen Bild.
"""
import hashlib
import re
import struct
import sys
import zlib

sys.path.insert(0, "/om/device/blueline/firstlight")
import newc  # noqa: E402

VERSION = "7.1.0-rc1-sdm845"
MODDIR = "usr/lib/modules/" + VERSION + "/kernel/drivers/usb/gadget"
ORDER = [
    ("libcomposite.ko", MODDIR + "/libcomposite.ko"),
    ("u_ether.ko", MODDIR + "/function/u_ether.ko"),
    ("usb_f_ncm.ko", MODDIR + "/function/usb_f_ncm.ko"),
    ("u_serial.ko", MODDIR + "/function/u_serial.ko"),
    ("usb_f_acm.ko", MODDIR + "/function/usb_f_acm.ko"),
    ("usb_f_rndis.ko", MODDIR + "/function/usb_f_rndis.ko"),
]
REF_IMG = "/ref/boot.img"

# Der Block, der in den Init gehoert. Abhaengigkeitsreihenfolge aus modules.dep
# des Referenz-Initramfs: libcomposite -> u_ether -> usb_f_ncm, u_serial ->
# usb_f_acm. busybox-insmod kann kein zstd und braucht kein modules.dep; es
# prueft den vermagic selbst gegen den laufenden Kernel.
BLOCK = '''# ---- Gadget-Module ----------------------------------------------------
# Der Kernel in diesem Bild ist der Distro-Kernel: sein gzip-Anteil ist
# byte-identisch zur Referenz. Dessen Config
# (config-postmarketos-qcom-sdm845.aarch64) setzt USB_LIBCOMPOSITE, U_ETHER,
# U_SERIAL, USB_F_NCM und USB_F_ACM als =m. Ohne libcomposite schlaegt schon
# das configfs-Mount fehl, ohne usb_f_ncm das mkdir functions/ncm.usb0.
# Pfad = Referenzpfad; unser Selbstbau-.config (=y) ist ein anderer Kernel.
MODDIR=/usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb/gadget
if [ -d /usr/lib/modules/7.1.0-rc1-sdm845 ]; then
    mark 'gadget-module-dir gefunden'
else
    mark 'KEIN /usr/lib/modules/7.1.0-rc1-sdm845 - Gadget-Module fehlen'
fi
for m in "$MODDIR/libcomposite.ko" "$MODDIR/function/u_ether.ko" \\
         "$MODDIR/function/usb_f_ncm.ko" "$MODDIR/function/u_serial.ko" \\
         "$MODDIR/function/usb_f_acm.ko"; do
    if insmod "$m" 2>/dev/null; then
        mark "modul $(basename "$m") geladen"
    else
        mark "modul $(basename "$m") FEHLER $?"
    fi
done
mark "moduli: $(ls /proc/modules 2>/dev/null | wc -l) geladen, usb_f_ncm $(grep -c usb_f_ncm /proc/modules 2>/dev/null)"

'''
ANCHOR = "mark 'usb gadget setup (reference sequence)'\n"


def kernel_blob(img):
    """Kernel+Begleit-DTB, wie kernel-blob-from-image.py ihn schneidet."""
    d = open(img, "rb").read()
    page = struct.unpack_from("<I", d, 40)[0] or 4096
    if page < 512:
        page = 4096              # v0-Kopf: page_size-Feld 0, packt auf 4096
    ks = struct.unpack_from("<I", d, 8)[0]
    return d[page:page + ks]


def gzip_prefix(blob):
    """Die Bytes des gzip-Stroms, real beendet - der DTB-Anhaengt dahinter ist
    bei uns anders (ramoops-Knoten) und darf den Vergleich nicht versauen."""
    do = zlib.decompressobj(16 + zlib.MAX_WBITS)
    n = 0
    while True:
        part = blob[n:n + (1 << 20)]
        if not part:
            raise SystemExit("gzip-Strom ohne EOF-Marker")
        try:
            do.decompress(part)
        except zlib.error:
            raise SystemExit("gzip-Strom abbricht bei %d B" % n)
        n += len(part)
        if do.eof:
            return blob[:n - len(do.unused_data)]


def already_done(out_cpio, modsrc):
    """Der Umbau ist idempotent: ein Archiv, das die Module bereits traegt und
    dessen Init den insmod-Block hat, wird nicht ein zweites Mal umgebaut."""
    try:
        ent = {e["name"]: e for e in newc.read_cpio(out_cpio)}
    except SystemExit:
        return False
    names = list(ent)
    if not names or names[-1] != "TRAILER!!!":
        return False
    if not any(n.endswith("/usb_f_ncm.ko") for n in names):
        return False
    init = ent["init"]["content"].decode("utf-8")
    return 'insmod "$m"' in init and "MODDIR=/usr/lib/modules/" in init


def main():
    src_img, modsrc, in_cpio, out_cpio = sys.argv[1:5]
    import os
    if os.path.isfile(out_cpio) and already_done(out_cpio, modsrc):
        for name, path in ORDER:
            src = os.path.join(modsrc, os.path.basename(path))
            ent = {e["name"]: e for e in newc.read_cpio(out_cpio)}
            if ent[path]["content"] != open(src, "rb").read():
                raise SystemExit("Archiv vorhanden, aber Modul weicht ab: " + path)
        print("Archiv bereits umgebaut (%d Eintraege) - Umbau uebersprungen, "
              "Module bytegleich mit %s" % (len(ent), modsrc))
        return

    # 1) Beweis, dass die Config-Ableitung zum Bild-Kernel gehoert.
    gz = gzip_prefix(kernel_blob(src_img))
    ref_gz = gzip_prefix(kernel_blob(REF_IMG))
    if hashlib.sha256(gz).hexdigest() != hashlib.sha256(ref_gz).hexdigest():
        raise SystemExit("Kernel-gzip weicht von der Referenz ab - Config-Urteil "
                         "waere fuer diesen Kernel unbewiesen")
    print("Kernel-gzip identisch zur Referenz: %d B, sha256 %s"
          % (len(gz), hashlib.sha256(gz).hexdigest()[:16]))

    es = newc.read_cpio(in_cpio)
    ent = {e["name"]: e for e in es}
    if "init" not in ent or not ent["init"].get("content"):
        raise SystemExit("init ohne Inhalt im Archiv")

    # 2) Module einsetzen: Pfad = Referenzpfad, 0644 root, ohne .zst.
    for name, path in ORDER:
        blob = open("/m/" + name, "rb").read()
        assert blob[:4] == bytes.fromhex("7f454c46"), name + " ist kein ELF"
        vm = re.search(rb"vermagic=([0-9.\-A-Za-z_]+)", blob)
        assert vm, name + " ohne vermagic"
        assert vm.group(1).decode().startswith(VERSION), \
            "%s: vermagic %s != laufender Kernel %s" % (name, vm.group(1).decode(), VERSION)
        old = ent.get(path)
        if old is None:
            # neues Archivglied: dieselbe Form, die read_cpio zurueckgibt
            # ({"meta": {Feld: int}, "name", "content"}), ino eindeutig hoch.
            meta = {"ino": 0x00520000 + len(es), "mode": 0o100644, "uid": 0,
                    "gid": 0, "nlink": 1, "mtime": 0, "datasize": len(blob),
                    "devmajor": 0, "devminor": 0, "rdevmajor": 0,
                    "rdevminor": 0, "namesize": len(path) + 1, "check": 0}
            entry = {"meta": meta, "name": path, "content": blob}
            es.insert(len(es) - 1, entry)          # direkt vor TRAILER!!!
            ent[path] = entry
        else:
            old["content"] = blob
            old["meta"]["datasize"] = len(blob)
        assert ent[path]["meta"]["mode"] & 0o777 == 0o644, "Modus nicht 0644: " + path

    init = ent["init"]["content"].decode("utf-8")
    if "insmod" in init:
        raise SystemExit("Modulblock bereits im Init - nicht zweimal umbauen")
    if init.count(ANCHOR) != 1:
        raise SystemExit("Anker fuer den Modulblock nicht eindeutig: %d" % init.count(ANCHOR))
    init = init.replace(ANCHOR, BLOCK + ANCHOR, 1)

    # 3) Reihenfolge im fertigen Init-Text: Module vor configfs-Mount, dieser
    #    vor den Funktions-Mkdirs. Die Mkdirs selbst laufen ohne 2>/dev/null;
    #    ihr Fehler war im Kernel-Log sichtbar, nur hat niemand dort gelesen.
    lines = init.splitlines()
    def first(needle):
        hits = [i for i, l in enumerate(lines) if needle in l]
        assert hits, "felt nach Umbau: " + needle
        return hits[0]
    a = first('insmod "$m"')
    b = first('mount -t configfs -o nodev,noexec,nosuid')
    c = first('functions/$netfunc')
    d = first('functions/acm.GS0')
    assert a < b < c < d, "Reihenfolge insmod -> configfs -> ncm -> acm nicht erfuetzt: %r" % [a, b, c, d]
    assert init.isascii(), "Init hat Nicht-ASCII-Bytes"
    ent["init"]["content"] = init.encode("utf-8")

    blob = newc.emit(es)
    open("/tmp/q.cpio", "wb").write(blob)
    back = {e["name"]: e for e in newc.read_cpio("/tmp/q.cpio")}
    names = list(back)
    assert names[-1] == "TRAILER!!!", names[-3:]
    for name, path in ORDER:
        assert path in back, "Modul nach emit nicht rundgelesen: " + path
        assert back[path]["content"] == open("/m/" + name, "rb").read()
        assert back[path]["meta"]["mode"] & 0o777 == 0o644
    assert back["init"]["content"].decode("utf-8") == init
    open(out_cpio, "wb").write(blob)
    print("Archiv %d Eintraege, %d Module eingebettet, Init %d Zeichen"
          % (len(names), len(ORDER), len(init)))


if __name__ == "__main__":
    main()
