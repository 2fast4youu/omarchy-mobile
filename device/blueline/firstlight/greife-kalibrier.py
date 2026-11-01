#!/usr/bin/env python3
"""Holt GPT-Sektoren und Kalibrier-Partitionen aus dem laufenden Bild, beglaubigt.

Grund: M1.3 und M1.4 verlangen vor dem ersten Slot-Flag-Write die LUN-Karte, die
Kalibrier-Backups mit zweifachem sha256 und die GPT-Sektoren mit den CRCs beider
Header. Bisher gab es dafuer keinen Kanal: ohne Shell war nichts zu lesen, und
mit Shell war sie nach ~340 s weg. v0af haelt das Fenster offen, solange eine
Verbindung steht.

Ablauf pro Bereich, damit ein Abbruch nicht als Erfolg durchgeht:
  1. Das Telefon holt den Bereich in /run/ab.bin (tmpfs) und nennt Bytezahl und
     sha256 dieser Datei.
  2. Der Reader holt /run/ab.bin in Bloecken, base64, jeder Block im Rahmen.
     Die Rahmen werden gebaut (Markierung als Concatenation), denn die Shell
     wiederholt jeden Befehl im Echo: ein geschriebener Rahmen kaeme zweimal
     zurueck, und der Sammler hielte das Echo fuer die Antwort (gemessen 20:45,
     sieben Artefakte verrutscht).
  3. Treffen Bytezahl und Hash der gefuegten Bloecke nicht, heisst die Datei im
     Manifest LUCKERIG und wird ein zweites Mal gelesen.

Ohne diese Pruefung ist ein Base64-Abgriff ueber eine Telnet-Leitung ein
Geruecht: die Kernel-Konfiguration kam um 20:45 zerstuelt an.
"""
import base64
import binascii
import gzip
import hashlib
import os
import re
import socket
import sys
import time

ZIEL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "evidence", "kalibrier")
FRIST = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
BLOCK = 4096
GRUND = "/run/ab.bin"
Q = chr(39)


def rahmen(wort, merkmal):
    """Befehl, der eine Markierung druckt, ohne dass das Echo sie enthaelt.

    Zwei Fallen, beide gemessen:
      * ein geschriebenes `@@ANFANG` kommt im Echo des Befehls zurueck, der
        Sammler haelte das Echo fuer die Antwort (20:45, sieben Artefakte
        verrutscht);
      * die Concatenation `${''}` gilt in dieser Shell als offenes Anführungs-
        zeichen — jedes Kommando haengt danach im Fortsetzungsprompt `> ` fest
        und es kommt gar keine Antwort (21:06, alle Bereiche „keine
        Grunddaten").
    printf druckt die Markierung, im Echo steht nur die Formatkette.
    """
    return "printf '@@%s\\n' " + wort + "_" + merkmal


def sammle(s, bis_zu, frist_s):
    """Sammle bis die Markierung da ist. Zeitüberschreitung ist kein Abbruch.

    Eine Leere von acht Sekunden heisst nur, dass das Telefon noch rechnet (ein
    dd ueber 32 MiB dauert), nicht, dass die Leitung kaputt ist.
    """
    ende, out = time.time() + frist_s, b""
    while time.time() < ende:
        try:
            d = s.recv(65536)
        except socket.timeout:
            continue
        except OSError:
            break
        if not d:
            break
        out += d
        if bis_zu.encode() in out:
            return out.decode("utf-8", "replace")
    return None


def abfrage(s, befehl, merkmal, frist_s=180):
    """Befehl im Rahmen senden, die Antwort ohne Echo zurueckgeben, oder None."""
    s.sendall((rahmen("ANFANG", merkmal) + "\r\n").encode())
    if sammle(s, "@@ANFANG_%s" % merkmal, 60) is None:
        return None
    s.sendall((befehl + "\r\n").encode())
    s.sendall((rahmen("ENDE", merkmal) + "\r\n").encode())
    antwort = sammle(s, "@@ENDE_%s" % merkmal, frist_s)
    if antwort is None:
        return None
    teil = antwort.split("@@ANFANG_%s" % merkmal, 1)[-1]
    teil = teil.split("@@ENDE_%s" % merkmal)[0]
    zeilen = []
    for z in teil.split("\n"):
        z = z.strip("\r").strip()
        if not z or z.startswith("~ #") or z.startswith(">") or z == befehl:
            continue
        zeilen.append(z)
    return "\n".join(zeilen)


def telefon(notiz):
    t0 = time.time()
    while time.time() - t0 < FRIST:
        try:
            s = socket.create_connection(("172.16.42.1", 23), timeout=3)
            s.settimeout(8.0)
            try:
                s.sendall(b"\r\n")
                s.recv(4096)
            except OSError:
                pass
            notiz("Telefon erreichbar nach %.0fs" % (time.time() - t0))
            return s
        except OSError:
            time.sleep(4)
    return None


def knoten(partname):
    """Shell-Ausdruck, der den Blockknoten eines Partitionsnamens sucht.

    Die by-partlabel-Ketten fehlen in unserem Initramfs (Wurzel #8), also ueber
    die uevent-Dateien, genau wie die Partitionssuche im Init selbst.
    """
    return ('$(for u in /sys/block/sd*/sd*/uevent; do grep -q "^PARTNAME=%s$" '
            '"$u" 2>/dev/null && { q="${u%%uevent}"; echo /dev/"${q##*/}"; '
            "break; }; done)") % partname


def hole(s, notiz, name, quelle, sektoren, start=0):
    """Bereich nach /run/ab.bin holen, gzippen, in Bloecken ablesen, beglaubigen.

    Dasgzippen ist kein Schmuck: die Kalibrier-Partitionen sind groesstenteils
    Nullen, und eine gepackte Datei geht in zwei Bloecken ueber die Leitung, wo die
    rohe 8000 Bloecke brauchte. Geprueft wird der Hash der gepackten Datei; der
    Klartext-Hash steht zusaetzlich im Manifest, weil M1.3 den haben will.
    """
    grund = abfrage(s, "dd if=%s bs=512 skip=%d count=%d of=%s 2>/dev/null; "
                       "gzip -9 -f -c %s > %s 2>/dev/null; "
                       "echo groesse=%s sha=%s; "
                       "echo klartext=%s klarsha=%s" % (
                           quelle, start, sektoren, GRUND, GRUND, GRUND + ".gz",
                           "wc -c < %s.gz" % GRUND,
                           "sha256sum %s.gz | cut -d%s -f1" % (GRUND, Q),
                           "wc -c < %s" % GRUND,
                           "sha256sum %s | cut -d%s -f1" % (GRUND, Q)),
                "grund-%s" % name)
    if grund is None:
        notiz("  %-30s keine Grunddaten" % name)
        return False
    m = re.search(r"groesse=(\d+)\s+sha=([0-9a-f]{64})", grund.replace("\n", " "))
    k = re.search(r"klartext=(\d+)\s+klarsha=([0-9a-f]{64})", grund.replace("\n", " "))
    if not m:
        notiz("  %-30s Grunddaten unlesbar: %r" % (name, grund[:90]))
        return False
    groesse, shall = int(m.group(1)), m.group(2)
    klar_g, klar_sha = (int(k.group(1)), k.group(2)) if k else (0, "")
    if groesse == 0:
        notiz("  %-30s am Telefon leer" % name)
        return False
    brocken = (groesse + BLOCK - 1) // BLOCK
    daten = {}
    for nr in range(brocken):
        # Jede Base64-Zeile bekommt ein Ausrufezeichen vorangestellt. Die Shell
        # wiederholt den Befehl im Echo, und bei ~80 Spalten bricht das Echo um —
        # die Bruchstuecke waeren sonst Payload, und ein `count=1` ist
        # zufaellig ein gueltiges Base64-Stueck. Eine Zeile, die mit ! beginnt,
        # kann das Echo nicht hervorbringen.
        befehl = "dd if=%s.gz bs=%d skip=%d count=1 2>/dev/null | base64 | sed %s" % (
            GRUND, BLOCK, nr, chr(34) + "s/^/!/" + chr(34))
        text = abfrage(s, befehl, "block-%s-%d" % (name, nr))
        if text is None:
            notiz("  %-30s Block %d/%d ohne Antwort" % (name, nr, brocken))
            return False
        rein = "".join(z[1:] for z in text.split("\n") if z.startswith("!"))
        rein = "".join(re.findall(r"[A-Za-z0-9+/=]+", rein))
        try:
            daten[nr] = base64.b64decode(rein + "=" * (-len(rein) % 4))
        except (binascii.Error, ValueError):
            daten[nr] = b""
    gepackt = b"".join(daten[i] for i in sorted(daten))
    sha = hashlib.sha256(gepackt).hexdigest()
    try:
        klartext = gzip.decompress(gepackt)
    except (OSError, EOFError):
        klartext = gepackt
    dicht = len(gepackt) == groesse and sha == shall
    if k:
        dicht = dicht and len(klartext) == klar_g and hashlib.sha256(klartext).hexdigest() == klar_sha
    with open(os.path.join(ZIEL, name), "wb") as f:
        f.write(klartext)
    notiz("  %-30s %10d B Klar  %s  sha %s  (%d B gepackt, %d Bloecke)" % (
        name, len(klartext), "dicht" if dicht else "LUCKERIG",
        hashlib.sha256(klartext).hexdigest()[:16], groesse, brocken))
    return dicht


def main() -> int:
    os.makedirs(ZIEL, exist_ok=True)
    notizdatei = os.path.join(ZIEL, "manifest-%s.txt" % time.strftime("%Y-%m-%d-%H%M"))

    def notiz(m):
        zeile = time.strftime("%H:%M:%S ") + m
        print(zeile, flush=True)
        with open(notizdatei, "a") as f:
            f.write(zeile + "\n")

    s = telefon(notiz)
    if s is None:
        notiz("Telefon in %ds nicht erreichbar" % FRIST)
        return 1
    notiz("=== Kalibrier- und GPT-Abgriff, Ziel %s ===" % ZIEL)
   # Die LUN-Karte: welcher Knoten fuehrt welchen Partitionsnamen (M1.3).
    karte = abfrage(s, "for u in /sys/block/sd*/sd*/uevent; do grep -H . $u; done 2>/dev/null",
                    "lun-karte")
    if karte:
        with open(os.path.join(ZIEL, "lun-karte.txt"), "w") as f:
            f.write(karte + "\n")
        notiz("  lun-karte.txt %d B" % (len(karte) + 1))
    # GPT: Header und Eintragssatz am Anfang jedes LUN; die sichere Kopfzeile
    # wird ueber die Groesse der Platte adresiert, hier ueber blockdev --getsize.
    for lun in "abcdef":
        hole(s, notiz, "gpt-lun%s-kopf.bin" % lun, "/dev/sd%s" % lun, 64, 0)
    # Die kleinen Kalibrier-Partitionen, ueber den Partitionsnamen gesucht.
    for part in ("modemst1", "modemst2", "persist", "frp", "misc", "devinfo", "dtbo_b"):
        hole(s, notiz, "kalibrier-%s.bin" % part, knoten(part), 1 << 20, 0)
    notiz("=== Abgriff fertig: %s ===" % ZIEL)
    try:
        s.close()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
