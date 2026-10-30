#!/usr/bin/env python3
"""Baut v0x aus v0ws Archiv: debugfs frueh, kein Phantom-Knopf, der modewert gemessen.

Drei Befunde, alle an der Quelle gemessen (Kernelbaum android-mainline/kernel-pmos,
2026-10-30 abends, nach dem v0w-Bau):

1. soft_connect als DATEI existiert in diesem Kernel nicht. grep -rn
   '"soft_connect"' ueber den ganzen Baum: 0 Dateien. Die drei Fundstellen im
   Kernel-Binary sind Kallsyms-Funktionsnamen (dwc3_gadget_soft_connect,
   dwc3_gadget_soft_disconnect, soft_connect_store). v0v und der v0w-Fallback
   schreiben eine Datei an, die der Kernel nie anlegt - daher war 'kein Knopf,
   Datei nicht gefunden' die erwartbare Antwort, nicht eine Ueberraschung.

2. real existiert als Datei der modus-Knopf: drivers/usb/dwc3/debugfs.c:1029
   setzt debugfs_create_file("mode", 0644, ...) unter
   debugfs_create_dir(dev_name(dwc->dev), usb_debug_root) (Zeile 1023), und der
   Ordner usb_debug_root = debugfs_create_dir("usb", NULL) entsteht
   bedingungslos in drivers/usb/common/common.c:422. CONFIG_USB_DWC3_DUAL_ROLE=y
   und CONFIG_DEBUG_FS=y stehen in android-mainline/kernel-pmos/.config.
   Der Pfad ist also /sys/kernel/debug/usb/<geraetename>/mode; der Geraetename
   wird NICHT angenommen - v0x sucht die Datei und meldet ihren Inhalt.

3. debugfs wurde nie vor der ersten Bind-Runde eingehaengt (die einzige mount-
   Zeile stand in v0w hinter der ersten Herzschlag-Serie und mitten in der
   Bind-Runde). v0x haengt es direkt nach dem PATH ein, vor jedem Bind.

Eingriffe (Anker durch Schnitt aus dem geladenen Archiv, nie abgetippt):
  A) Titel v0w -> v0x
  B) mount -t debugfs vor der ersten Zeile, die den Zaehlkanal liest
  C) Fallback auf den Phantompfad raus; ohne Fund heisst der Befund
     'kein Fund' und es wird nicht getestet
  D) MODEPFAD/MODENEUGEFUNDEN/MODE vor den Write-Zeilen, modepfad= und
     modewert= in beiden Beweiszeilen
  E) modewert im Herzschlag (derselbe echo, den v0w fuer debugfs= schrieb)
"""
from __future__ import annotations

import importlib.util
import os
import sys

Q, E, B, N = chr(34), chr(39), chr(92), chr(10)
I12 = " " * 12
HIER = os.path.dirname(os.path.abspath(__file__))

spec = importlib.util.spec_from_file_location("newc", os.path.join(HIER, "newc.py"))
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

# Am v0w-Bild gemesselle Abschlussfolgen (Zeile 74 Herzschlag, Zeile 371 Bind):
TRA = "tr " + E + B + "n" + E + " " + E + " " + E + ")"      # bis zum Paren
TRE = TRA + Q                                                 # Herzschlag:  ')"'
TRL = TRE + " > /dev/kmsg"                                     # Bindblock:   ')" > /dev/kmsg'


def lerne_anker(init):
    z = init.splitlines()
    titel = next(x for x in z if x.strip().startswith("echo " + E + "Omarchy Mobile first-light v0w"))
    pfad = next(x for x in z if x.strip().startswith("export PATH="))
    herz = next(x for x in z if "debugfs=$(ls /sys/kernel/debug" in x)
    fallback = next(x for x in z if x.strip().startswith('[ -n "$SC" ] || SC='))
    pruef = next(x for x in z if x.strip().startswith('test -w "$SC"; SCRCA=$?'))
    runde = next(x for x in z if "weicher-bind $rb:" in x and "scrca=$SCRCA" in x)
    spaeter = next(x for x in z if "spaeter 5s:" in x)
    assert init.count("mount -t debugfs") == 1, "mount-Zeilen: %d" % init.count("mount -t debugfs")
    return dict(titel=titel, pfad=pfad, herz=herz, fallback=fallback, pruef=pruef,
                runde=runde, spaeter=spaeter)


def umbau(init, a):
    text = init
    arbeit = []

    # A) Titel
    arbeit.append((a["titel"], a["titel"].replace("v0w", "v0x")))

    # B) debugfs vor allem, was den Zaehlkanal liest. Die mount-Zeile in der
    #    Runde bleibt stehen: haengt schon, zweiter mount schlaegt fehl, die 2
    #    Uhr 20 zeigt in der Fehlerausgabe, welcher Fall vorlag.
    arbeit.append((a["pfad"],
                   a["pfad"] + N + "# v0x: debugfs vor der ersten Bind-Runde (v0w haengte es erst"
                   + N + "# mitten in der Runde ein, die Herzschlaege davor waren dunkel)."
                   + N + "mount -t debugfs none /sys/kernel/debug 2>/dev/null || true"))

    # C) Kein Fallback mehr auf den Phantompfad.
    arbeit.append((a["fallback"],
                   I12 + '[ -n "$SC" ] || SC=""   # v0x: der v0w-Fallback war ein Phantom'))

    # D2) Die Beweiszeilen tragen das Messfeld.
    arbeit.append(("scrca=$SCRCA rc0=$sc0rc",
                   "scrca=$SCRCA modepfad=$MODENEUGEFUNDEN modewert=$MODW rc0=$sc0rc"))
    arbeit.append(("scrca=$SCRCA gefunden=$SZAHL, ",
                   "scrca=$SCRCA gefunden=$SZAHL modewert=$MODW, "))


    # D) Der modus-Knopf, gemessen an der Quelle: real, 0644, unter dem
    #    Geraetenamen in usb_debug_root. Der Name wird gesucht, nicht gesetzt.
    arbeit.append((a["pruef"],
                   a["pruef"] + N
                   + I12 + "MODEPFAD=$(find /sys/kernel/debug -name mode 2>/dev/null | head -2)"
                   + N + I12 + "MODENEUGEFUNDEN=$(printf %s \"$MODEPFAD\" 2>/dev/null | wc -l 2>/dev/null)"
                   + N + I12 + "MODE=$(printf %s \"$MODEPFAD\" 2>/dev/null | head -1)"
                   + N + I12 + "MODW=$( { cat \"$MODE\"; } 2>&1 ); MODWRC=$?"))

    # D2) Die Beweiszeilen tragen das Messfeld.
    arbeit.append(("scrca=$SCRCA rc0=$sc0rc",
                   "scrca=$SCRCA modepfad=$MODENEUGEFUNDEN modewert=$MODW rc0=$sc0rc"))
    arbeit.append(("scrca=$SCRCA gefunden=$SZAHL, ",
                   "scrca=$SCRCA gefunden=$SZAHL modewert=$MODW, "))

    # E) modewert im Herzschlag, am Ende derselben Zeile, die v0w schrieb.
    alt_herz = a["herz"]
    neu_herz = ("              echo \"debugfs=$(ls /sys/kernel/debug 2>/dev/null | " + TRA
                + " usb=$(ls /sys/kernel/debug/usb 2>/dev/null | " + TRA
                + " modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)\"")
    arbeit.append((alt_herz, neu_herz))

    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)

    offen, zu = text.count("("), text.count(")")
    print("  Bilanz nach dem Umbau: %d ( gegen %d )" % (offen, zu))
    assert offen == zu, "Paren-Bilanz verschoben: %d offen, %d zu" % (offen, zu)
    for nr, zeile in enumerate(text.splitlines(), 1):
        if not zeile.lstrip().startswith("echo"):
            continue
        inside = zeile[zeile.find(Q) + 1:zeile.rfind(Q)] if zeile.count(Q) >= 2 else ""
        if inside.count("(") != inside.count(")"):
            print("  not ok - Zeile %d: Echo-Kette %d ( gegen %d )"
                  % (nr, inside.count("("), inside.count(")")))
    return text


def haupt():
    if len(sys.argv) != 3:
        print("usage: patch-v0x.py <neu.cpio von v0w> <neu.cpio fuer v0x>", file=sys.stderr)
        return 2
    in_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(in_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    neben = aus_cpio + ".r"
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher = e["content"].decode()
        a = lerne_anker(vorher)
        text = umbau(vorher, a)
        assert "first-light v0x" in text, "neuer Panel-Titel fehlt"
        assert "first-light v0w" not in text, "alter Panel-Titel noch im Text"
        assert text.count("bDeviceState") == 0, "blinde Lesung zurueckgekehrt"
        assert text.count("mount -t debugfs") == 2, "mount-Zeilen %d, erwartet 2" % text.count("mount -t debugfs")
        assert '[ -n "$SC" ] || SC=""' in text, "Phantom-Fallback noch drin"
        assert "modewert=$MODW" in text and "modepfad=$MODENEUGEFUNDEN" in text, \
            "der modus-Bericht fehlt"
        assert text.count("done") == vorher.count("done"), \
            "done-Zaehlung veraendert (%d gegen %d)" % (text.count("done"), vorher.count("done"))
        assert text.count("; do") == vorher.count("; do"), \
            "Schleifenzahl veraendert (%d gegen %d)" % (text.count("; do"), vorher.count("; do"))
        assert "gefunden=$SZAHL" in text and "suche=$SCLISTE" in text, \
            "der Suchbericht fehlt in der Beweiszeile"
        assert "SCRCA=$?" in text, "die Beschreibbar-Pruefung fehlt"
        ks = [x for x in text.splitlines() if "test -w " in x]
        assert len(ks) == 1 and ks[0].lstrip().startswith("if ["), \
            "test -w: %d Zeilen, erwartet eine einzige, in ihrer Bedingung" % len(ks)
        assert text.isascii(), "Init enthaelt Nicht-ASCII (Panel ohne UTF-Konsole)"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    with open(neben, "wb") as offen:
        offen.write(blob)
    back = {e["name"]: e for e in newc.read_cpio(neben)}
    init = back["init"]["content"].decode()
    assert back["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert back["init"]["content"] == next(
        e["content"] for e in es if e["name"] == "init"), "round-trip nicht dicht"
    module = [n for n in back if n.startswith("usr/lib/modules/")]
    soll = len({e["name"] for e in es if e["name"].startswith("usr/lib/modules/")})
    assert len(module) == soll >= 5, "Module nach round-trip nicht vollstaendig: %d von %d" % (
        len(module), soll)
    with open(aus_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(aus_cpio, 0o644)
    print("patch-v0x: init %d B, %d Zeilen, Module %d, modewert-Bericht %d mal, mount-Zeilen %d"
          % (len(init), init.count(chr(10)), len(module),
             init.count("modewert=$MODW"), init.count("mount -t debugfs")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())

    # C2) erst jetzt: Der nackte test -w des Vorgaengers muss weg. Am ersten
    #     v0x-Bau gemessen blieb er unter dem bedingten stehen und schrieb
    #     SCRCA=9 (kein Fund) zu SCRCA=1 um - stumm, unterhalb jedes Beweises.
    #     Als eigener Schritt, weil der Fallback-Zeile ein Comment haengt und
    #     ein Zwei-Zeilen-Anker daran schon zweimal zerbrach (0 Fundstellen).
    arbeit.append((I12 + 'test -w "$SC"; SCRCA=$?' + N, ""))
