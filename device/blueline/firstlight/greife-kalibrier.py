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
import zlib
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


def hole(s, notiz, name, quelle, sektoren, start=0):
    """Bereich nach /run/ab.bin holen, gzippen, in Bloecken ablesen, beglaubigen.

    Dasgzippen ist kein Schmuck: die Kalibrier-Partitionen sind groesstenteils
    Nullen, und eine gepackte Datei geht in zwei Bloecken ueber die Leitung, wo die
    rohe 8000 Bloecke brauchte. Geprueft wird der Hash der gepackten Datei; der
    Klartext-Hash steht zusaetzlich im Manifest, weil M1.3 den haben will.
    """
    # Die vier Antwortzeilen bekommen das @@-Praezix, damit sie im Echo-Wust
    # wiederzufinden sind: das Echo wiederholt den Befehl und bricht bei ~78
    # Spalten um, aber keine Echo-Zeile kann mit @@ beginnen.
    antwort = ("printf '@@%s %s %s %s\\n' " + " ".join(chr(34) + f + chr(34) for f in (
        "groesse=$(wc -c < %s 2>/dev/null | tr -d ' ')" % (GRUND + ".gz"),
        "sha=$(sha256sum %s 2>/dev/null | cut -d' ' -f1)" % (GRUND + ".gz"),
        "klartext=$(wc -c < %s 2>/dev/null | tr -d ' ')" % GRUND,
        "klarsha=$(sha256sum %s 2>/dev/null | cut -d' ' -f1)" % GRUND)) + " 2>/dev/null")
    grund = abfrage(s, "dd if=%s bs=512 skip=%d count=%d of=%s 2>/dev/null; "
                       "gzip -9 -f -c %s > %s 2>/dev/null; %s"
                    % (quelle, start, sektoren, GRUND, GRUND, GRUND + ".gz", antwort),
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
        # Ein zusammenhaengender Base64-Strom ohne Umbuch: tr -d nimmt die
        # Zeilenumbrueche, die busybox base64 bei 70 Spalten selbst einbaut.
        # Nur eine Zeile, die ZWISCHEN 40 und 40000 Zeichen lang ist und nur aus
        # Base64-Zeichen besteht, kann Payload sein — kein Echo-Stueck erfuellt
        # das, weil jedes Echo-Stueck Leerzeichen, Klammern oder Punkte haelt.
        befehl = "dd if=%s.gz bs=%d skip=%d count=1 2>/dev/null | base64 | tr -d %s; echo" % (
            GRUND, BLOCK, nr, chr(39) + chr(92) + "n" + chr(39))
        text = abfrage(s, befehl, "block-%s-%d" % (name, nr))
        if text is None:
            notiz("  %-30s Block %d/%d ohne Antwort" % (name, nr, brocken))
            return False
        if nr == 0:
            # Der Rohton des ersten Blocks: wenn eine Beglaubigung nicht passt,
            # muss die Leitung selbst nachzulesen sein, nicht nur ihr Ergebnis.
            with open(os.path.join(ZIEL, "roh-%s.block0.txt" % name), "w") as f:
                f.write(text)
        # Ohne das abtrennende echo oben klebt der Prompt an der Payload
        # (tr -d frisst den Zeilensprung am Ende), und die Zeile ist nicht mehr
        # rein — der Filter wuerfe sie weg. zusaetzlich wird ein angeklebter
        # Prompt abgeschnitten, falls er doch einmal mitkommt.
        kandidaten = []
        for z in text.split("\n"):
            # Die langste Fuehrung aus Base64-Zeichen nehmen: klebt der Prompt
            # an (tr -d frisst den Zeilensprung am Payload-Ende), hoert die Folge
            # davor auf. Echo-Stuecke erreichen die Laenge fast nie, und wenn,
            # erwischt es die Beglaubigung.
            m = re.match(r"[A-Za-z0-9+/]{40,}={0,2}", z.strip())
            if m:
                kandidaten.append(m.group(0))
        rein = "".join(kandidaten)
        try:
            daten[nr] = base64.b64decode(rein + "=" * (-len(rein) % 4))
        except (binascii.Error, ValueError):
            daten[nr] = b""
    gepackt = b"".join(daten[i] for i in sorted(daten))
    sha = hashlib.sha256(gepackt).hexdigest()
    try:
        klartext = gzip.decompress(gepackt)
    except (OSError, EOFError, zlib.error) as fehler:
        # Ein fehlendes Blockstueck ist kein Absturz: ein abgebrochenes gzip
        # wirft zlib.error. Genau diese Luecke soll gemeldet werden, nicht der
        # halbe Rest als Klartext durchgewinkt.
        notiz("  %-30s Entpacken fehlgeschlagen (%s) — LUECKERIG"
              % (name, type(fehler).__name__))
        return False
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
    # Die LUN-Karte: welcher Knoten fuehrt welchen Partitionsnamen (M1.3), und
    # die Groesse jeder Scheibe in 512-B-Sektoren — ohne die laesst sich der
    # zweite GPT-Kopf nicht adresieren, der ganz hinten liegt.
    karte = abfrage(s, "for u in /sys/block/sd*/sd*/uevent; do grep -H . $u; done 2>/dev/null; "
                       "for d in /sys/block/sd*/size /sys/block/sd*/sd*/size; do "
                       "echo $d $(cat $d); done 2>/dev/null",
                    "lun-karte")
    knoten = {}
    sektoren = {}
    scheiben = {}
    if karte:
        with open(os.path.join(ZIEL, "lun-karte.txt"), "w") as f:
            f.write(karte + "\n")
        notiz("  lun-karte.txt %d B" % (len(karte) + 1))
        for zeile in karte.split("\n"):
            m = re.match(r"^/sys/block/(\S+?)/(\S+)/uevent:PARTNAME=(\S+)$", zeile.strip())
            if m:
                knoten[m.group(3)] = "/dev/" + m.group(2)
            m = re.match(r"^/sys/block/\S+/(\S+)/size (\d+)$", zeile.strip())
            if m:
                sektoren["/dev/" + m.group(1)] = int(m.group(2))
            m = re.match(r"^/sys/block/([^/]+)/size (\d+)$", zeile.strip())
            if m:
                scheiben["/dev/" + m.group(1)] = int(m.group(2))
        notiz("  Karte: %d Partitionsnamen, %d Partitions-groessen, %d Scheiben" % (len(knoten), len(sektoren), len(scheiben)))

    else:
        notiz("  keine Karte — Kalibrier-Bereiche koennen nicht adresiert werden")

    offen = []

    def sicher(name, quelle, anz, start=0):
        """Ein Bereich, und wenn er fehlt, ein zweiter Versuch am Ende.

        Ein Loch beim ersten Anlauf ist kein Beweis: ein einzelner Block ist schon
        mal zu spaet gekommen, waehrend das Telefon noch gzippte. Der zweite
        Versuch kostet eine Minute und entscheidet, ob das Manifest ein Loch traegt.
        """
        if not hole(s, notiz, name, quelle, anz, start):
            offen.append((name, quelle, anz, start))
    # GPT: Header und Eintragssatz am Anfang jedes LUN; die sichere Kopfzeile
    # wird ueber die Groesse der Platte adresiert, hier ueber blockdev --getsize.
    for lun in "abcdef":
        sicher("gpt-lun%s-kopf.bin" % lun, "/dev/sd%s" % lun, 64, 0)
    # Die kleinen Kalibrier-Partitionen, ueber den Partitionsnamen gesucht.
    # Der zweite GPT-Kopf liegt ganz hinten — ohne die Scheibengroesse ist er
    # nicht zu adresieren, und ohne ihn ist eine Partitionstabelle nicht heilbar.
    for lun in "abcdef":
        platte = "/dev/sd%s" % lun
        ende = scheiben.get(platte, 0)
        if ende >= 64:
            sicher("gpt-lun%s-ende.bin" % lun, platte, 64, max(0, ende - 64))
    # Vor einem Write auf boot_a muss die Sicherung von boot_a da sein, und zwar
    # mit gepruefter Groesse und geprueftem sha (Gregors Regel vor jedem Write).
    # boot_b fehlt hier mit Absicht: sein Inhalt ist per Konstruktion die
    # Referenzdatei pmos-ref-build/ref/boot.img (sha ed2c225f...), und 64 MiB
    # ueber diese Leitung kosten eine Viertelstunde Haltezeit pro Bild.
    for part in ("boot_a", "dtbo_a", "vbmeta_a", "vbmeta_b",
                 "modemst1", "modemst2", "persist", "frp", "misc", "devinfo", "dtbo_b"):
        pfad = knoten.get(part)
        if not pfad:
            notiz("  %-30s nicht in der Karte — uebersprungen" % ("kalibrier-%s.bin" % part))
            continue
        # Die wirkliche Groesse, nicht ein erratener Vorrat: persist ist 32 MiB,
        # misc 1 MiB. Ohne die Zahl aus der Karte waere persist abgeschnitten.
        anzahl = min(sektoren.get(pfad, 2048), 1 << 17)
        sicher("kalibrier-%s.bin" % part, pfad, anzahl, 0)
    if offen:
        notiz("  zweiter Versuch fuer %d Loch(er): %s"
              % (len(offen), ", ".join(n for n, _, _, _ in offen)))
        for name, quelle, sektoren, start in list(offen):
            if hole(s, notiz, name, quelle, sektoren, start):
                offen.remove((name, quelle, sektoren, start))
    if offen:
        notiz("  ehrliches Loch bleibt: %s" % ", ".join(n for n, _, _, _ in offen))
    notiz("=== Abgriff fertig: %s ===" % ZIEL)
    try:
        s.close()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
