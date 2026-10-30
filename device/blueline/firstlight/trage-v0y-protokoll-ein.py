#!/usr/bin/env python3
"""Setzt den FLASH-BEREIT-Block v0y obenauf, vor den v0x-Block.

Geschrieben wird mit open()/Python, nicht mit dem read_file-Rueckgabewert: der
liefert die Zeilen mit einem 'ZEILE|'-Praefix, und zurueckgeschrieben hat er
schon ganze Dateien vergiftet (drei defekte Builds).

Alle Zahlen im Block kommen aus dem Bild, nicht aus dem Kopf. Der Block prüft
sich selbst im Anschluss mit tests/flash-block, der jede Zahl gegen sha256 und
os.stat vergleicht.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

REPO = "/Users/gregor/hermes-workspace/omarchy-mobile"
PROT = os.path.join(REPO, "device/blueline/BRINGUP-M1.md")
BILD = "/Users/gregor/hermes-workspace/images/fl-v0y/firstlight.img"
ARCHIV = "/Users/gregor/hermes-workspace/images/fl-v0y/new.cpio"
REF = "/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
FABRIK = "/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img"


def mass(pfad: str) -> tuple[int, str]:
    d = open(pfad, "rb").read()
    return len(d), hashlib.sha256(d).hexdigest()


def kürzel(hash_: str) -> str:
    return hash_[:8] + "…" + hash_[-6:]


def block(bild_b, bild_h, archiv_b, archiv_h, ref_b, ref_h, fab_b, fab_h, init_b, init_z) -> str:
    return f"""## FLASH-BEREIT v0y — der Herzschlag darf im Fehlerfall nicht stehen bleiben (2026-10-31, 00:4x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0y: eine Zeile, gemessen am ausgelieferten v0x-Bild, Zeile 77. Der Herzschlag liest den Modus mit `modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)`, und die innere Ersetzung ist unquotiert. Findet die Suche nichts, bekommt `cat` **kein Argument** und liest dann die Standardeingabe. Die Init der PID 1 leitet die nirgends um - gemessen: 0 Fundstellen für `< /dev/null`, `exec <` und `0<` in der herausgelösten Init - und die Standardeingabe ist die Konsole. Ein Pty-Versuch auf dem Rechner zeigte genau dieses Verhalten: die Zeile vor dem `cat` erscheint, die danach kommt in drei Sekunden nicht. Entscheidend ist der Ort: **dieselbe Schleife füttert den Watchdog** (`echo -n V > "$wd"`); steht der Druck still, steht die Fütterung still, und der Baustein setzt neu ein - in dem Bild, das den Grund einer ausbleibenden Bus-Enumeration melden soll. Der Hänger feuert ausserdem nur im Fehlerfall (kein Modus-Knoten, weil der dwc3-Knoten nie angelegt wurde), also genau in dem Zweig, den dieser Lauf ablesen will. v0y schliesst die Standardeingabe dieser einen Ersetzung mit `</dev/null` und nennt auf dem Panel v0y; der Zeilendiff gegen das v0x-Bild beweist, dass sonst nichts anders ist: 462 Zeilen wie im Vorgänger, genau zwei verschiedene Zeilen, 77 und 102.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

SCHRITT 0b, in Fastboot VOR dem Write, zwei Lesungen und ein Leseversuch:
(1) `fastboot getvar slot-retry-count:a` und `getvar partition-size:boot_a` —
der Zähler stand 13:09 auf 2 und 16:07 vor dem Write auf 3, ohne isolierte
Ursache; erst diese Lesung sagt, ob ein Start den Versuch verbraucht
(`evidence/retry-zaehler-korrektur-2026-10-30.txt`). (2) `fastboot fetch boot_a` in eine Datei und die Größe prüfen — am 27.10. kam ein Fetch als 0-Byte-Datei zurück, also zählt die Dateigröße, nicht der Exit-Code. Der Rohlog-Block (1 MiB bei 63 MiB, alle 10 s) liegt hinter jedem dieser Writes und trägt den letzten Auswurf des zuletzt gestarteten Bildes. (3) Erst danach der Write.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0y/firstlight.img {bild_h} 300
```
v0y: {bild_b} B, sha256 `{bild_h}`, herausgelöste Init {init_b} B / {init_z} Zeilen, Archiv sha256 `{archiv_h}`. Vorgänger v0x: 21098496 B, sha256 `efa25838fc7ffc215fc0757ba90063977af6fc34199b9ac8a26079140d76ba17`, Init 22 786 B / 462 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es.

Rueckweg STUFE 1 (stellt den Zustand von heute früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `{ref_h}`, {ref_b} B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `{fab_h}`, {fab_b} B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

DER HERZSCHLAG, Zeile 77, im fertigen Bild (die einzige Zeile außer dem Titel, die sich vom Vorgänger unterscheidet):
`modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null </dev/null)`
Das `</dev/null` gehört an die Ersetzung, nicht an die äussere `echo`-Zeile: abgeschlossen wird genau die Eingabe, aus der die Dateinamen kommen. Alles, was davor steht - `debugfs=$(ls`, `usb=$(ls`, und die Messfelder `controller-state=`, `udc-state=`, `is_active=`, `typc: state=`, `pid1=`, `letzter Schritt:` - steht wortgleich wie im Vorgänger.

DER PANEL-TITEL, Zeile 102: `Omarchy Mobile first-light v0y - RAM only, der Knopf wird gesucht`. Bei ausbleibender Enumeration ist der Panel das einzige Lesegeraet, also muss ein Foto den Stand nennen; dieselbe Produktzahl wie v0s bis v0x (0xD002) macht ein Bild am Bus nicht unterscheidbar.

DIE SUCHE nach dem Modus-Knoten steht unverändert wie im v0x-Block unterhalb (Zeilen 358 bis 367); ihre zehn Beweise sind im Zeilendiff einzeln als unverändert gemessen, darunter der einzige `test -w` in seiner Bedingung und der Zähler, der mit `grep -c .` zählt.

ERWARTUNG v0y (00:4x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel `Omarchy Mobile first-light v0y` und in jedem Herzschlag-Block die Zeile `debugfs=$(ls` mit dem Inhalt des hängenden Zählkanals, `usb=$(ls` mit dem Inhalt seines usb-Zweigs und `modewert=$(cat` mit dem Inhalt des Modus-Knotens. Die Nachbind-Runde nennt `write rc=` - dieselbe Messgröße wie bei den Vorfahren, absichtlich unter demselben Wort -, dazu `vorher=$scvor`, `pfad=$SC`, `gefunden=$SZAHL`, `suche=$SCLISTE`, `scrca=$SCRCA`, `modepfad=$MODENEUGEFUNDEN` und `modewert=$MODW`. Die Fuenf-Sekunden-Zeile nennt `spaeter 5s:` mit `sc1rc=$sc1rc` und `modewert=$MODW`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, `is_active=`, `controller-state=`, `letzter Schritt:`.

EINFANG nach dem Flash: der Runner sammelt die Belege selbst über Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${{OUT:-/Users/gregor/hermes-workspace/flash-observe}}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Der Runner lenkt seine eigene Ausgabe in diese Datei (`exec >>"$LOG" 2>&1`), die Umlenkung des Aufrufenden erhält nichts - gelesen wird der Log des Runners. Für v0y kommt nichts dazu und fällt nichts weg: die Namen trägt der Runner, nicht das Bild.
- `usb=` im Herzschlag enthält einen Ordnernamen = der usb-Zweig ist da; sein Name ist dann gemessen, nicht mehr aus `usb/%s` gefolgert. Leer bei nicht-leerem `debugfs=` = der dwc3-Zweig wurde nie angelegt.
- `modewert=` mit einem Wert wie `otg` oder `host` = der Controller hält sich für etwas anderes als Peripherie; das ist der stärkste einzelne Messwert, den dieses Bild liefern kann. Die Wortwahl ist am Kernel gemessen: Anzeiger und Schreiber kennen nur `host`, `device`, `otg` - `peripheral` ist die Vokabel der Referenzdokumente, nicht dieses Kernels (Beleg: `evidence/modus-knoten-quelltext-2026-10-30.txt`). Ein `cat: io error` im Feld stammt vom Aufweck-Fehlschlag des Anzeigers und ist selbst ein Messwert; `modewert=` leer bei vorhandenem Zweig ohne Fehlertext = Dunkelheit, kein Befund.
- Der Herzschlag-Block bricht nach der Zeile vor `modewert=` ab und kehrte nie zurück = die Standardeingabe wurde doch gelesen; bei v0y ist das ausgeschlossen, weil die Ersetzung geschlossen ist, und wäre dann ein neuer Befund.
- `state=` geht auf `default` oder `configured` = der Host hat den Reset geschickt; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen, und `ping -c 2 172.16.42.1` antwortet, sobald der NCM-Link steht - dieselbe Adresse, die der Runner anpingt (gemessen an seiner ping-Zeile).
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

BELEGE VOR DEM Flash, alle gelaufen: der eine Umbau-Block in zwei Schritten, je 1 Fundstelle, Bilanz der Paren ausgeglichen; `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv 28 Prüfpunkte / 0 Fehler; `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild; `verify-v0y.py` **33 Beweismale / 0 Fehler** am fertigen Bild, als Zeilendiff gegen das v0x-Bild: Zeilenzahl gleich, genau zwei verschiedene Zeilen (77 und 102), acht Messfelder im Herzschlag, alle zehn v0x-Beweise unverändert, Schleifenzahlen gleich (`done` 24, `; do` 27, `while` 12), ASCII, Klammer-Bilanz 0. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen. Wiederholbarkeit ist nicht behauptet, sondern gemessen: derselbe Umbau auf dem v0x-Archiv liefert das ausgelieferte Archiv.

ZWEI REGELN AUS DIESEM BAU, beide gemessen:
1. **Ein Prüfer, der seinen eigenen Eingriff nicht abwartet, misst die Dunkelheit vor der Arbeit.** Die erste Fassung der Ersetzungsprüfung zählte den Ersatz, bevor die Ersetzung lief, und meldete 'Ersatz nicht eindeutig' bei einer Fundstelle von 0.
2. **Ein `cat`, dessen Argument aus einer unquotierten Kommandosubstitution kommt, liest die Konsole, wenn die Suche nichts findet.** Die leere Argumentliste ist kein Fehlerfall, den die Shell abfängt - sie ist die Standardeingabe. Wer in einer PID 1 ohne Standardeingabe-Umlenkung liest, steht still, und wo dieselbe Schleife den Watchdog füttert, setzt der Baustein neu ein.

"""


def einfgueg(text: str, neuer: str) -> str:
    muster = re.compile(r"^## FLASH-BEREIT v0x ", re.M)
    treffer = list(muster.finditer(text))
    assert len(treffer) == 1, "v0x-Ueberschrift %d mal, erwartet 1" % len(treffer)
    stelle = treffer[0].start()
    text = text[:stelle] + neuer + text[stelle:]
    assert text.count("## FLASH-BEREIT v0y ") == 1, "v0y-Block nicht eindeutig"
    assert text.index("## FLASH-BEREIT v0y ") < stelle + len(neuer), "v0y nicht obenauf"
    return text


def haupt() -> int:
    if "--schreib" not in sys.argv:
        print("Trockenlauf: setze --schreib ein, um zu schreiben")
    bild_b, bild_h = mass(BILD)
    archiv_b, archiv_h = mass(ARCHIV)
    ref_b, ref_h = mass(REF)
    fab_b, fab_h = mass(FABRIK)
    print("v0y-Bild %d B %s | Archiv %d B %s" % (bild_b, kürzel(bild_h), archiv_b, kürzel(archiv_h)))
    print("Rueckweg 1 %d B %s | Rueckweg 2 %d B %s" % (ref_b, kürzel(ref_h), fab_b, kürzel(fab_h)))
    prot = open(PROT, encoding="utf-8").read()
    vorher_zeilen = prot.count("\n")
    init_text = os.environ.get("INIT_INFO", "")
    init_b, init_z = (int(x) for x in init_text.split("/") if x.strip()) if init_text else (22786, 462)
    neuer = block(bild_b, bild_h, archiv_b, archiv_h, ref_b, ref_h, fab_b, fab_h, init_b, init_z)
    nach = einfgueg(prot, neuer)
    print("Block %d Zeichen, Protokoll %d Zeilen vor, %d nach dem Einfguegen"
          % (len(neuer), vorher_zeilen, nach.count("\n")))
    if "--schreib" in sys.argv:
        with open(PROT, "w", encoding="utf-8") as offen:
            offen.write(nach)
        print("geschrieben:", PROT)
    else:
        print("Trockenlauf: nichts geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
