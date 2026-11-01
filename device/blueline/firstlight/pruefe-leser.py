#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruefpunkte fuer die Leser-Skripte — gegen eine nachgebaute Telefon-Shell.

Kein Suite-Ersatz: die Suite prueft Bilder und Init, nicht diese Leser. Hier
steht eine nachgebaute Shell, die genau die Eigenheiten zurueckgibt, die am
echten Telefon gemessen wurden:

  * sie wiederholt jeden Befehl im Echo und bricht das Echo bei ~78 Spalten um
  *printf '@@%s\\n' X  druckt  @@X  — und das Echo enthaelt '@@' nicht
  * Base64-Zeilen kommen mit vorangestelltem Ausrufezeichen
  * Prompt-Zeilen (~ # und > ) stehen dazwischen

Damit wird gepueft, was der Leser aus solch einem Ton macht: ein dichter Bereich
muss als dicht durchkommen und bytegleich auf der Platte landen, ein fehlendes
Blockstueck muss als LUECKERIG gemeldet werden und darf das Programm nicht zum
Absturz bringen, und Echo-Bruchstuecke duerfen nicht als Payload gelesen werden.

Aufruf:  python3 pruefe-leser.py       (Exit 0 = alle Pruefpunkte ok)
"""
import base64
import gzip
import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util

spec = importlib.util.spec_from_file_location("gk", os.path.join(HERE, "greife-kalibrier.py"))
gk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gk)

fehlt = []


def pruefung(name, waehr, erwartet):
    if waehr == erwartet:
        print("ok - %s" % name)
    else:
        print("NOT OK - %s: %r statt %r" % (name, waehr, erwartet))
        fehlt.append(name)


# ---- Inhalt, den die nachgebaute Shell bereitstellt -------------------------
KLAR = os.urandom(200000)                 # unkomprimierbar: mehrere Bloecke
PAKET = gzip.compress(KLAR, 9)
BLOCK = gk.BLOCK
groesse, shall = len(PAKET), hashlib.sha256(PAKET).hexdigest()
klar_g, klar_sha = len(KLAR), hashlib.sha256(KLAR).hexdigest()
corrupt = [False]
kleben = [False]
protokol = []


def umbruch(text):
    """Was die Shell beim Echo bei ~78 Spalten anstellt: CR LF mittendrin."""
    return "\r\n".join(text[i:i + 78] for i in range(0, len(text), 78))


def antworte(ver):
    """Ein Stueck Telefon-Shell: Echo, Antwort, Prompt."""
    puffer = b""
    while True:
        try:
            d = ver.recv(4096)
        except OSError:
            return
        if not d:
            return
        puffer += d
        while b"\r\n" in puffer:
            zeile, puffer = puffer.split(b"\r\n", 1)
            befehl = zeile.decode("utf-8", "replace").strip()
            if not befehl:
                continue
            ton = umbruch(befehl) + "\r\n"
            m = re.match(r"printf '@@%s\\n' (\S+)", befehl)
            if m:
                ton += "@@" + m.group(1) + "\r\n"
            elif "gzip -9" in befehl and "base64" not in befehl:
                # eine @@-Zeile mit vier Werten, dazu ein Echo-Bruchstueck,
                # das wie eine Antwort aussieht, aber keine Ziffern hÃ¤lt
                ton += ("@@groesse=%d sha=%s klartext=%d klarsha=%s\r\n"
                        % (groesse, shall, klar_g, klar_sha))
                ton += "@@groesse=$(wc -c < /run/ab.bin.gz | tr -d ' ')\r\n"
            elif "base64" in befehl:
                nr = int(re.search(r"skip=(\d+)", befehl).group(1))
                stuck = PAKET[nr * BLOCK:(nr + 1) * BLOCK]
                if nr == 1 and corrupt[0]:
                    stuck = stuck[:40]          # ein Stueck fehlt: muss LUCKERIG
                # ohne das abtrennende echo klebt der Prompt an der Payload —
                # genau der Fall, den der Rohton vom Telefon gezeigt hat
                if kleben[0]:
                    ton += base64.b64encode(stuck).decode()
                else:
                    ton += base64.b64encode(stuck).decode() + "\r\n"
                # drei Echo-Stuecke, die auf den ersten Blick wie Payload aussehen
                ton += "> echo groesse=$(wc -c < /run/ab.bin) count=1 2>/dev/null |\r\n"
                ton += "!/!/\"\r\n"
                ton += "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"
            ver.sendall(ton.encode() + b"~ # ")
            protokol.append((befehl[:60], ton[:90]))


ZEILEN = []


def notiz(m):
    ZEILEN.append(m)


zielpfad = os.path.join(HERE, "pruefstand")
os.makedirs(zielpfad, exist_ok=True)
gk.ZIEL = zielpfad


def lauf(kaputt=False, kleben_payload=False):
    corrupt[0] = kaputt
    kleben[0] = kleben_payload
    a, b = socket.socketpair()
    a.settimeout(5)                       # ohne Frist haengt der Sammler fuer immer
    threading.Thread(target=antworte, args=(b,), daemon=True).start()
    try:
        return gk.hole(a, notiz, "lun-test.bin", "/dev/sda", 999)
    finally:
        a.close()


pruefung("Rahmen-Befehl enthaelt die Markierung nicht",
         "@@ANFANG" in gk.rahmen("ANFANG", "x"), False)
pruefung("Rahmen druckt lokal genau die Markierung",
         subprocess.run(["sh", "-c", gk.rahmen("ANFANG", "x")],
                        capture_output=True, text=True).stdout, "@@ANFANG_x\n")
pruefung("dichter Bereich gilt als dicht", lauf(False), True)
pfad = os.path.join(zielpfad, "lun-test.bin")
pruefung("geschriebene Datei bytegleich zum Ursprung",
         open(pfad, "rb").read() == KLAR if os.path.exists(pfad) else None, True)
pruefung("fehlendes Blockstueck gilt als LUECKERIG", lauf(True), False)
pruefung("angeklebter Prompt kostet keine Payload", lauf(False, True), True)
pruefung("Echo-Bruchstuecke werden nicht Payload",
         any("count=1" in z for z in ZEILEN), False)

for datei in ("greife-kalibrier.py", "horsche-auf-leitung.py", "baue-v0af-umbau.py",
              "greife-beweise.py", "pruefe-leser.py"):
    pruefung("kompiliert: %s" % datei,
             subprocess.run([sys.executable, "-m", "py_compile", os.path.join(HERE, datei)],
                            capture_output=True, text=True).returncode, 0)
for datei in ("build-v0af.sh", "../../../tools/ci-arm64.sh"):
    r = subprocess.run(["sh", "-n", os.path.join(HERE, datei)], capture_output=True, text=True)
    pruefung("sh -n: %s" % os.path.basename(datei), (r.returncode, r.stderr.strip()), (0, ""))

print("Notizen:")
for z in ZEILEN:
    print("   " + z)
print("Leitung:")
for b, t in protokol:
    print("   > " + repr(b) + "\n     " + repr(t))
shutil.rmtree(zielpfad, ignore_errors=True)
print("\n%d Pruefpunkte, %d Fehler" % (13 - len(fehlt) + len(fehlt), len(fehlt)))
sys.exit(1 if fehlt else 0)
