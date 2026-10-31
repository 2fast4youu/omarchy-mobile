#!/usr/bin/env python3
"""v0y -> v0z, als EIN Durchgang ueber das geladene v0y-Archiv.

Drei Befunde, alle gemessen, keiner gefolgert:

1. DER KNOPF IST REAL, aber ein Sysfs-Attribut der UDC-Klasse, kein debugfs-
   Knoten. Gregors Panel-Ablesung vom 31.10. listete soft_connect im Feld
   udcdateien= (das ist die Liste von /sys/class/udc/<udc>/). Am Quelltext:
   drivers/usb/gadget/udc/core.c:1784 DEVICE_ATTR_WO(soft_connect), im
   Attribut-Feld Zeile 1845. Die Worte des Schreibhandlers (Zeile 1750ff) sind
   'connect' und 'disconnect' (sysfs_streq), alles andere gibt -EINVAL; ohne
   gebundenes Gadget gibt es -EOPNOTSUPP mit der Kernelmeldung 'soft-connect
   without a gadget driver'. v0v und v0w drueckten ein Phantom im debugfs, und
   der Schreiber in v0vs Fallback haette '1' geschrieben, was -EINVAL ist.

2. DAS GADGET FEHLT WAHRSCHEINLICH: der Herzschlag meldet gadgetordner= und
   gebunden= leer, also findet die Nachbind-Runde von v0s kein Gadget und
   laeuft an der Platzhalterzeile durch ('[ -e "$g/UDC" ] || continue'), ohne
   je eine Beweiszeile zu drucken. Die Anlage wartet nur 30 s auf den UDC
   (Zeile 172, von der Referenz uebernommen, die bei 1.734 s bindet) und
   ueberspringt dann alles.

3. DIE ANTWORT IST SCHON AUF DEM GERAET, aber nicht auf dem Panel: die fruehen
   Marks stehen in /run/steps.log, die Herzschlagzeile 'letzter Schritt:' zeigt
   jedoch nur die letzte Zeile, und die schreibt der dmesg-Block bei 42 s.

Deshalb, in dieser Reihenfolge:
  A  Titel v0y -> v0z (ein Foto muss den Stand nennen)
  B  drei Herzschlagzeilen DAZU (nichts wird ersetzt): die Haengelifste aus
     /proc/self/mountinfo, der Gadget-und-Controllerestand, und die letzten
     sechs Zeilen der Schritt-Log. Die vorhandene 'letzter Schritt:'-Zeile
     bleibt stehen, die Messung bleibt also erhalten und wird nur erweitert.
  C  eine EIGENE Runde DAZU (die v0s-Runde bleibt unangetastet): abwarten,
     Haengen.pruefen und nachhaengen, das Gadget anlegen WENN KEINS DA IST
     (dieselbe Folge wie weiter oben, jeder Rueckgabewert notiert), binden,
     dann 'connect' auf den echten Pfad, und das Ergebnis in die Schritt-Log,
     die der Herzschlag vorliest.

Eingefuegt statt ersetzt, wo es geht: ein Ersatz, der eine vorhandene Messung
stum macht, war dreimal die Ursache eines Laufs, der zu spaet auffiel.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

TITEL_AN = "first-light v0y - RAM only"
TITEL_NEU = "first-light v0z - RAM only"

# Anker: eindeutige Teile aus dem geladenen Archiv, nie aus der Erinnerung.
ANKER_HERZ = "modewert=$(cat $(find /sys/kernel/debug -name mode"
ANKER_DROPBEAR = "mkdir -p /etc/dropbear"
CFS = "/sys/kernel/config/usb_gadget"


def einrueckung(zeile: str) -> str:
    return zeile[:len(zeile) - len(zeile.lstrip())]


def einzige(text: str, teil: str) -> str:
    treffer = [z for z in text.splitlines() if teil in z]
    assert len(treffer) == 1, "Anker %r: %d Fundstellen, erwartet 1" % (teil[:40], len(treffer))
    return treffer[0]


def herzschlag_zeilen(einr: str) -> str:
    """Die drei neuen Messzeilen, in derselben Einrueckung wie die Nachbarzeile.

    Jeder Leser haelt sein Ziel in der Hand (Dateiname oder </dev/null): eine
    leere Kommandosubstitution haette cat ohne Argument gelesen lassen, und die
    Standardeingabe der PID 1 ist die Konsole (am Pty gemessen, v0y-Grund).
    """
    Z = []
    Z.append('echo ' + chr(34) + "haengt: debugfs=$(grep -c ' - debugfs ' /proc/self/mountinfo)"
             " configfs=$(grep -c ' - configfs ' /proc/self/mountinfo)"
             " modus=$(cat /sys/kernel/debug/usb/*/mode </dev/null 2>&1)" + chr(34))
    Z.append('echo ' + chr(34) + "gadget: ordner=$(ls " + CFS + " 2>/dev/null | tr '\\n' ' ')"
             " udcGadget=$(readlink /sys/class/udc/*/gadget 2>/dev/null)"
             " is_active=$(cat /sys/class/udc/*/is_active </dev/null 2>&1)"
             " speed=$(cat /sys/class/udc/*/current_speed </dev/null 2>&1)"
             " netz=$(ls /sys/class/net 2>/dev/null | tr '\\n' ' ')" + chr(34))
    Z.append('echo ' + chr(34) + "schritte: $(tail -6 /run/steps.log 2>/dev/null | tr '\\n' '|')" + chr(34))
    return "\n".join(einr + z for z in Z)


def runde_text() -> str:
    q = chr(34)
    k = "\n"
    Zeilen = [
        "# --- v0z-Runde: das Gadget anlegen, wenn der spaete UDC es verpasst hat ---",
        "# Grund, gemessen: der Herzschlag meldet gadgetordner= und gebunden= leer, und",
        "# die v0s-Runde findet deshalb kein Gadget (ihr Platzhalter laeuft ohne",
        "# Beweiszeile durch). Die Anlage oben wartet nur 30 s auf den UDC. Diese Runde",
        "# legt an, WENN NICHTS DA IST, und drueckt den echten Knopf: am Panel als",
        "# udcdateien= abgelesen, am Quelltext als DEVICE_ATTR_WO gemessen",
        "# (drivers/usb/gadget/udc/core.c:1784), mit den Worten 'connect' und",
        "# 'disconnect' (Zeile 1763/1768) und -EOPNOTSUPP ohne gebundenes Gadget",
        "# (Zeile 1753ff). Ihr Ergebnis geht in die Schritt-Log, die der Herzschlag",
        "# vorliest: das Panel ist bei ausbleibender Enumeration das einzige Lesegeraet.",
        "(",
        "    zs=0",
        "    while [ \"$zs\" -lt 20 ]; do",
        "        sleep 15",
        "        zs=$((zs + 1))",
        "        mkdir -p /sys/kernel/debug 2>/dev/null",
        "        mount -t debugfs none /sys/kernel/debug 2>/dev/null; dfrc=$?",
        "        mkdir -p /sys/kernel/config 2>/dev/null",
        "        mount -t configfs -o nodev,noexec,nosuid configfs /sys/kernel/config 2>/dev/null; cfrc=$?",
        "        udc=$(ls /sys/class/udc 2>/dev/null | head -1)",
        "        " + q + "akt=v0z runde $zs bei $(cut -d. -f1 /proc/uptime)s: debugfsrc=$dfrc configfsrc=$cfrc udc=${udc:-KEINER}" + q,
        "        if [ ! -e " + q + CFS + "/g1" + q + " ]; then",
        "            mkdir " + q + CFS + "/g1" + q + " 2>/dev/null; g1rc=$?",
        "            echo 0x18D1 > " + q + CFS + "/g1/idVendor" + q + " 2>/dev/null",
        "            echo 0xD002 > " + q + CFS + "/g1/idProduct" + q + " 2>/dev/null",
        "            mkdir -p " + q + CFS + "/g1/strings/0x409" + q + " 2>/dev/null",
        "            echo " + chr(39) + "Omarchy Mobile" + chr(39) + " > " + q + CFS + "/g1/strings/0x409/manufacturer" + q + " 2>/dev/null",
        "            echo " + chr(39) + "omamobile-blueline" + chr(39) + " > " + q + CFS + "/g1/strings/0x409/serialnumber" + q + " 2>/dev/null",
        "            echo " + chr(39) + "Pixel 3 (blueline)" + chr(39) + " > " + q + CFS + "/g1/strings/0x409/product" + q + " 2>/dev/null",
        "            nf=ncm.usb0",
        "            mkdir " + q + CFS + "/g1/functions/$nf" + q + " 2>/dev/null || nf=rndis.usb0",
        "            mkdir -p " + q + CFS + "/g1/configs/c.1/strings/0x409" + q + " 2>/dev/null",
        "            echo " + chr(39) + "USB network" + chr(39) + " > " + q + CFS + "/g1/configs/c.1/strings/0x409/configuration" + q + " 2>/dev/null",
        "            ln -s " + q + CFS + "/g1/functions/$nf" + q + " " + q + CFS + "/g1/configs/c.1" + q + " 2>/dev/null",
        "            mkdir " + q + CFS + "/g1/functions/acm.GS0" + q + " 2>/dev/null",
        "            ln -s " + q + CFS + "/g1/functions/acm.GS0" + q + " " + q + CFS + "/g1/configs/c.1" + q + " 2>/dev/null",
        "            akt=" + q + "$akt | g1 NEU angelegt g1rc=$g1rc funktion=$nf knoepfe=$(ls " + CFS + "/g1/functions 2>/dev/null | tr '\\n' ' ')" + q,
        "        else",
        "            akt=" + q + "$akt | g1 war da: $(ls " + CFS + " 2>/dev/null | tr '\\n' ' ')" + q,
        "        fi",
        "        gebunden=$(cat " + q + CFS + "/g1/UDC" + q + " </dev/null 2>/dev/null)",
        "        if [ -z " + q + "$gebunden" + q + " ] && [ -n " + q + "$udc" + q + " ]; then",
        "            btext=$( { echo " + q + "$udc" + q + " > " + q + CFS + "/g1/UDC" + q + "; } 2>&1 ); brc=$?",
        "            akt=" + q + "$akt | binden rc=$brc text=${btext:-ohne}" + q,
        "        else",
        "            akt=" + q + "$akt | gebunden=${gebunden:-leer}" + q,
        "        fi",
        "        SC=$(ls /sys/class/udc/*/soft_connect 2>/dev/null | head -1)",
        "        gebunden=$(cat " + q + CFS + "/g1/UDC" + q + " </dev/null 2>/dev/null)",
        "        if [ -n " + q + "$SC" + q + " ] && [ -n " + q + "$gebunden" + q + " ]; then",
        "            stext=$( { echo connect > " + q + "$SC" + q + "; } 2>&1 ); src=$?",
        "            sleep 5",
        "            akt=" + q + "$akt | connect rc=$src text=${stext:-ohne} pfad=$SC state=$(cat /sys/class/udc/*/state </dev/null 2>&1) netz=$(ls /sys/class/net 2>/dev/null | tr '\\n' ' ')" + q,
        "        else",
        "            akt=" + q + "$akt | Knopf nicht gedrueckt pfad=${SC:-KEINER} gebunden=${gebunden:-leer}" + q,
        "        fi",
        "        for iface in usb0 eth0 ncm0; do",
        "            ifconfig " + q + "$iface" + q + " 172.16.42.1 2>/dev/null",
        "        done",
        "        echo " + q + "[$(cut -d. -f1 /proc/uptime)s] step: $akt" + q + " >> /run/steps.log 2>/dev/null",
        "        echo " + q + "omamobile-blueline: $akt" + q + " > /dev/kmsg",
        "    done",
        ") &",
    ]
    return k.join(Zeilen)


def umbau(text: str) -> str:
    arbeit = []
    arbeit.append((einzige(text, TITEL_AN), einzige(text, TITEL_AN).replace("v0y", "v0z")))
    herz = einzige(text, ANKER_HERZ)
    arbeit.append((herz, herz + "\n" + herzschlag_zeilen(einrueckung(herz))))
    arbeit.append((einzige(text, ANKER_DROPBEAR), runde_text() + "\n" + einzige(text, ANKER_DROPBEAR)))

    for nr, (alt, neu) in enumerate(arbeit, 1):
        n = text.count(alt)
        print("  Schritt %d: %d Fundstelle(n), %d Zeichen Anker" % (nr, n, len(alt)))
        assert n == 1, "Schritt %d: %d Fundstellen, erwartet 1" % (nr, n)
        text = text.replace(alt, neu, 1)
        assert text.count(neu) >= 1, "Schritt %d: Ersatz danach nicht im Text" % nr

    # Klassenpruefung: jeder Zeilen-Leser in den neuen Zeilen haelt ein Ziel
    # in der Hand. Eine leere Kommandosubstitution ist kein Fehlerfall, den die
    # Shell abfängt, sondern die Standardeingabe = die Konsole der PID 1.
    blind = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        for leser in ("cat ", "tail ", "head ", "wc ", "grep ", "readlink "):
            for teil in zeile.split("$(")[1:]:
                if teil.strip().startswith(leser.strip() + " $") or teil.strip().startswith(leser.strip() + ")"):
                    blind.append((nr, leser.strip()))
    if blind:
        print("  nicht ok - Leser ohne Argument in Zeile(n): %s" % sorted({b[0] for b in blind}))
    offen, zu = text.count("("), text.count(")")
    print("  Bilanz nach dem Umbau: %d ( gegen %d )" % (offen, zu))
    assert offen == zu, "Paren-Bilanz verschoben: %d offen, %d zu" % (offen, zu)
    assert text.isascii(), "Init traegt Nicht-ASCII (Panel ohne UTF-Konsole)"
    assert text.count("echo connect > ") == 1, "das connect-Wort steht %d mal, erwartet 1" % text.count("echo connect > ")
    assert text.count("soft_connect") >= 2, "der echte Pfad ist nicht zweimal im Text (Suche und Runde)"
    return text


def haupt() -> int:
    if len(sys.argv) != 3:
        print("usage: baue-v0z-umbau.py <new.cpio von v0y> <new.cpio fuer v0z>", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    vorher = {}
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        vorher = dict((x["name"], x["content"]) for x in es)
        text = umbau(e["content"].decode())
        assert TITEL_NEU in text and "first-light v0y" not in text, "Panel-Titel nicht umgestellt"
        assert "haengt: debugfs=$(grep" in text, "die Haengelifste fehlt"
        assert "schritte: $(tail -6 /run/steps.log" in text, "die Schritt-Vorlese fehlt"
        assert "letzter Schritt: $(tail -1 /run/steps.log" in text, "die vorhandene Messung ist weg"
        assert "gadget: ordner=$(" in text, "der Gadgetezustand fehlt"
        assert "v0z-Runde" in text, "die v0z-Runde fehlt"
        # Die neue Runde enthaelt zwei Schleifenenden (das while und das
        # iface-Schleifchen), also sind zwei done mehr. Der fruehere Punkt
        # fordererte +1 und scheiterte an der eigenen Zaehlung, gemessen: 26
        # gegen erwartet 25. Gezahlt wird die Differenz, nicht die Zahl im Kopf.
        mehr = text.count("done") - vorher["init"].decode().count("done")
        assert mehr == 2, "done-Differenz %d, erwartet 2 (while und for in der neuen Runde)" % mehr
        assert text.count("; do") - vorher["init"].decode().count("; do") == 2, \
            "Schleifenkoepfe: zwei erwartet in der neuen Runde"
        e["content"] = text.encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as offen:
        offen.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    assert zurueck["init"]["meta"]["mode"] & 0o111, "init nach emit nicht ausfuehrbar"
    assert zurueck["init"]["content"] == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip nicht dicht"
    modul = [n for n in zurueck if n.startswith("usr/lib/modules/")]
    soll = len({e["name"] for e in es if e["name"].startswith("usr/lib/modules/")})
    assert len(modul) == soll >= 5, "Module nach round-trip unvollstaendig: %d von %d" % (len(modul), soll)
    with open(aus_cpio, "wb") as offen:
        offen.write(blob)
    os.chmod(aus_cpio, 0o644)
    init = zurueck["init"]["content"].decode()
    print("baue-v0z: init %d B, %d Zeilen, Module %d, neue Zeilen %d, connect-Wort %d mal"
          % (len(init), init.count(chr(10)), len(modul),
             init.count(chr(10)) - vorher["init"].decode().count(chr(10)),
             init.count("echo connect > ")))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
