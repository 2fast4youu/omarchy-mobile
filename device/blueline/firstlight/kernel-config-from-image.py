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
import hashlib
import re
import struct
import subprocess
import sys
import zlib

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


def report(tag, img, expect=None):
    blob, d, page, ks = kernel_blob(img)
    cfg = ikconfig(blob)
    print("== %s ==" % tag)
    print("   kernel_size %d B, Seite %d, Blob gzip-magic %s"
          % (ks, page, blob[:3].hex()))
    if expect:
        got = hashlib.sha256(open(img, "rb").read()).hexdigest()
        good = got == expect
        print("   Bild-sha256 gegen Vorgabe %s: %s"
              % (expect[:16], "TREFFER" if good else "ABWEICHEND " + got))
        if not good:
            raise SystemExit("Bild hat nicht die erwartete sha256")
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

# Optionale Vorgabe: erwartete sha256 des fertigen Bildes, gemessen am
# zurueckgelesenen Bild. Ein Rezept, das seinen eigenen/hash-Pfad haelt, ist ein
# Leser mehr, der nicht auf den Builder vertraut - und die Groesse bleibt nicht
# als Zahl in einem Shellskript stehen, die niemand nachmisst.
argv = list(sys.argv[1:])
expect, imgs = None, []
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--expect-sha256":          # beide Schreibweisen, damit ein
        expect = argv[i + 1]; i += 2    #Uberlauf nicht als Bilddatei endet
    elif a.startswith("--expect-sha256="):
        expect = a.split("=", 1)[1]; i += 1
    else:
        imgs.append(a); i += 1
if expect and not imgs:
    raise SystemExit("--expect-sha256 ohne Bildpfad: es wird nichts gepueft")
results = {}
for img in imgs:
    tag = img.split("/")[-2] if "/" in img else img
    r = report(tag, img, expect)
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
