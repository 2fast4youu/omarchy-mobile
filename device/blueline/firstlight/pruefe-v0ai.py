#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ad-hoc-Pruefung fuer v0ai (offset in Byte, Fehlerwortlaut, Marker-Messung).

Ausdruecklich KEIN Suite-Gruen: die kanonische Suite (tools/ci-arm64.sh, 148 Punkte)
laeuft hier nicht mit. Diese Pruefung geht die vier anderen Aenderungen der letzten
Runde ab, und zwar am Verhalten:

  1. umbau(): die Umformung laeuft gegen den WIRKLICH ausgelieferten Init von v0ah
     (aus pack-v0ah/init, nicht nachgetippt) und muss Anker, Wortlaut, Zeilenzahl,
     ASCII und den neuen Versatz belegen — inklusive der Negativprobe gegen ein
     Archiv, das den Anker nicht traegt.
  2. build-v0ai.sh: Grundarchiv ist v0ah, Ausgabe ist v0ai, der Umbau ist
     vorgeschaltet, und die Bildpruefung verlangt jetzt offset=1048576.
  3. beweise-marker.py: laesst sich kompilieren, kein Befehl ueberlebt die
    Shell-Grenze von ~78 Zeichen, die drei Markierfelder sind drin, Namen dicht.
  4. misst-offset-einheit.sh: Syntax, und der Messaufbau legt das Dateisystem bei
     1 MiB ab und prueft 1024, 2048 und 1048576 — mit dem Archiv-mount.
  5. Falls der Build durch ist: das fertige Bild, sein sha256 und der Init aus dem
     ausgelieferten Archiv (aus-bild.cpio) mit Versatz in Byte und neuem Titel.
"""
import importlib.util
import os
import re
import subprocess
import sys

FL = "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight"
IMG = "/Users/gregor/hermes-workspace/images"
INIT_V0AH = "/Users/gregor/hermes-workspace/pack-v0ah/init"
ok = notok = 0


def pruef(beschreibung, bedingung,zusatz=""):
    global ok, notok
    if bedingung:
        ok += 1
        print("ok - %s" % beschreibung)
    else:
        notok += 1
        print("NOT OK - %s%s" % (beschreibung, ("  [%s]" % zusatz) if zusatz else ""))


def lade_umbau():
    spec = importlib.util.spec_from_file_location("u", os.path.join(FL, "baue-v0ai-umbau.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


text = open(INIT_V0AH, encoding="utf-8").read()
pruef("der v0ah-Init liegt zum Nachpruefen aus (677 Zeilen)",
      text.count("\n") == 677, "%d Zeilen" % text.count("\n"))
pruef("er traegt den alten Versatz 1024 und das 2>/dev/null",
      "offset=1024" in text and "mount -o rw,offset=1024 \"/dev/$UDNAME\" /ud 2>/dev/null" in text)

u = lade_umbau()
neu = u.umbau(text)
pruef("umbau: Versatz in Byte statt in 1024-Byte-Blocken",
      "offset=1048576" in neu and "offset=1024" not in neu)
pruef("umbau: kein 2>/dev/null mehr an den beiden Mounts",
      'mount -o rw,offset=1048576 "/dev/$UDNAME" /ud 2>&1' in neu
      and 'mount -o rw "/dev/$UDNAME" /ud 2>&1' in neu
      and re.search(r"mount -o rw[^\n]*/ud 2>/dev/null", neu) is None)
pruef("umbau: Erfolg haelt an /proc/mounts fest, nicht am Schweigen des Mounts",
      neu.count('grep -q " /ud " /proc/mounts') == 2)
pruef("umbau: der Fehlerwortlaut geht in die Marke (zwei Marken)",
      "v0ai VersatzMount" in neu and "v0ai beide Mounts fehl" in neu
      and '$udfehler' in neu)
pruef("umbau: Titel und Marken umbenannt, kein v0ah-Rest",
      "first-light v0ai - userdata rw" in neu and "v0ah" not in neu)
pruef("umbau: Suchsektor, Wache-Ausnahme, switch_root und Rueckweg bleiben drin",
      "UDSTART=16547840" in neu and "/tmp/uddev" in neu
      and "switch_root /ud /init" in neu and "restart2 bootloader" in neu)
pruef("umbau: nur ASCII, Zeilenzahl wachst nur um die neuen Kommentare (%d -> %d)"
      % (text.count("\n"), neu.count("\n")),
      all(ord(c) < 128 for c in neu) and 0 < neu.count("\n") - text.count("\n") <= 8)
# Die 79-Zeichen-Grenze gilt dem Telnet-Zeileneditor (gemessen an Befehlen, die ins
# Telefon getippt werden), NICHT dem Init: der laeuft aus einer Datei, und dieser
# ausgelieferte Init enthaelt laengste Zeilen ueber 150 Zeichen — mit ihm ist das
# Telefon booten und haben die Marken funktioniert. Pruefen laengt man hier also die
# Beweislisten (unten), nicht den Init.
pruef("Init-Langzeilen sind kein Befund: der ausgelieferte Init hat Zeilen bis %d Zeichen"
      % max(len(z) for z in text.splitlines()),
      max(len(z) for z in text.splitlines()) > 79)
pruef("umbau: keine neue Zeile ueberragt die laengste bereits erfolgreich bootende Zeile",
      max(len(z) for z in neu.splitlines()) <= max(len(z) for z in text.splitlines()) + 20,
      "neue laengste %d gegen %d" % (max(len(z) for z in neu.splitlines()),
                                     max(len(z) for z in text.splitlines())))
try:
    u.umbau(text.replace("offset=1024", "ohne versatz"))
    pruef("umbau weist ein Archiv ohne den Anker ab", False, "hat stillgeschwiegen")
except AssertionError as fehler:
    pruef("umbau weist ein Archiv ohne den Anker ab: %s" % str(fehler)[:52], True)

b = open(os.path.join(FL, "build-v0ai.sh"), encoding="utf-8").read()
pruef("build-v0ai.sh: Grundarchiv v0ah, Ausgabe v0ai",
      '$IMGD/fl-v0ah/new.cpio' in b and '$IMGD/fl-v0ah":/q:ro' in b
      and '$IMGD/fl-v0ai":/r' in b and "mkdir -p \"$IMGD/fl-v0ai\"" in b)
pruef("build-v0ai.sh: Umbau vorgeschaltet, Bildpruefung verlangt den Byte-Versatz",
      "baue-v0ai-umbau.py /q/new.cpio /r/new.cpio" in b
      and 'assert \\"offset=1048576\\" in init' in b and 'assert \\"first-light v0ai\\" in init' in b)
pruef("build-v0ai.sh: Syntax", subprocess.run(["sh", "-n", os.path.join(FL, "build-v0ai.sh")],
                                             capture_output=True).returncode == 0)

m = open(os.path.join(FL, "beweise-marker.py"), encoding="utf-8").read()
befehle = re.findall(r'\("([^"]+)", "((?:[^"\\]|\\.)*)"\),', m)
pruef("beweise-marker.py: kompiliert", subprocess.run(
    [sys.executable, "-m", "py_compile", os.path.join(FL, "beweise-marker.py")],
    capture_output=True).returncode == 0)
pruef("beweise-marker.py: %d Beweise, alle Befehle <= 78 Zeichen (laengster %d)"
      % (len(befehle), max(len(b) for _, b in befehle)), len(befehle) >= 10
      and all(len(b) <= 78 for _, b in befehle))
pruef("beweise-marker.py: die drei Markierfelder 0, 4096 und 8192 werden gelesen",
      all(("skip=%d " % n) in m for n in (0, 4096, 8192)))
pruef("beweise-marker.py: keine doppelten oder leerlaufbehafteten Dateinamen",
      len({n for n, _ in befehle}) == len(befehle)
      and all(n.strip() == n and " " not in n for n, _ in befehle))
pruef("beweise-marker.py: Partition ueber Anfangssektor, nicht ueber Namesortierung",
      "S=16547840" in m and "cat $p/start" in m)

o = open(os.path.join(FL, "misst-offset-einheit.sh"), encoding="utf-8").read()
pruef("misst-offset-einheit.sh: Syntax", subprocess.run(
    ["sh", "-n", os.path.join(FL, "misst-offset-einheit.sh")], capture_output=True).returncode == 0)
pruef("misst-offset-einheit.sh: Dateisystem bei 1 MiB im Blockgeraet, drei Versatzwerte",
      "bs=1M seek=1" in o and "for wert in 1024 2048 1048576" in o)
pruef("misst-offset-einheit.sh: gemessen wird mit dem mount aus dem Archiv, nicht nur dem des Containers",
      "mount-archiv" in o and "/alt/mount" in o)
# Verboten ist 2>/dev/null an den Stellen, deren Wortlaut der Beweis ist: an den
# Mounts und an ihren Erfolgsmeldungen. An mknod, modprobe und am losetup -d am Ende
# ist es gleichgueltig — dort steht kein Beweis, den es verstecken koennte.
mountzeilen = [z for z in o.splitlines() if "mount " in z and "offset" in z or "--version" in z]
pruef("misst-offset-einheit.sh: an allen Mount-Zeilen (%d) steht kein 2>/dev/null"
      % len(mountzeilen), all("2>/dev/null" not in z for z in mountzeilen),
      "betroffen: " + "; ".join(z.strip()[:60] for z in mountzeilen if "2>/dev/null" in z))

zy = open(os.path.join(FL, "schreibe-v0ai.sh"), encoding="utf-8").read()
pruef("schreibe-v0ai.sh: Syntax", subprocess.run(["sh", "-n", os.path.join(FL, "schreibe-v0ai.sh")],
                                                 capture_output=True).returncode == 0)
pruef("schreibe-v0ai.sh: Groesse und sha256 der Sicherung vor dem Write, harter Abbruch",
      'kalibrier-boot_a.bin' in zy and 'sha256-lokal.txt' in zy
      and 'erwartet $soll' in zy and 'return 1' in zy)
pruef("schreibe-v0ai.sh: Satz, Begleitdatei-Gegenprobe, Wachhueter ohne geerbten Ausgang",
      "Satz vor dem Write" in zy and "shasum -a 256 -c" in zy
      and "</dev/null" in zy and '>/dev/null 2>&1 &' in zy)
helfer = "/tmp/hermes-verify-fake-fastboot.sh"
open(helfer, "w").write('#!/bin/sh\necho "FAKE $*"; echo "OKAY [  0.001s]"\nexit 0\n')
os.chmod(helfer, 0o755)
um = dict(os.environ, FB=helfer,
          UDATEI=os.path.join(IMG, "userdata-alpine/marker-4mib.sparse.img"))
lauf = subprocess.run(["sh", os.path.join(FL, "schreibe-v0ai.sh")], capture_output=True,
                      text=True, env=um, timeout=200)
protokoll = lauf.stdout + lauf.stderr
pruef("Trockenuebung: Exit 0, Marker-Bild zuerst, dann boot_a, Slot a, Reboot",
      lauf.returncode == 0 and "marker-4mib.sparse.img" in protokoll  
      and "fl-v0ai/firstlight.img" in protokoll and "--set-active=a" in protokoll
      and "WRITE-ZYKLUS FERTIG" in lauf.stdout,
      "Ende: %r" % (protokoll.strip()[-60:],))
pruef("Trockenuebung: die Sicherung wird mit voller sha256 bestätigt",
      "0478f8dbe456a5877976f2514aa105619acf6c91056afb14eabe824d5c6929a0" in protokoll)
kaputt_ordner = "/tmp/hermes-verify-keine-backups"
os.makedirs(kaputt_ordner, exist_ok=True)
open(os.path.join(kaputt_ordner, "sha256-lokal.txt"), "w").write("0" * 64 + "  kalibrier-boot_a.bin\n")
um_kaputt = dict(um, BACKUP=kaputt_ordner)
lauf2 = subprocess.run(["sh", os.path.join(FL, "schreibe-v0ai.sh")], capture_output=True,
                       text=True, env=um_kaputt, timeout=200)
pruef("Negativprobe: falsche Sicherungssumme bricht ab (Exit %d), ohne Write auf boot_a"
      % lauf2.returncode, lauf2.returncode == 1
      and "ABBRUCH" in lauf2.stdout + lauf2.stderr
      and "flash boot_a" not in lauf2.stdout)

bild = os.path.join(IMG, "fl-v0ai", "firstlight.img")
if os.path.exists(bild):
    import hashlib, struct, gzip
    sys.path.insert(0, FL)
    import newc
    ro = open(bild, "rb").read()
    ks = struct.unpack_from("<I", ro, 8)[0]
    rs = struct.unpack_from("<I", ro, 16)[0]
    seite = 4096
    anfang = seite + ((ks + seite - 1) // seite) * seite
    ent = gzip.decompress(ro[anfang:anfang + rs])
    aus_bild = os.path.join(IMG, "fl-v0ai", "aus-bild.cpio")
    if os.path.exists(aus_bild):
        pruef("Bild-Ramdisk: das ausgeliehene Archiv ist bytegleich zum Entpackten",
              open(aus_bild, "rb").read() == ent)
    Hilf = "/tmp/hermes-verify-v0ai-bild.cpio"
    open(Hilf, "wb").write(ent)
    es = newc.read_cpio(Hilf)
    os.remove(Hilf)
    init = next(e["content"].decode("utf-8", "replace") for e in es if e["name"] == "init")
    pruef("fertiges Bild: %d Eintraege, Init mit offset in Byte, Titel, Fehlerwortlaut"
          % len(es),
          "offset=1048576" in init and "first-light v0ai" in init
          and "v0ai beide Mounts fehl" in init)
    pruef("fertiges Bild: kein 1024-Versatz, kein 2>/dev/null am userdata-Mount",
          "offset=1024" not in init
          and not any(z.strip().startswith("mount -o rw") and "2>/dev/null" in z
                      for z in init.splitlines()))
    pruef("fertiges Bild: die sechs Module sind unverloren",
          sum(1 for e in es if e["name"].endswith(".ko")) == 6)
    print("   Bild %d B, sha256 %s" % (len(ro), hashlib.sha256(ro).hexdigest()))
else:
    print("   (Bild fl-v0ai/firstlight.img noch nicht da - Build lief nicht durch.)")

print("\nAd-hoc-Pruefung v0ai: %d Pruefpunkte, %d Fehler" % (ok + notok, notok))
print("Nicht behauptet: Suite-Gruen. Die kanonische Suite (148 Punkte) lief hier")
print("nicht, und das Schreiben am Telefon ist durch diese Pruefung nicht belegt.")
sys.exit(1 if notok else 0)
