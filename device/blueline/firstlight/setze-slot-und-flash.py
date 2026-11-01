#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M1.4: Slot neu stellen, boot_a mit dem eigenen Bild, normal starten (kein RAM).

Warum Fastboot und kein Partition-Write: der Retry-Zaehler liegt nicht in misc.
In der ganzen 1-MiB-Partition stehen genau zehn Nicht-Null-Bytes — 'theme-dark'
bei 2048, ein Rest vom Recovery-Theme (gemessen an der Sicherung von 21:58,
sha f5f22730aa58099d). Was ABOOT an Zaehlern haelt, liegt ausserhalb jeder
Partition und ist von der laufenden Shell nicht zu lesen. Der einzige belegte
Hebel ist Fastboot; --set-active=a war der Fix fuer Wurzel #11.

Bedingung vor jedem Write (Gregors Regel): die Sicherung von boot_a muss da sein,
mit gepruefter Groesse und geprueftem sha gegen das Manifest. Ohne sie bricht
dieses Skript, bevor es irgendetwas schreibt.

Aufruf:  python3 setze-slot-und-flash.py [bild] [--trocken]
"""
import hashlib
import os
import re
import socket
import subprocess
import sys
import time

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
SERIAL = "PIXEL3-SERIAL"
HIER = os.path.dirname(os.path.abspath(__file__))
BILD = "/Users/gregor/hermes-workspace/images/fl-v0af/firstlight.img"
BILD_SHA = "f097ef0f9a1a858a15d72aad023be27f9a02e419116d25c580d99fe86d1a2c9d"
SICHERUNG = "/Users/gregor/hermes-workspace/backups/blueline-2026-11-01"
MANIFEST = os.path.join(HIER, "evidence", "kalibrier")
TELEFON = ("172.16.42.1", 23)
BELEG = []

for arg in sys.argv[1:]:
    if arg == "--trocken":
        TROCKEN = True
    else:
        BILD = arg
TROCKEN = globals().get("TROCKEN", False)


def notiz(m):
    line = time.strftime("%H:%M:%S ") + m
    print(line, flush=True)
    BELEG.append(line)


def fb(*args, frist=30):
    try:
        p = subprocess.run([FB, "-s", SERIAL] + list(args), capture_output=True,
                           text=True, timeout=frist)
        out = ((p.stdout or "") + (p.stderr or "")).replace("\r", "")
    except subprocess.TimeoutExpired:
        return "FESTGEFAHREN nach %ds" % frist
    for z in out.splitlines():
        if z.strip():
            BELEG.append("  fb " + " ".join(args) + " -> " + z.strip())
    return out


def state():
    """Die vier A/B-Werte, mit Leerzeichen-Toleranz (fastboot druckt 'x: a')."""
    antwort = fb("getvar", "all", frist=20)
    fund = {}
    for schl in ("current-slot", "slot-retry-count:a", "slot-retry-count:b",
                 "slot-unbootable:a", "slot-unbootable:b"):
        m = re.search(re.escape(schl) + r": *(\S+)", antwort)
        fund[schl] = m.group(1) if m else "NICHT GELESEN"
    notiz("A/B-Zustand: " + "  ".join("%s=%s" % (k, v) for k, v in fund.items()))
    return fund


def offen():
    try:
        s = socket.create_connection(TELEFON, timeout=4)
        s.close()
        return True
    except OSError:
        return False


def sicherung_pruefen():
    """Grösse und sha der boot_a-Sicherung gegen das neueste Manifest.

    Die Datei liegt erst im evidence-Ordner und wird spaeter in den Sicherungs-
    ordner verschoben (56 MB-images hoeren nicht ins Repo). Deshalb suchen beide
    Orte, und Beglaubigung heisst: Groesse und sha stimmen mit dem Manifest ueberein.
    """
    name = "kalibrier-boot_a.bin"
    pfade = [os.path.join(SICHERUNG, name), os.path.join(MANIFEST, name)]
    kandidaten = sorted(f for f in os.listdir(MANIFEST) if f.startswith("manifest-"))
    fund = [p for p in pfade if os.path.exists(p)]
    if not fund or not kandidaten:
        notiz("KEINE Sicherung (%s) oder kein Manifest — Write bleibt aus" % ", ".join(pfade))
        return False
    mit = open(os.path.join(MANIFEST, kandidaten[-1]), encoding="utf-8").read()
    m = re.search(re.escape(name) + r"\s+(\d+) B Klar\s+dicht\s+sha ([0-9a-f]{16})", mit)
    if not m:
        notiz("Manifest %s fuehrt %s nicht als dicht — Write bleibt aus"
              % (kandidaten[-1], name))
        return False
    groesse, sha_kurz = int(m.group(1)), m.group(2)
    for pfad in fund:
        wirklich = os.path.getsize(pfad)
        sha_wirklich = hashlib.sha256(open(pfad, "rb").read()).hexdigest()
        notiz("Sicherung %s: Manifest %d B sha %s, Datei %d B sha %s (%s)"
              % (name, groesse, sha_kurz, wirklich, sha_wirklich[:16], pfad))
        if wirklich == groesse and sha_wirklich.startswith(sha_kurz):
            notiz("Sicherung beglaubigt, Write ist erlaubt")
            return True
    notiz("keine Sicherung passt zum Manifest — Write bleibt aus")
    return False


def main():
    notiz("=== M1.4: Slot setzen, boot_a fuellen, normal starten ===")
    if not os.path.exists(BILD):
        notiz("Bild fehlt: %s" % BILD)
        return 2
    sha = hashlib.sha256(open(BILD, "rb").read()).hexdigest()
    notiz("Bild %s: %d B sha %s" % (os.path.basename(BILD), os.path.getsize(BILD), sha[:16]))
    if sha != BILD_SHA and BILD.endswith("firstlight.img") and "fl-v0af" in BILD:
        notiz("sha weicht vom verbrieften v0af ab — Write bleibt aus")
        return 2
    if offen():
        notiz("Telefon laeuft schon (Port 23 offen) — hier wird nichts geflasht")
        return 0
    if "fastboot" not in fb("devices", frist=8):
        notiz("kein Fastboot-Geraet in der Liste — nichts gethan")
        return 2
    vor = state()
    if not sicherung_pruefen():
        return 2
    if TROCKEN:
        notiz("trockener Lauf: nicht gesetzt, nicht geflasht")
        return 0
    notiz("Slot setzen: " + fb("--set-active=a", frist=30).strip().splitlines()[-1])
    notiz("flash boot_a: " + fb("flash", "boot_a", BILD, frist=600).strip().splitlines()[-1])
    nach = state()
    for k in vor:
        if vor[k] != nach[k]:
            notiz("  %s: %s -> %s" % (k, vor[k], nach[k]))
    notiz("Neustart ins Flash: " + fb("reboot", frist=30).strip().splitlines()[-1])
    t0 = time.time()
    while time.time() - t0 < 300 and not offen():
        time.sleep(3)
    notiz("Port 23 %s nach %ds" % ("offen" if offen() else "BLEIBT ZU", int(time.time() - t0)))
    if offen():
        time.sleep(20)
        notiz("Port 23 zwanzig Spaeter noch offen: %s" % offen())
    with open(os.path.join(MANIFEST, "m1-4-%s.txt" % time.strftime("%Y-%m-%d-%H%M")), "w",
              encoding="utf-8") as f:
        f.write("\n".join(BELEG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
