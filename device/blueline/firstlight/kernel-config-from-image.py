#!/usr/bin/env python3
"""Welche Config tragt der Kernel, der im zu flashenden Bild steckt?

Extrahiert den IKCONFIG-Einbettungsblock aus dem Kernel-Blob eines boot.img
(zlib, wie scripts/extract-ikconfig) und beantwortet die Frage, die ueber NCM
entheidet: sind USB_F_NCM / USB_F_ACM / TYPEC-* / NVMEM_REBOOT_MODE im
*laufenden* Kernel =y (dann braucht das modullose Initramfs nichts) oder =m
(dann fehlt jede .ko und mkdir functions/ncm.usb0 scheitert, egal wie korrekt
die Gadget-Sequenz ist). Liest mit open(), nie mit einem Zeilen praefixierenden
Leser.
"""
import re, struct, subprocess, sys, zlib

IKSTART = b"IKCFG_ST"
IKEND = b"IKCFG_ED"


def kernel_blob(img):
    """Kernel+SMTB/DTB-Blob eines Android-header-v0/v2 boot.img, ohne dem
    Kopf zu glauben: kernel_size lesen ist ok, der Blob *endet* dort."""
    d = open(img, "rb").read()
    page = struct.unpack_from("<I", d, 40)[0] or 4096
    page = 4096 if page < 512 else page          # v0: page_size-Feld ist 0
    ks = struct.unpack_from("<I", d, 8)[0]
    off = page                                    # erste Seite ist der Kopf
    return d[off:off + ks], d, page, ks


def ikconfig(blob):
    i = blob.find(IKSTART)
    if i < 0:
        return None
    j = blob.find(IKEND, i)
    if j < 0:
        return None
    raw = blob[i + len(IKSTART):j]
    for skip in (0, 1):                            # leading NUL padding
        try:
            return zlib.decompress(raw[skip:])
        except zlib.error:
            continue
    try:
        do = zlib.decompressobj()
        return do.decompress(raw)
    except zlib.error as err:
        return "ZLIB-FEHLER: %s" % err


def report(tag, img):
    blob, d, page, ks = kernel_blob(img)
    cfg = ikconfig(blob)
    print("== %s ==" % tag)
    print("   kernel_size %d B, Seite %d, Blob gzip-magic %s"
          % (ks, page, blob[:3].hex()))
    if cfg is None:
        print("   IKCONFIG: NICHT EINGEBETTET (CONFIG_IKCONFIG=n) -> Config des "
              "Baums ist nicht aus dem Bild beweisbar")
        return None
    if isinstance(cfg, str):
        print("  ", cfg); return None
    txt = cfg.decode("utf-8", "replace")
    print("   IKCONFIG: %d Bytes, first line %r" % (len(txt), txt.splitlines()[0][:60]))
    keys = ["CONFIG_IKCONFIG", "CONFIG_MODULES", "CONFIG_USB_CONFIGFS",
            "CONFIG_USB_LIBCOMPOSITE", "CONFIG_USB_F_NCM", "CONFIG_USB_F_ACM",
            "CONFIG_USB_F_RNDIS", "CONFIG_USB_CONFIGFS_NCM", "CONFIG_USB_CONFIGFS_ACM",
            "CONFIG_USB_DWC3", "CONFIG_USB_DWC3_QCOM", "CONFIG_TYPEC",
            "CONFIG_TYPEC_QCOM_PMIC", "CONFIG_TYPEC_UCSI", "CONFIG_TYPEC_MANAGER",
            "CONFIG_NVMEM_REBOOT_MODE", "CONFIG_QCOM_PON", "CONFIG_PSCI_POWER_OFF",
            "CONFIG_USB_NET_CDC_NCM", "CONFIG_USB_NET_RNDIS_HOST", "CONFIG_UNIX",
            "CONFIG_NET", "CONFIG_DEVTMPFS", "CONFIG_FS_CONFIGFS", "CONFIG_CIFS",
            "CONFIG_USB_ACM", "CONFIG_USB_SERIAL_QCOM_WHITEWISP", "CONFIG_QCOM_SMEM"]
    found = {}
    for k in keys:
        m = re.search(r"^%s=(.*)$" % re.escape(k), txt, re.M)
        found[k] = m.group(1) if m else "—(nicht gesetzt)"
    for k, v in found.items():
        print("   %-42s %s" % (k, v))
    modlines = [l for l in txt.splitlines() if l.endswith("=m")]
    print("   Module im laufenden Kernel ueberhaupt: %d" % len(modlines))
    return txt, found


want = ["CONFIG_USB_F_NCM", "CONFIG_USB_F_ACM", "CONFIG_USB_CONFIGFS",
        "CONFIG_USB_LIBCOMPOSITE", "CONFIG_TYPEC_QCOM_PMIC",
        "CONFIG_NVMEM_REBOOT_MODE", "CONFIG_USB_DWC3_QCOM"]

imgs = sys.argv[1:]
results = {}
for img in imgs:
    tag = img.split("/")[-2] if "/" in img else img
    r = report(tag, img)
    results[img] = r
    if r is None:
        continue
    txt, found = r
    need_mod = [k for k in want if found[k] == "m"]
    unset = [k for k in want if found[k].startswith("—")]
    print("   -> braucht als Modul geladen: %s" % (", ".join(need_mod) or "keine"))
    print("   -> gar nicht gesetzt        : %s" % (", ".join(unset) or "keine"))
    print("   -> NCM-Verdict: %s"
          % ("MODULFEHLEND im modullosen Initramfs — mkdir functions/ncm.usb0 scheitert"
             if found["CONFIG_USB_F_NCM"] == "m" else
             "EINGEBAUT (=y) — kein .ko noetig" if found["CONFIG_USB_F_NCM"] == "y"
             else "UNKLAR"))
    print()
