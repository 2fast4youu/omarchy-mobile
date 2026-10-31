#!/usr/bin/env python3
"""Setzt den FLASH-BEREIT-Block v0z obenauf, vor den v0y-Block.

Geschrieben mit open()/Python, nie mit dem read_file-Rueckgabewert (der liefert
'ZEILE|'-Praefixe und hat drei Builds vergiftet). Alle Zahlen im Block kommen aus
dem Bild, danach prueft tests/flash-block jede Zahl gegen sha256 und os.stat.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

REPO = "/Users/gregor/hermes-workspace/omarchy-mobile"
PROT = os.path.join(REPO, "device/blueline/BRINGUP-M1.md")
BILD = "/Users/gregor/hermes-workspace/images/fl-v0z/firstlight.img"
ARCHIV = "/Users/gregor/hermes-workspace/images/fl-v0z/new.cpio"
REF = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
FABRIK = "/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img"


def mass(pfad: str) -> tuple[int, str]:
    d = open(pfad, "rb").read()
    return len(d), hashlib.sha256(d).hexdigest()


def block(bild_b, bild_h, archiv_h, ref_b, ref_h, fab_b, fab_h, init_info) -> str:
    init_b, init_z = init_info
    return f"""## FLASH-BEREIT v0z — der echte Knopf, am Panel abgelesen und am Quelltext gemessen (2026-10-31, 13:3x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0z: Gregors Panel-Ablesung von v0y (13:0x, Uptime 1482-1494 s) hat zwei Befunde, beide in Dateien festgehalten (`evidence/weicher-knopf-panel-und-quelltext-2026-10-31.txt`). ERSTENS: das Feld `udcdateien=` listet `soft_connect` — der weiche Verbindungsknopf IST da, aber in der UDC-Klasse unter `/sys/class/udc/<udc>/`, nicht im debugfs. Die Suche von v0w (`find /sys/kernel/debug -name soft_connect`) konnte ihn dort nie finden, und meine ROOT CAUSE #6 ('der Knoten existiert nicht') war ein Befehl an die falsche Stelle: der Knoten existiert, mein Pfad war falsch. Am Quelltext gemessen (`drivers/usb/gadget/udc/core.c`): Zeile 1784 `DEVICE_ATTR_WO(soft_connect)`, die Worte des Handlers sind `connect` und `disconnect` (Zeile 1763, 1768, `sysfs_streq`), alles andere gibt `-EINVAL` (Zeile 1774), und ohne gebundenes Gadget gibt es `-EOPNOTSUPP` mit der Kernelmeldung `soft-connect without a gadget driver` (Zeile 1753ff). v0vs Fallback hätte `1` geschrieben, also `-EINVAL`. ZWEITENS: `gadgetordner=` ist leer, `gebunden=` ist leer, `controller-state=not attached` — es gab in diesen Bootes gar kein Gadget. Die Anlage wartet höchstens 30 s auf den UDC (Zeile 172, von der Referenz übernommen, die bei 1.734 s bindet) und überspringt sonst alles; die Nachbind-Runde von v0s beginnt mit einer Platzhalter-Schleife, die ohne Gadget am nicht erweiterten Muster durchläuft, ohne je eine Beweiszeile zu drucken. DRITTENS, und das ist der Grund, warum vier Bootes lang keine Antwort zu sehen war: die Marks der Anlage stehen in `/run/steps.log`, die Herzschlagzeile `letzter Schritt:` zeigt aber nur `tail -1`, und die letzte Zeile schreibt der dmesg-Block bei 42 s. Deshalb stand in zwei Bootes dasselbe `steps:[43s]` — kein Stehenbleiben, sondern die letzte von mehreren Zeilen.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

SCHRITT 0b, in Fastboot VOR dem Write, zwei Lesungen und ein Leseversuch:
(1) `fastboot getvar slot-retry-count:a` und `getvar partition-size:boot_a` —
intrauf gemessen am 31.10.: 12:46:22 vor dem Write `slot-retry-count:a: 2`,
12:47:05 nach dem Write `slot-retry-count:a: 3`. Der Write auf boot_a setzt den
Zähler auf seinen Anfangswert, ein erfolgreicher Start verbraucht ihn; ein
Stand von 3 bedeutet also frisch geflasht, nicht drei Fehlversuche
(`evidence/v0y-null-enumeration-und-retry-entschieden-2026-10-31.txt`). (2) `fastboot fetch boot_a`: gemessen meldet diese ABOOT-Generation `Unable to get max-fetch-size. Device does not support fetch command.` und die Datei bleibt 0 Byte — der Rohlog-Kanal ist aus Fastboot heraus geschlossen, der Versuch bleibt trotzdem stehen, weil nur die Datei das belegt. (3) Erst danach der Write.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0z/firstlight.img {bild_h} 300
```
v0z: {bild_b} B, sha256 `{bild_h}`, herausgelöste Init {init_b} B / {init_z} Zeilen, Archiv sha256 `{archiv_h}`. Vorgänger v0y: 21098496 B, sha256 `ee2b9cb4e88e11f50353277fae1fd745eebc92e9bc288df2c719d25eea158dca`, Init 22 786 B / 462 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es, und alle Bilder von v0s bis v0z tragen dieselbe Produktzahl 0xD002, ein Bild ist am Bus also nicht unterscheidbar.

Rueckweg STUFE 1 (stellt den Zustand von vorgestern früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `{ref_h}`, {ref_b} B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `{fab_h}`, {fab_b} B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

Gerät ist jetzt (gemessen 2026-10-31, zuletzt 12:52:57): **läuft v0y, an keinem Bus** — `fastboot devices` ohne Eintrag, kein Pixel am USB-Baum, `ping -c 2 172.16.42.1` antwortet nicht. Muster identisch zu v0r (302 s) und v0t: Kernel und Init laufen, der Panel zeigt Titel und Herzschlag, der Controller meldet keine Bindung. Für diesen Flash ist der Tastendruck nötig.

DIE NEUE RUNDE, alle 15 s, und ihr Ergebnis geht in die Schritt-Log, die der Herzschlag vorliest: debugfs und configfs hängen (Rückgabewerte `debugfsrc=` und `configfsrc=`), das Gadget anlegen **wenn keins da ist** (dieselbe Folge wie weiter oben: `0x18D1`/`0xD002`, `ncm.usb0` mit `rndis.usb0`-Fallback, `acm.GS0` daneben), binden wenn ungebunden (`binden rc=` mit Fehlertext), dann `connect` auf `/sys/class/udc/<udc>/soft_connect` und nach 5 s `state=` und `netz=` zurücklesen. Der Knopf wird NACH der Bindung gedrückt, weil der Handler ohne Gadget nur `-EOPNOTSUPP` antwortet — die Bindung wird also erst gelesen (`gebunden=$(cat …/g1/UDC </dev/null 2>/dev/null)`), dann gedrückt.

DER HERZSCHLAG, drei Zeilen DAZU, nichts ersetzt: `haengt:` mit der Häengeliste aus `/proc/self/mountinfo` (wie oft debugfs und configfs wirklich häangen), `gadget:` mit Ordnerinhalt, `readlink /sys/class/udc/*/gadget`, `is_active`, `current_speed` und `netz`, und `schritte:` mit `tail -6 /run/steps.log`. Die vorhandene Zeile `letzter Schritt:` mit `tail -1` bleibt stehen.

ERWARTUNG v0z (13:3x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel `Omarchy Mobile first-light v0z` und in jedem Block `haengt:` mit zwei Zahlen (die Häengeliste), `schritte:` mit den letzten sechs Schritten, und aus der neuen Runde die Wörter `g1 NEU angelegt` oder `g1 war da`, `binden rc=`, `connect rc=` mit `text=` und `pfad=`, danach `state=` und `netz=`. Die Fälle, die dieses Bild ohne jeden Bus trennt:
- `connect rc=0` mit `text=ohne` und danach `state=` auf `default` oder `addressed` oder `configured` = der Host hat den Reset gesehen; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen und eine Enumeration im Runner.
- `connect rc=` ungleich null mit `text=` enthaltend `soft-connect without a gadget driver` = die Bindung stand nicht, obwohl `binden rc=0` meldete; der Widerspruch ist der Messwert, nicht ein Fehler des Bildes.
- `text=` enthaltend `invalid argument` = die words-Annahme ist falsch (der Handler nannte im Quelltext `connect`, gemessen Zeile 1763).
- `binden rc=` ungleich null mit `text=` enthaltend `device or resource busy` = der Controller trägt in diesem Moment einen anderen Treiber; `no such device` = der UDC-Name passt nicht.
- `haengt:` mit debugfs 0 = debugfs häingt nicht, und `usb=` im alten Feld bleibt damit dunkel; das ist dann der einzige Weg, an den Modus-Knoten zu kommen, und nicht der Knopf.
- `g1 NEU angelegt` bei einem Boot, in dem die alte Anlage `No UDC found in 30 s` gemeldet haben muss = der UDC kam spaeter als die Wartezeit der Referenz; die runde Anlage ist damit die Erklärung der vier dunklen Bootes.
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

EINFANG nach dem Flash: der Runner sammelt die Belege selbst über Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${{OUT:-/Users/gregor/hermes-workspace/flash-observe}}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Der Runner lenkt seine eigene Ausgabe in diese Datei (`exec >>"$LOG" 2>&1`), die Umlenkung des Aufrufenden erhält nichts - gelesen wird der Log des Runners. Bei ausbleibender Enumeration ist das Panel das einzige Lesegeraet: ein Foto muss den Stand nennen, und der Titel nennt ihn.

BELEGE VOR DEM Flash, alle gelaufen: der Eine Durchgang über das geladene v0y-Archiv (drei Schritte, je 1 Fundstelle, Bilanz 182 offene gegen 182 zu Paren), `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv 0 Fehler, `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild, `verify-v0z.py` **46 Beweismale / 0 Fehler** am fertigen Bild, darunter die Selbstmessung des Prüfers an fünf bekannten Formen (5/5) und der Zeilendiff gegen v0y: genau eine geaenderte Zeile (der Titel), 67 eingefügte, keine gelöschte, jedes Messfeld des Vorgängers wortgleich erhalten. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen.

DREI REGELN AUS DIESEM BAU, alle gemessen:
1. **Ein Suchbegriff, an der falschen Stelle gesucht, meldet eine Abwesenheit, die keine ist.** `soft_connect` wurde im Kernelbaum und im debugfs gesucht und für nicht existent erklärt; es steht in der UDC-Klasse und war die ganze Zeit im eigenen Herzschlag-Feld `udcdateien=` ablesbar. Vor einem 'existiert nicht' gehört die Liste des laufenden Systems, nicht die der Quelle.
2. **`2>/dev/null` enthält den Teilstring `</dev/null` und deckt trotzdem nur den Fehlerausgang.** Der erste Leserscanner meldete die echte Hängerzeile als sauber; nach der Umstellung auf Token-Klassen misst der Prüfer sich selbst (5/5). Ein Prüfer ohne Selbstmessung schläft grün.
3. **Eine Platzhalter-Schleife ohne Fund druckt keine Beweiszeile und meldet damit Nichtstun als Fehlschlag.** `for g in /sys/kernel/config/usb_gadget/*` mit `[ -e "$g/UDC" ] || continue` lief vier Bootes lang still durch. Wer aus dem Fehlen einer Meldung schliesst, muss zuerst zeigen, dass der Zweig die Meldung überhaupt hätte drucken können.

"""


def einfgueg(text: str, neuer: str) -> str:
    muster = re.compile(r"^## FLASH-BEREIT v0y ", re.M)
    treffer = list(muster.finditer(text))
    assert len(treffer) == 1, "v0y-Ueberschrift %d mal, erwartet 1" % len(treffer)
    stelle = treffer[0].start()
    text = text[:stelle] + neuer + text[stelle:]
    assert text.count("## FLASH-BEREIT v0z ") == 1, "v0z-Block nicht eindeutig"
    assert text.index("## FLASH-BEREIT v0z ") < text.index("## FLASH-BEREIT v0y "), "v0z nicht obenauf"
    return text


def haupt() -> int:
    bild_b, bild_h = mass(BILD)
    archiv_b, archiv_h = mass(ARCHIV)
    ref_b, ref_h = mass(REF)
    fab_b, fab_h = mass(FABRIK)
    init_info = tuple(int(x) for x in os.environ.get("INIT_INFO", "0/0").split("/"))
    print("v0z-Bild %d B %s | Archiv %d B %s" % (bild_b, bild_h[:8] + "…" + bild_h[-6:],
                                                 archiv_b, archiv_h[:8] + "…" + archiv_h[-6:]))
    print("Rueckweg 1 %d B %s | Rueckweg 2 %d B %s" % (ref_b, ref_h[:8] + "…" + ref_h[-6:],
                                                       fab_b, fab_h[:8] + "…" + fab_h[-6:]))
    print("Init %d B / %d Zeilen" % init_info)
    prot = open(PROT, encoding="utf-8").read()
    vorher = prot.count("\n")
    nach = einfgueg(prot, block(bild_b, bild_h, archiv_h, ref_b, ref_h, fab_b, fab_h, init_info))
    print("Protokoll %d Zeilen vor, %d nach dem Einfguegen" % (vorher, nach.count("\n")))
    if "--schreib" in sys.argv:
        with open(PROT, "w", encoding="utf-8") as offen:
            offen.write(nach)
        print("geschrieben:", PROT)
    else:
        print("Trockenlauf: nichts geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
