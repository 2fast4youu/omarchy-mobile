#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Belegt VOR dem ersten Write auf userdata, was auf der Partition liegt.

Grund: 51 GiB werden nicht gesichert (kein 64-GiB-Backup, und ein Teilstueck
waere keine Sicherung), also muss vor dem Schreibvorgang in offenen Zahlen
dastehen, dass die Partition keine Nutzerdaten traegt. Gelesen wird das am
laufenden Flash-Start (v0af, alles ausser userdata schreibgeschuetzt) durch die
bewaehrte Rahmenleitung aus greife-kalibrier.py — derselbe Leser, dieselben
Regeln, hier nur mit einer anderen Beweisliste.

Die zwei Stuecke, die zaehlen: der ext4-Superblock (laesst er sich lesen, ist
die Partition ein leeres Fabrik-Dateisystem, kein Datengrab) und das
Inhaltsverzeichnis von /mnt/ud. Ein geleertes userdata hat ausser lost+found
nichts. Das Telefon zusaetzlich entsperrt (`unlocked: yes`) — ein Entsperren
loescht auf diesem Geraet die Nutzerdaten, gemessen als getvar-Antwort.

Aufruf:  beweise-userdata.py [zielordner]
"""
import importlib.util
import os
import socket
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gk", os.path.join(HIER, "greife-kalibrier.py"))
gk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gk)

ZIEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HIER, "evidence", "vor-userdata")
# Userdata beginnt laut GPT bei LBA 2068480, Sektor 4096 B — in 1024-B-Blocken
# ist das das Vierfache. Die Zahl kommt aus dem Auszug, nicht aus dem Kopf.
UDLB = 2068480
BEWEISE = [
    ("rueckgabezeit.txt", "cat /proc/uptime"),
    ("partitionen.txt", "cat /proc/partitions"),
    ("partlabel.txt", "ls /dev/disk/by-partlabel 2>/dev/null | head -30"),
    ("sda-groessen.txt", "awk '$4~/^sda[0-9]+$/{print $3, $4}' /proc/partitions | sort -n"),
    # Die Partition wird ueber ihren Anfangssektor aus der GPT geholt, nicht ueber
    # 'die groesste Partition' — dieselbe Regel, die der neue Init braucht, und
    # sort -n auf Nameslisten waehlt 'sda10' vor 'sda2' (gemessen).
    ("UD-Rahmen.txt", "D=/sys/block/sda; S=16547840"),
    ("UD- suchen.txt", "for p in $D/sda*; do [ $(cat $p/start) = $S ] && UD=/dev/${p##*/}; done"),
    ("UD-gefunden.txt", "echo UD=$UD"),
    ("ud-geraet.txt", "echo $UD; ls -l $UD; cat $UD/size 2>/dev/null"),
    ("ud-blockgroesse.txt", "blockdev --getss $UD 2>/dev/null; blockdev --getsize64 $UD 2>/dev/null"),
    ("ud-ro.txt", "blockdev --getro $UD 2>/dev/null; blockdev --getro /dev/sda 2>/dev/null"),
    ("ud-superblock.txt",
     "dd if=$UD bs=1024 skip=1 count=1 2>/dev/null | hexdump -C | sed -n '1,5p'"),
    ("ud-ext4-makler.txt", "dd if=$UD bs=1 skip=1080 count=2 2>/dev/null | hexdump -C"),
    ("ud-uuid.txt", "dd if=$UD bs=1 skip=1040 count=16 2>/dev/null | hexdump -C"),
    ("ud-name.txt", "dd if=$UD bs=1 skip=122 count=16 2>/dev/null | tr -d '\\0'"),
    ("ud-mount-ro.txt", "mkdir -p /mnt/ud; mount -o ro $UD /mnt/ud 2>&1 | head -2; "
                        "echo rc=$?"),
    ("ud-inhalt.txt", "ls -la /mnt/ud 2>/dev/null | head -30"),
    ("ud-verbrauch.txt", "df -h /mnt/ud 2>/dev/null | tail -2"),
    ("ud-verloren.txt", "ls -la /mnt/ud/lost+found 2>/dev/null | head -6"),
    ("ud-tiefste-sicht.txt", "find /mnt/ud -maxdepth 2 2>/dev/null | head -25"),
    ("ud-entfernt.txt", "umount /mnt/ud 2>&1 | head -2; echo rc=$?"),
    ("speicher-ro.txt", "for d in /sys/block/sd*; do echo $d ro=$(cat $d/ro); done"),
    ("geraet-modell.txt", "cat /proc/device-tree/model 2>/dev/null | tr -d '\\0'"),
    ("partition-zeilen.txt", "wc -l < /proc/partitions"),
    # Vergleich mit dem Bild auf dem Mac: wo genau ist der geschriebene Satz?
    ("ud-versatz-1024.txt", "dd if=/dev/sda21 bs=1 skip=1024 count=64 2>/dev/null | hexdump -C"),
    ("ud-versatz-2048.txt", "dd if=/dev/sda21 bs=1 skip=2048 count=64 2>/dev/null | hexdump -C"),
    ("ud-versatz-8192.txt", "dd if=/dev/sda21 bs=1 skip=8192 count=64 2>/dev/null | hexdump -C"),
    ("ud-blockgroesse.txt", "dum2fs -h /dev/sda21 2>&1 | head -6"),
    ("ud-gpt-kopf.txt", "dd if=/dev/sda21 bs=1 skip=512 count=32 2>/dev/null | hexdump -C"),
]


def notiz(m):
    print(time.strftime("%H:%M:%S ") + m, flush=True)


os.makedirs(ZIEL, exist_ok=True)
s = socket.create_connection(("172.16.42.1", 23), timeout=8)
s.settimeout(25)
gk.wecke_shell(s)
notiz("Leitung offen, Shell geweckt")
gesamt = 0
for name, befehl in BEWEISE:
    text = gk.abfrage(s, befehl, name.replace(".", "-"))
    if text is None:
        notiz("  %-24s KEINE Antwort im Rahmen" % name)
        continue
    offen = os.path.join(ZIEL, name)
    with open(offen, "w", encoding="utf-8") as datei:
        datei.write(text if text.endswith("\n") else text + "\n")
    gesamt += len(text)
    notiz("  %-24s %5d B  %s" % (name, len(text), text.strip().splitlines()[0][:56]
                                 if text.strip() else ""))
s.close()
nicht_gefuellt = [n for n, _ in BEWEISE
                  if not os.path.exists(os.path.join(ZIEL, n))
                  or os.path.getsize(os.path.join(ZIEL, n)) == 0]
notiz("%d Beweise, %d Bytes, %d leer: %s"
      % (len(BEWEISE), gesamt, len(nicht_gefuellt), ", ".join(nicht_gefuellt) or "keine"))
sys.exit(1 if len(nicht_gefuellt) > 4 else 0)
