<!-- SPDX-License-Identifier: MIT -->
# Pixel 3 (blueline): first light

## AUSSTEHENDER WRITE (2026-11-03, gemessen um 08:0x) - dieser Block ersetzt fuer den naechsten Write alles darunter

Was aussteht und warum: v0ak haelt die Userdata-Wurzel read-write und haltbar, und
die Uebergabe laeuft (auf der seriellen Konsole als leere alte Wurzel gelesen,
Nachtrag 27). Es fehlt nur das neue Userdata-Bild: traegt als Wurzel-`/init` den
Gadget-Aufbau (configfs, `ncm.usb0` + `acm.GS0`, `172.16.42.1`, `telnetd -l /bin/sh`)
und schreibt `/omamobile/LEBEN` auf die echte Partition. Beides fehlt in der Wurzel,
die jetzt laeuft - deshalb ist das Telefon fuer den Mac taub, obwohl es lebt.

Anruf (wartet auf das Telefon im Fastboot, dann der Zyklus von selbst; Frist hier
1440 Runden a 10 s = 4 h, sonst Standard 40 min):

```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
FRIST_RUNDEN=1440 sh warte-und-schreibe.sh
```

Der Laeufer ruebergibt an `schreibe-v0ai.sh` mit `BOOTIMG` auf v0ak und `FRIST=420`.
Beide Skripte sind ungeaendert im Einsatz seit den Commits `e19c509` (Write-Meldung)
und `cca2331` (Pruefung dazu); kanonische Suite auf diesem Stand: 164 ok, 4 skip,
0 not-ok, Ausgang 0.

Inhalte, alle soeben von der Platte gemessen (nicht aus der Erinnerung):

| Partition | Datei | Groesse | sha256 |
| --- | | --- | --- | --- |
| userdata | `/Users/gregor/hermes-workspace/images/userdata-alpine/rootfs-vorlauf.sparse.img` | 117441332 B | `7d9f217928cf3866d2fa02f166502cbef2ddd7bb8e93c03adb6bac8ce6e52b03` |
| boot_a | `/Users/gregor/hermes-workspace/images/fl-v0ak/firstlight.img` | 21143552 B | `f5ac4efda70345d864ea9bf431c4fb6d930b686e6dc97b4b00da37f4f25a426a` |
| Rueckweg STUFE 1 | `/Users/gregor/hermes-workspace/images/fl-v0af/firstlight.img` (mit Power+Leiser starten) | 21143552 B | `f097ef0f9a1a858a15d72aad023be27f9a02e419116d25c580d99fe86d1a2c9d` |
| Sicherung boot_a | `/Users/gregor/hermes-workspace/backups/blueline-2026-11-01/kalibrier-boot_a.bin` | 67108864 B | `0478f8dbe456a5877976f2514aa105619acf6c91056afb14eabe824d5c6929a0` |

Zu den beiden Bildern liegen `.sha256`-Begleitdateien mit denselben Summen; der
Zyklus prueft sie vor dem ersten Write und prueft vor dem boot_a-Write die
Sicherung gegen `sha256-lokal.txt` - bei Abweichung bricht er ab, ohne geschrieben
zu haben. Rueckweg STUFE 2 bleibt das Factory-Image (loescht userdata).

Vor dem Write, in diesem Fastboot-Moment, als Erstes die Slot-Lesungen (seit
2026-11-03 00:3x nicht mehr gelesen, der Wiederholungs-Zaehler ist unbkannt):
`getvar current-slot`, `getvar slot-retry-count:a`, `getvar slot-unbootable:a`.
Steht `retry-count:a` auf 0, zuerst `--set-active=a` und die Lesung danach
dokumentieren - ohne Fuellung macht der erste Start des Slots den Slot unbootbar.

ERWARTUNG, jetzt vor dem Flash festgelegt (jede Zeile ist im ausgelieferten
Userdata-Bild nachzulesen, nicht im Kopf): spaetestens vier Minuten nach dem
Neustart antwortet `ping 172.16.42.1`, Port 23 ist offen, und auf dem Telefon
steht `cat /omamobile/LEBEN` mit Zeitstempel, Wurzelgeraet und Kernel; in
`grep " / " /proc/mounts` steht das Userdata-Geraet mit `rw`; der Gadget-Schalter
`state` steht auf `configured`. Die Gegenseiten: kein Eintrag am Bus = der
Gadget-Block in der neuen Wurzel lief nicht (dann die Marke in
`/omamobile/LEBEN` auf der Partition suchen, sie liegt trotzdem da); Port offen
ohne Stempel = Uebergabe vor dem Stempel gescheitert; Stempel da ohne Netz =
Gadget-Aufbau in der neuen Wurzel fehlgeschlagen, die `/ud`-Lesung aus dem
Initramfs bleibt als Beweis erhalten.

Wartend jetzt in einer Dauerschleife, nicht mehr in einzelnen Fenstern:

```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
while :; do aus=$(mktemp -t warte-fenster)
  FRIST_RUNDEN=1440 sh warte-und-schreibe.sh >"$aus" 2>&1; zy=$?
  sed 's/^/  /' "$aus"
  grep -q "telefon im fastboot" "$aus" && { echo "Zyklus durchgelaufen, Exit $zy"; break; }
  echo "Fenster um, nichts geschrieben (Exit $zy)"; sleep 20
done
```

Der Grund fuer die Zeile mit `grep` statt eines Blicks auf den Ausgang:
`warte-und-schreibe.sh` meldet Ausgang 1 fuer BEIDES - kein Geraet im Fenster und
ein fehlgeschlagener Write (der Zyklus selbst endet mit 1). Wer eine Schleife auf
den Ausgang baut, hoert nach dem ersten echten Fehler einfach auf.

Der Handgriff bleibt der einzige Weg ins Fastboot: Power + Leiser 10-20 s, bis
FASTBOOT MODE im Display steht. Von der seriellen Shell aus ist kein Neustart
moeglich, der dort ankommt - die ueberlebende Shell hat eine geleerte Wurzel,
kein Programm und kein `/proc` (Nachtrag 27), und ein Panic-Neustart wuerde
Slot a normal starten und wieder in dieselbe stumme Wurzel fallen.

Hinweis auf die Falle darunter: der folgende Block `FLASH-BEREIT v0z` beschreibt
den Stand vom 31.10. (v0z, Panelablesung, Runner `run-flash-observe.sh`) und ist
geschichte - er wird weiterhin vom Blockwart gegen Bild und Runner geprueft, aber
fueralles, was jetzt ansteht, gilt der Block oben.

## FLASH-BEREIT v0z — der echte Knopf, am Panel abgelesen und am Quelltext gemessen (2026-10-31, 13:3x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

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
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0z/firstlight.img ba18304d745e23c210b64c614420ccc03b0133b4fcc3bc60554e2db152c77154 300
```
v0z: 21098496 B, sha256 `ba18304d745e23c210b64c614420ccc03b0133b4fcc3bc60554e2db152c77154`, herausgelöste Init 27516 B / 528 Zeilen, Archiv sha256 `98fe5ef66679bd22d583a96ad15ac2432b1392297dc0e7404ed8e8ed9ff2552d`. Vorgänger v0y: 21098496 B, sha256 `ee2b9cb4e88e11f50353277fae1fd745eebc92e9bc288df2c719d25eea158dca`, Init 22 786 B / 462 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es, und alle Bilder von v0s bis v0z tragen dieselbe Produktzahl 0xD002, ein Bild ist am Bus also nicht unterscheidbar.

Rueckweg STUFE 1 (stellt den Zustand von vorgestern früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28729344 B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`, 67108864 B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

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

EINFANG nach dem Flash: der Runner sammelt die Belege selbst über Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${OUT:-/Users/gregor/hermes-workspace/flash-observe}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Der Runner lenkt seine eigene Ausgabe in diese Datei (`exec >>"$LOG" 2>&1`), die Umlenkung des Aufrufenden erhält nichts - gelesen wird der Log des Runners. Bei ausbleibender Enumeration ist das Panel das einzige Lesegeraet: ein Foto muss den Stand nennen, und der Titel nennt ihn.

BELEGE VOR DEM Flash, alle gelaufen: der Eine Durchgang über das geladene v0y-Archiv (drei Schritte, je 1 Fundstelle, Bilanz 182 offene gegen 182 zu Paren), `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv 0 Fehler, `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild, `verify-v0z.py` **47 Beweismale / 0 Fehler** (46 am gebauten Bild, der 47ste Punkt kam nach dem Flash dazu: das Nebenarchiv `new.cpio`, an dem der Reihenfolgepruefer haengt, wird gegen das Bild gemessen - fuehrt denselben Init, 27 516 B, bytegleich; Gegentest mit mutiertem Archiv meldet Fehler) am fertigen Bild, darunter die Selbstmessung des Prüfers an fünf bekannten Formen (5/5) und der Zeilendiff gegen v0y: genau eine geaenderte Zeile (der Titel), 67 eingefügte, keine gelöschte, jedes Messfeld des Vorgängers wortgleich erhalten. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen.

DREI REGELN AUS DIESEM BAU, alle gemessen:
1. **Ein Suchbegriff, an der falschen Stelle gesucht, meldet eine Abwesenheit, die keine ist.** `soft_connect` wurde im Kernelbaum und im debugfs gesucht und für nicht existent erklärt; es steht in der UDC-Klasse und war die ganze Zeit im eigenen Herzschlag-Feld `udcdateien=` ablesbar. Vor einem 'existiert nicht' gehört die Liste des laufenden Systems, nicht die der Quelle.
2. **`2>/dev/null` enthält den Teilstring `</dev/null` und deckt trotzdem nur den Fehlerausgang.** Der erste Leserscanner meldete die echte Hängerzeile als sauber; nach der Umstellung auf Token-Klassen misst der Prüfer sich selbst (5/5). Ein Prüfer ohne Selbstmessung schläft grün.
3. **Eine Platzhalter-Schleife ohne Fund druckt keine Beweiszeile und meldet damit Nichtstun als Fehlschlag.** `for g in /sys/kernel/config/usb_gadget/*` mit `[ -e "$g/UDC" ] || continue` lief vier Bootes lang still durch. Wer aus dem Fehlen einer Meldung schliesst, muss zuerst zeigen, dass der Zweig die Meldung überhaupt hätte drucken können.

ERGEBNIS DIESES FLASHS (gemessen 2026-10-31, `evidence/v0z-geflasht-null-beobachtungen-2026-10-31.txt`): Rueckweg vor dem Write geprueft, 28729344 B, sha256 identisch mit diesem Block. Write um 14:41:02 auf boot_a (21098496 B), Nachernte des Runners nach dem Write `slot-retry-count:a: 3` bei 2 vor dem Write - die entschiedene Zaehlerregel zum zweiten Mal intrauf gemessen. 14:46:10 `ERGEBNIS: 0 Beobachtungen mit neuen Eintraegen, 307 s gelaufen`, danach kein Fastboot-Eintrag und `172.16.42` an keiner Schnittstelle: dieselbe Null wie v0r (302 s), v0t und v0y (305 s). Was v0z neu sagt, steht nur auf dem Panel: `g1 NEU angelegt` oder `g1 war da`, `binden rc=`, `connect rc=` mit `text=` und danach `state=` und `netz=`, dazu `haengt:` und `schritte:` mit den letzten sechs Schritten. Noch nicht abgelesen, deshalb nicht gemessen: keine dieser Zeichenketten. Zwei Selbstfehler auf diesem Lauf, beide im eigenen Pruefweg: ein Hash aus der Erinnerung statt aus der Datei (der Vergleich meldete eine Scheinabweichung), und ein eigenes Nachernten der getvars nach dem Neustart, das haingt, weil fastboot auf ein Gerat wartet - der Runner hat diese Werte selbst nach dem Write protokolliert.

## ENTSCHEIDUNGSTABELLE: die Modulzeilen im Panel (2026-10-31, ohne Telefon)

Das v0z-Panel zeigt `schritte:` mit den letzten sechs Zeilen aus `/run/steps.log`. Die Init setzt im Modulblock sieben Marks (Verzeichnis, fünf Module, Bilanz); die letzten sechs sind also die fünf Modulzeilen plus die Bilanz. Daraus folgt:

| Panel zeigt | Bedeutung | Was Gregor tut |
| --- | --- | --- |
| `modul libcomposite.ko geladen` und die vier anderen `geladen` | Module sind geladen, die Init ist über den Block hinaus | Weiter mit den Bind-Zeilen: `g1 NEU angelegt` oder `g1 war da`, `binden rc=`, `connect rc=` mit `text=`, danach `state=` und `netz=`. Keine Enumeration heißt: die Ursache liegt im Gadget-Aufbau/Binden, nicht in den Modulen. |
| `modul … FEHLER 1` (oder FEHLER mit anderer Zahl) | insmod ist für dieses Modul gescheitert | Modulnamen und Fehlerzahl notieren. Die statische Prüfung sagt: vermagic (7.1.0-rc1-sdm845) und Signatur passen, die `.ko` sind byte-gleich zur Referenz (`evidence/modulpruefung-statisch-2026-10-31.txt`). Nächster Schritt: `modprobe` statt `insmod` im nächsten Bild, oder Moduldatei/Reihenfolge prüfen. |
| Modulzeilen erscheinen gar nicht | Die Init hat den Modulblock nicht erreicht | `schritte:` und `haengt:` lesen, den letzten Marker vor der Stille als Todespunkt nehmen, den frühen Boot prüfen (ACM, Mounts). Die Module sind dann nicht die Ursache. |

Das Foto muss die sechs Zeilen zeigen; ohne sie ist die Tabelle nicht anwendbar.

## FLASH-BEREIT v0y — der Herzschlag darf im Fehlerfall nicht stehen bleiben (2026-10-31, 00:4x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0y: eine Zeile, gemessen am ausgelieferten v0x-Bild, Zeile 77. Der Herzschlag liest den Modus mit `modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)`, und die innere Ersetzung ist unquotiert. Findet die Suche nichts, bekommt `cat` **kein Argument** und liest dann die Standardeingabe. Die Init der PID 1 leitet die nirgends um - gemessen: 0 Fundstellen für `< /dev/null`, `exec <` und `0<` in der herausgelösten Init - und die Standardeingabe ist die Konsole. Ein Pty-Versuch auf dem Rechner zeigte genau dieses Verhalten: die Zeile vor dem `cat` erscheint, die danach kommt in drei Sekunden nicht. Entscheidend ist der Ort: **dieselbe Schleife füttert den Watchdog** (`echo -n V > "$wd"`); steht der Druck still, steht die Fütterung still, und der Baustein setzt neu ein - in dem Bild, das den Grund einer ausbleibenden Bus-Enumeration melden soll. Der Hänger feuert ausserdem nur im Fehlerfall (kein Modus-Knoten, weil der dwc3-Knoten nie angelegt wurde), also genau in dem Zweig, den dieser Lauf ablesen will. v0y schliesst die Standardeingabe dieser einen Ersetzung mit `</dev/null` und nennt auf dem Panel v0y; der Zeilendiff gegen das v0x-Bild beweist, dass sonst nichts anders ist: 462 Zeilen wie im Vorgänger, genau zwei verschiedene Zeilen, 77 und 102.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

SCHRITT 0b, in Fastboot VOR dem Write, zwei Lesungen und ein Leseversuch:
(1) `fastboot getvar slot-retry-count:a` und `getvar partition-size:boot_a` —
der Zähler stand 13:09 auf 2 und 16:07 vor dem Write auf 3, ohne isolierte
Ursache; erst diese Lesung sagt, ob ein Start den Versuch verbraucht
(`evidence/retry-zaehler-korrektur-2026-10-30.txt`). (2) `fastboot fetch boot_a` in eine Datei und die Größe prüfen: gemessen am 31.10. um 12:46 meldet diese ABOOT-Generation `Unable to get max-fetch-size. Device does not support fetch command.` und die Datei bleibt 0 Byte. Der lesende Zweig ist auf diesem Gerät also geschlossen, nicht etwa nur unzuverlässig; der Versuch bleibt trotzdem vor jedem Write stehen, weil nur die Datei selbst das belegt. Ein Bild, das seinen Grund über einen Partitions-Schwanz ablegen will, muss den Leser mitbringen. (3) Erst danach der Write.

DER ZÄHLER IST ENTSCIEDEN, intrauf gemessen (31.10., ein einziger Lauf): 12:46:22 vor dem Write `slot-retry-count:a: 2`, 12:47:05 nach dem Write `slot-retry-count:a: 3`, beides die fastboot-Ausgabe desselben Runner-Laufs (`evidence/v0y-null-enumeration-und-retry-entschieden-2026-10-31.txt`). Der Write auf boot_a setzt den Zähler auf seinen Anfangswert, ein erfolgreicher Start verbraucht ihn. Das erklärt jede Lesung der letzten vier Tage ohne weitere Annahme, und es heilt den Lesewert: 3 bedeutet frisch geflasht, nicht vier fehlgeschlagene Versuche.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0y/firstlight.img ee2b9cb4e88e11f50353277fae1fd745eebc92e9bc288df2c719d25eea158dca 300
```
v0y: 21098496 B, sha256 `ee2b9cb4e88e11f50353277fae1fd745eebc92e9bc288df2c719d25eea158dca`, herausgelöste Init 22786 B / 462 Zeilen, Archiv sha256 `35aad0ee7d9e5517f1a5f011fda242307766f0cb865719ff56226e263cf784d6`. Vorgänger v0x: 21098496 B, sha256 `efa25838fc7ffc215fc0757ba90063977af6fc34199b9ac8a26079140d76ba17`, Init 22 786 B / 462 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es.

Rueckweg STUFE 1 (stellt den Zustand von heute früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28729344 B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`, 67108864 B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

DER HERZSCHLAG, Zeile 77, im fertigen Bild (die einzige Zeile außer dem Titel, die sich vom Vorgänger unterscheidet):
`modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null </dev/null)`
Das `</dev/null` gehört an die Ersetzung, nicht an die äussere `echo`-Zeile: abgeschlossen wird genau die Eingabe, aus der die Dateinamen kommen. Alles, was davor steht - `debugfs=$(ls`, `usb=$(ls`, und die Messfelder `controller-state=`, `udc-state=`, `is_active=`, `typc: state=`, `pid1=`, `letzter Schritt:` - steht wortgleich wie im Vorgänger.

DER PANEL-TITEL, Zeile 102: `Omarchy Mobile first-light v0y - RAM only, der Knopf wird gesucht`. Bei ausbleibender Enumeration ist der Panel das einzige Lesegeraet, also muss ein Foto den Stand nennen; dieselbe Produktzahl wie v0s bis v0x (0xD002) macht ein Bild am Bus nicht unterscheidbar.

DIE SUCHE nach dem Modus-Knoten steht unverändert wie im v0x-Block unterhalb (Zeilen 358 bis 367); ihre zehn Beweise sind im Zeilendiff einzeln als unverändert gemessen, darunter der einzige `test -w` in seiner Bedingung und der Zähler, der mit `grep -c .` zählt.

ERWARTUNG v0y (00:4x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel `Omarchy Mobile first-light v0y` und in jedem Herzschlag-Block die Zeile `debugfs=$(ls` mit dem Inhalt des hängenden Zählkanals, `usb=$(ls` mit dem Inhalt seines usb-Zweigs und `modewert=$(cat` mit dem Inhalt des Modus-Knotens. Die Nachbind-Runde nennt `write rc=` - dieselbe Messgröße wie bei den Vorfahren, absichtlich unter demselben Wort -, dazu `vorher=$scvor`, `pfad=$SC`, `gefunden=$SZAHL`, `suche=$SCLISTE`, `scrca=$SCRCA`, `modepfad=$MODENEUGEFUNDEN` und `modewert=$MODW`. Die Fuenf-Sekunden-Zeile nennt `spaeter 5s:` mit `sc1rc=$sc1rc` und `modewert=$MODW`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, `is_active=`, `controller-state=`, `letzter Schritt:`.

EINFANG nach dem Flash: der Runner sammelt die Belege selbst über Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${OUT:-/Users/gregor/hermes-workspace/flash-observe}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Der Runner lenkt seine eigene Ausgabe in diese Datei (`exec >>"$LOG" 2>&1`), die Umlenkung des Aufrufenden erhält nichts - gelesen wird der Log des Runners. Für v0y kommt nichts dazu und fällt nichts weg: die Namen trägt der Runner, nicht das Bild.
- `usb=` im Herzschlag enthält einen Ordnernamen = der usb-Zweig ist da; sein Name ist dann gemessen, nicht mehr aus `usb/%s` gefolgert. Leer bei nicht-leerem `debugfs=` = der dwc3-Zweig wurde nie angelegt.
- `modewert=` mit einem Wert wie `otg` oder `host` = der Controller hält sich für etwas anderes als Peripherie; das ist der stärkste einzelne Messwert, den dieses Bild liefern kann. Die Wortwahl ist am Kernel gemessen: Anzeiger und Schreiber kennen nur `host`, `device`, `otg` - `peripheral` ist die Vokabel der Referenzdokumente, nicht dieses Kernels (Beleg: `evidence/modus-knoten-quelltext-2026-10-30.txt`). Ein `cat: io error` im Feld stammt vom Aufweck-Fehlschlag des Anzeigers und ist selbst ein Messwert; `modewert=` leer bei vorhandenem Zweig ohne Fehlertext = Dunkelheit, kein Befund.
- Der Herzschlag-Block bricht nach der Zeile vor `modewert=` ab und kehrte nie zurück = die Standardeingabe wurde doch gelesen; bei v0y ist das ausgeschlossen, weil die Ersetzung geschlossen ist, und wäre dann ein neuer Befund.
- `state=` geht auf `default` oder `configured` = der Host hat den Reset geschickt; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen, und `ping -c 2 172.16.42.1` antwortet, sobald der NCM-Link steht - dieselbe Adresse, die der Runner anpingt (gemessen an seiner ping-Zeile).
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

BELEGE VOR DEM Flash, alle gelaufen: der eine Umbau-Block in zwei Schritten, je 1 Fundstelle, Bilanz der Paren ausgeglichen; `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv 28 Prüfpunkte / 0 Fehler; `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild; `verify-v0y.py` **33 Beweismale / 0 Fehler** am fertigen Bild, als Zeilendiff gegen das v0x-Bild: Zeilenzahl gleich, genau zwei verschiedene Zeilen (77 und 102), acht Messfelder im Herzschlag, alle zehn v0x-Beweise unverändert, Schleifenzahlen gleich (`done` 24, `; do` 27, `while` 12), ASCII, Klammer-Bilanz 0. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen. Wiederholbarkeit ist nicht behauptet, sondern gemessen: derselbe Umbau auf dem v0x-Archiv liefert das ausgelieferte Archiv.

ZWEI REGELN AUS DIESEM BAU, beide gemessen:
1. **Ein Prüfer, der seinen eigenen Eingriff nicht abwartet, misst die Dunkelheit vor der Arbeit.** Die erste Fassung der Ersetzungsprüfung zählte den Ersatz, bevor die Ersetzung lief, und meldete 'Ersatz nicht eindeutig' bei einer Fundstelle von 0.
2. **Ein `cat`, dessen Argument aus einer unquotierten Kommandosubstitution kommt, liest die Konsole, wenn die Suche nichts findet.** Die leere Argumentliste ist kein Fehlerfall, den die Shell abfängt - sie ist die Standardeingabe. Wer in einer PID 1 ohne Standardeingabe-Umlenkung liest, steht still, und wo dieselbe Schleife den Watchdog füttert, setzt der Baustein neu ein.

## FLASH-BEREIT v0x — debugfs früh, und der Knopf, der wirklich existiert (2026-10-30, 23:0x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0x: drei Befunde an der Quelle `android-mainline/kernel-pmos`, alle gemessen nach dem v0w-Bau. Erstens: `soft_connect` als Datei existiert in diesem Kernel nicht — die Suche über den ganzen Kernelbaum nach dem Dateinamen als String meldet 0 Dateien; die drei Fundstellen im Kernel-Binary sind Namen in der Kallsyms-Tafel, die Datei selbst wird nie angelegt, und v0vs Druck sowie v0ws Fallback liefen ins Phantom (deshalb meldete v0w im Feld `text0=` ein `No such file or directory` ohne Aussagewert). Zweitens: real ist der Modus — die Quelldatei des debugfs-Zweigs setzt den Modus-Knoten (Zeile 1029, 0644) unter dem Gerätenamen im usb-Zweig, und dieser Zweig entsteht bedingungslos in `drivers/usb/common/common.c:422`; `CONFIG_USB_DWC3_DUAL_ROLE=y` und `CONFIG_DEBUG_FS=y` stehen in der Konfiguration dieses Baums, derselbe Baum, aus dem die laufende Referenz stammt (Zeile 698 oben). Drittens: v0w hing debugfs erst in Zeile 350 ein, mitten in der Bind-Runde — die Herzschläge davor waren Dunkelheit, nicht Befund. Der erste v0x-Bau zeigte überdies einen Eigenfehler, der erst dem neuen Beweismal auffiel: der nackte `test -w` des Vorgängers blieb unter dem bedingten stehen und schrieb `SCRCA=9` (kein Fund) zu `SCRCA=1` um, stumm und unterhalb jedes Beweises.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

SCHRITT 0b, in Fastboot VOR dem Write, zwei Lesungen und ein Leseversuch:
(1) `fastboot getvar slot-retry-count:a` und `getvar partition-size:boot_a` —
der Zähler stand 13:09 auf 2 und 16:07 vor dem Write auf 3, ohne isolierte
Ursache; erst diese Lesung sagt, ob ein Start den Versuch verbraucht
(`evidence/retry-zaehler-korrektur-2026-10-30.txt`). (2) `fastboot fetch boot_a` in eine Datei und die Größe prüfen — am 27.10. kam ein Fetch als 0-Byte-Datei zurück, also zählt die Dateigröße, nicht der Exit-Code. Der Rohlog-Block (1 MiB bei 63 MiB, alle 10 s, in allen fünf gebauten Bildern) konnte von den 21 098 496 B großen Writes nicht erreicht werden und trägt den letzten Auswurf des zuletzt gestarteten Bildes. (3) Erst danach der Write.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0x/firstlight.img efa25838fc7ffc215fc0757ba90063977af6fc34199b9ac8a26079140d76ba17 300
```
v0x: 21098496 B, sha256 `efa25838fc7ffc215fc0757ba90063977af6fc34199b9ac8a26079140d76ba17`, herausgelöste Init 22775 B / 462 Zeilen, Archiv sha256 `7bfb4f84fba1716bc450868df0aca8496e1e9614734e641a5657dcd5f02376ac`. Vorgänger v0w: 21098496 B, sha256 `49a1ffcab918b6edebd7ce3d1b6f62a6e260b902850a9a519974913130715680`, Init 22 110 B / 455 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es.

Rueckweg STUFE 1 (stellt den Zustand von heute früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28729344 B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`, 67108864 B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

Gerät ist jetzt (gemessen 2026-10-30, zuletzt 21:07): **läuft v0t, an keinem Bus** — `fastboot devices` ohne Eintrag, kein Pixel am USB-Baum, `ping -c 2 172.16.42.1` antwortet nicht; das Panel zeigte bei v0t Titel und Herzschlag mit `state=not attatched` und leerem `gebunden=`-Feld (Gregors Ablesung). Für diesen Flash ist der Tastendruck nötig.

DER FRÜHE EINHANG, Zeile 19, noch vor jedem Herzschlag:
`mount -t debugfs none /sys/kernel/debug 2>/dev/null || true`
Der zweite Einhang in der Runde (Zeile 353) bleibt stehen; hängt der Zweig schon, schlägt er fehl, und sein Rückgabewert ist der Bericht darüber.

DIE SUCHE, wie sie im fertigen Bild steht — aus dem Archiv geschnitten, nicht abgetippt —, Zeilen 358 bis 367:
    SCDATEIEN=$(find /sys/kernel/debug -name soft_connect 2>/dev/null | head -6)
    SCLISTE=$(printf %s "$SCDATEIEN" 2>/dev/null | tr '\n' ' ')
    SZAHL=$(printf %s "$SCDATEIEN" 2>/dev/null | grep -c . 2>/dev/null)
    SC=$(printf %s "$SCDATEIEN" 2>/dev/null | head -1)
    [ -n "$SC" ] || SC=""   # v0x: der v0w-Fallback war ein Phantom
    if [ -n "$SC" ]; then test -w "$SC"; SCRCA=$?; else SCRCA=9; fi
    MODEPFAD=$(find /sys/kernel/debug -name mode 2>/dev/null | head -2)
    MODENEUGEFUNDEN=$(printf %s "$MODEPFAD" 2>/dev/null | grep -c . 2>/dev/null)
    MODE=$(printf %s "$MODEPFAD" 2>/dev/null | head -1)
    MODW=$( { cat "$MODE"; } 2>&1 ); MODWRC=$?
Der Modus wird gelesen, nie geschrieben: ihn auf `device` zu stellen ist ein eigener Versuch und gehört nicht in ein Bild, das erst messen soll (Beleg: `evidence/modus-knoten-quelltext-2026-10-30.txt`, Wortwahl und Lesbarkeit dort Zeile fuer Zeile am Quelltext gemessen). Der Zähler der Modusfunde nutzt dieselbe Zählweise wie `SZAHL` (Zeilen anzahl, nicht Umbruchzahl) — mit `wc -l` hätte ein einziger Fund null gemeldet, weil eine Befehlsersetzung den Abschiedsumbruch frisst.

DER HERZSCHLAG meldet in jedem Block die Suche und den Modus, Zeile 77:
`echo "debugfs=$(ls /sys/kernel/debug 2>/dev/null | tr '\n' ' ') usb=$(ls /sys/kernel/debug/usb 2>/dev/null | tr '\n' ' ') modewert=$(cat $(find /sys/kernel/debug -name mode 2>/dev/null | head -1) 2>/dev/null)"`

DIE NACHBIND-RUNDE, Zeile 378:
`echo "omamobile-blueline: weicher-bind $rb: write rc=$rc text=$err vorher=$scvor pfad=$SC gefunden=$SZAHL suche=$SCLISTE scrca=$SCRCA modepfad=$MODENEUGEFUNDEN modewert=$MODW rc0=$sc0rc text0=$sc0 rc1=$sc1rc text1=$sc1, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), interfaces=$(ls /sys/class/net 2>/dev/null | tr '\n' ' ')" > /dev/kmsg`

DIE FÜNF-SEKUNDEN-ZEILE, Zeile 381:
`echo "omamobile-blueline: weicher-bind $rb spaeter 5s: sc1rc=$sc1rc sc1text=$sc1 scrca=$SCRCA gefunden=$SZAHL modewert=$MODW, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), udc-state=$(cat /sys/class/udc/*/state 2>/dev/null)" > /dev/kmsg`

ERWARTUNG v0x (23:0x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel `Omarchy Mobile first-light v0x` und in jedem Herzschlag-Block die Zeile `debugfs=$(ls` mit dem Inhalt des hängenden Zählkanals, `usb=$(ls` mit dem Inhalt seines usb-Zweigs und `modewert=$(cat` mit dem Inhalt des Modus-Knotens. Die Nachbind-Runde nennt `write rc=` - dieselbe Messgröße wie bei den Vorfahren, absichtlich unter demselben Wort -, dazu `vorher=$scvor`, `pfad=$SC`, `gefunden=$SZAHL`, `suche=$SCLISTE`, `scrca=$SCRCA`, `modepfad=$MODENEUGEFUNDEN` und `modewert=$MODW`. Die Fuenf-Sekunden-Zeile nennt `spaeter 5s:` mit `sc1rc=$sc1rc` und `modewert=$MODW`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, `is_active=`, `controller-state=`, `letzter Schritt:`. Die Fälle, die dieses Bild ohne jeden Bus trennt, stehen in der Aufzählung darunter.

EINFANG nach dem Flash: der Runner sammelt die Belege selbst über Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${OUT:-/Users/gregor/hermes-workspace/flash-observe}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Für v0x kommt nichts dazu und fällt nichts weg: die Namen trägt der Runner, nicht das Bild.
- `usb=` im Herzschlag enthält einen Ordnernamen = der usb-Zweig ist da; sein Name ist dann gemessen, nicht mehr aus `usb/%s` gefolgert. Leer bei nicht-leerem `debugfs=` = der dwc3-Zweig wurde nie angelegt, und der Modus-Fall ist entschieden, ohne ihn gedrückt zu haben.
- `modewert=` mit einem Wert wie `otg` oder `host` = der Controller hält sich für etwas anderes als Peripherie; das ist der stärkste einzelne Messwert, den dieses Bild liefern kann, und die Entscheidung für den nächsten Versuch (ihn auf `device` zu stellen - die Wortwahl ist am Kernel gemessen: Anzeiger und Schreiber kennen nur `host`, `device`, `otg`; `peripheral` ist die Vokabel der Referenzdokumente, nicht dieses Kernels). Ein `cat: io error` im Feld stammt vom Aufweck-Fehlschlag des Anzeigers und ist selbst ein Messwert; `modewert=` leer bei vorhandenem Zweig ohne Fehlertext = Dunkelheit, kein Befund.
- `gefunden=0` mit leerem `suche=` und `scrca=9` mit `text1=`-Text `kein Knopf` = der Phantombefund ist amtlich; v0vs `pfad=` war eine Annahme, der Fall ist abgeschlossen, nicht offen.
- `rc0=` oder `rc1=` ungleich null mit `read-only file system` = debugfs hängt nicht (dann ist der frühe Einhang fehlgeschlagen, Zeile 19); `invalid argument` = der Controller trägt den gadget-Zweig in diesem Moment nicht.
- `state=` geht auf `default` oder `configured` = der Host hat den Reset geschickt; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen — dieselbe Produktzahl wie v0s bis v0w, eine Enumeration ist also nur über den Panel-Titel einem Bild zuzuordnen.
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

BELEGE VOR DEM Flash, alle gelaufen: Trockenlauf des einen Umbau-Blocks (7 Schritte, je 1 Fundstelle, Bilanz 153 offene gegen 153 zu Paren — die Zahl ist am fertigen Archiv gemessen, nicht erwartet), `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv (0 Fehler), `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild (mit den Mounts des Baurezepts; der ad-hoc-Aufruf ohne Modulmount meldete 6 Dunkelheiten, kein Bildfehler), `verify-v0x.py` **52 Beweismale / 0 Fehler** am fertigen Bild — darunter die Reihenfolge: früher Einhang Zeile 19 vor Herzschlag Zeile 77 und Bind-Runde Zeile 378, Suche Zeile 358 vor der bedingten Setzung Zeile 362, Modus-Suche Zeile 364, Lesung Zeile 367, Meldung Zeile 378 378/381, und der einzige `test -w` in seiner Bedingung. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen.

DREI REGELN AUS DIESEM BAU, alle gemessen:
1. **Ein Löschschritt, der einen Anker löscht, macht den nächsten Blind.** Mein erster v0x-Tilgungsschritt entfernte die Zeile, die der Folgeschritt als Anker zählte, und meldete dessen 0 Fundstellen als fehlenden Text. Wer in einem Durchlauf löscht und einfügt, sortiert die Einfügung vor die Löschung desselben Textes.
2. **Wer eine Messung bedingt macht, muss die Bedingung mitzählen.** Der bedingte Beschreibbar-Test liegt in derselben Zeile wie der Test selbst; eine Prüferin, die den nackten Zeilenanfang sucht, fand null Zeilen und hätte den Defekt übersehen, den sie melden sollte.
3. **Ein Zeilenzähler, der auf Umbrüche schaut, misst eine Befehlsersetzung zu null.** `wc -l` zählt Umbrüche, und die Ersetzung frisst den letzten; die Beweiszeile desselben Bildes zählte schon längst mit `grep -c .` — die vorhandene Zählweise ist die, die man erbt, nicht die, die man als erstes schreibt.

## FLASH-BEREIT v0w — der Knopf wird gesucht, nicht angenommen (2026-10-30, 20:4x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0w: v0v drückte `/sys/kernel/debug/usb/` + UDC-Name + `/soft_connect`, **ohne diesen Pfad je beobachtet zu haben**. Am entpackten Kernel-Binary (44 498 944 B) sind die drei `soft_connect`-Fundstellen Namen in der Kallsyms-Tafel (`dwc3_gadget_soft_connect`, `dwc3_gadget_soft_disconnect`, `soft_connect_store`); `CONFIG_IKCONFIG=n` liefert keine eingebettete Config, ob der Knoten zur Laufzeit angelegt wird, ist aus dem Bild nicht beweisbar (firstlight/evidence/debugfs-zweig-kernelbinary-2026-10-30.txt). Ein Bild, das einen unbestätigten Knoten drückt, meldet "kein Knopf" genauso wie "Knopf ohne Wirkung". v0w sucht den Knoten im hängenden Zählkanal, meldet die gefundene Zahl und die Pfade im Herzschlag, und drückt nur, wenn die Datei beschreibbar ist.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

SCHRITT 0b, in Fastboot VOR dem Write, zwei Lesungen und ein Leseversuch:
(1) `fastboot getvar slot-retry-count:a` und `getvar partition-size:boot_a` —
der Zaehler stand 13:09 auf 2 und 16:07 vor dem Write auf 3, ohne isolierte
Ursache; erst diese Lesung sagt, ob ein Start den Versuch verbraucht
(evidence/retry-zaehler-korrektur-2026-10-30.txt). (2) `fastboot fetch boot_a
/tmp/boot_a.raw` und die Größe prüfen — am 27.10. kam ein Fetch als 0-Byte-Datei
zurueck, also zählt die Dateigröße, nicht der Exit-Code. Der logflush-Block
(1 MiB bei 63 MiB, alle 10 s, in allen vier gebauten Bildern) konnte von den
21 098 496 B grossen Writes nicht erreicht werden und trägt den letzten Flush
des zuletzt gestarteten Bildes. (3) Erst danach der Write.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0w/firstlight.img 49a1ffcab918b6edebd7ce3d1b6f62a6e260b902850a9a519974913130715680 300
```
v0w: 21098496 B, sha256 `49a1ffcab918b6edebd7ce3d1b6f62a6e260b902850a9a519974913130715680`, herausgelöste Init 22110 B / 455 Zeilen, Archiv sha256 `3e364f48fe3dd383c8c96e7becf0abca8d3fa9aa5cff42a3dd9e7b5b743fa7c7`. Vorgänger v0v: 21098496 B, sha256 `2d19241e88f61921716e3b176fdded0772e24257da894563a0e0874d5f1bd316`, Init 21 417 B / 449 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es.

Rueckweg STUFE 1 (stellt den Zustand von heute früh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28729344 B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`, 67108864 B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

Gerät ist jetzt (gemessen 2026-10-30 20:37): **läuft v0t, an keinem Bus** — `fastboot devices` ohne Eintrag, kein Fastboot-Gerät am USB-Baum, `ping -c 2 172.16.42.1` antwortet nicht; `boot_a` hält den v0t-Hash, und das Panel zeigt Titel und Herzschlag mit `state=not attatched` und leerem `gebunden=`-Feld (Gregors Ablesung). Für diesen Flash ist der Tastendruck nötig.

DIE SUCHE, wie sie im fertigen Bild steht — aus dem Archiv geschnitten, nicht abgetippt —, Zeilen 355 bis 362:
    SCDATEIEN=$(find /sys/kernel/debug -name soft_connect 2>/dev/null | head -6)
    SCLISTE=$(printf %s "$SCDATEIEN" 2>/dev/null | tr '\n' ' ')
    SZAHL=$(printf %s "$SCDATEIEN" 2>/dev/null | grep -c . 2>/dev/null)
    SC=$(printf %s "$SCDATEIEN" 2>/dev/null | head -1)
    [ -n "$SC" ] || SC=/sys/kernel/debug/usb/$u/soft_connect
    test -w "$SC"; SCRCA=$?
    if [ $SCRCA -eq 0 ]; then sc0=$( { echo 0 > "$SC"; } 2>&1 ); sc0rc=$?; else sc0="kein Knopf"; sc0rc=9; fi
    if [ $SCRCA -eq 0 ]; then sc1=$( { echo 1 > "$SC"; } 2>&1 ); sc1rc=$?; else sc1="kein Knopf, Suche: $SCLISTE"; sc1rc=9; fi

DER HERZSCHLAG meldet in jedem Block die Suche selbst, Zeile 74:
`echo "debugfs=$(ls /sys/kernel/debug 2>/dev/null | tr '\n' ' ') usb=$(ls /sys/kernel/debug/usb 2>/dev/null | tr '\n' ' ')"`

DIE NACHBIND-RUNDE, Zeile 371:
`echo "omamobile-blueline: weicher-bind $rb: write rc=$rc text=$err vorher=$scvor pfad=$SC gefunden=$SZAHL suche=$SCLISTE scrca=$SCRCA rc0=$sc0rc text0=$sc0 rc1=$sc1rc text1=$sc1, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), interfaces=$(ls /sys/class/net 2>/dev/null | tr '\n' ' ')" > /dev/kmsg`

DIE FÜNF-SEKUNDEN-ZEILE, Zeile 374:
`echo "omamobile-blueline: weicher-bind $rb spaeter 5s: sc1rc=$sc1rc sc1text=$sc1 scrca=$SCRCA gefunden=$SZAHL, UDC steht auf $(cat "$g/UDC" 2>/dev/null), staat=$(cat "$g/udc/$u/state" 2>/dev/null), udc-state=$(cat /sys/class/udc/*/state 2>/dev/null)" > /dev/kmsg`

ERWARTUNG v0w (20:5x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt den Titel `Omarchy Mobile first-light v0w - RAM only, der Knopf wird gesucht` und in jedem Herzschlag-Block die Zeile `debugfs=$(ls` mit dem Inhalt des haengenden Zaehlkanals und `usb=$(ls` mit dem Inhalt seines usb-Zweigs. Die Nachbind-Runde nennt `write rc=` - dieselbe Messgroesse wie bei den Vorfaehrern, absichtlich unter demselben Wort -, dazu `vorher=$scvor`, `pfad=$SC`, `gefunden=$SZAHL`, `suche=$SCLISTE` und `scrca=$SCRCA`. Die Fuenf-Sekunden-Zeile nennt `spaeter 5s:` mit `sc1rc=$sc1rc` und `scrca=$SCRCA`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, `is_active=`, `controller-state=`, `letzter Schritt:`. Zwei Messgroessen, die in der Referenz vorkommen, liefert dieses Bild nicht und verspricht es auch nicht: die dwc3-Rolle und ein vbus-Feld, ihre Abwesenheit ist Bauart und kein Befund. Die Faelle, die dieses Bild ohne jeden Bus trennt, stehen in der Aufzaehlung darunter.

EINFANG nach dem Flash: der Runner sammelt die Belege selbst ueber Telnet ein - die entscheidende Datei ist `v0r-steps.log`, ihre Geschwister in der Befehlsliste des Runners heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in dem Ordner, den der Runner unter seinem Ausgabe-Pfad anlegt (gemessen an seiner Zeile `OUT=${OUT:-/Users/gregor/hermes-workspace/flash-observe}`). Die Ablauf-Protokolle liegen dort und nicht im Repo, unter anderem `/Users/gregor/hermes-workspace/flash-observe/v0r-steps.log`. Fuer v0w kommt nichts dazu und faellt nichts weg: die Namen traegt der Runner, nicht das Bild, und der Block nennt sie, damit der Wart sie gegen die Befehlsliste halten kann.
- `gefunden=0` mit leerem `suche=` = der Knoten existiert in diesem Kernel nicht; v0vs `pfad=` war eine Annahme, und der Fall ist damit abgeschlossen, nicht offen.
- `gefunden=1` mit gefülltem `suche=` und `scrca=0`, aber `state=` bleibt `not attached` = der Knoten ist da, beschreibbar, gedrückt — und der Host sieht trotzdem nichts: VBUS, CC, Kabel oder Port. Software kann hier nichts mehr richten.
- `rc0=` oder `rc1=` ungleich null mit `invalid argument` = der Controller trägt den gadget-Zweig in diesem Moment nicht. `read-only file system` = debugfs hängt nicht. `No such file or directory` bei `scrca=0` = die Datei verschwand zwischen Test und Write.
- `scrca=9` mit `text0=kein Knopf` = die Beschreibbar-Prüfung hat den Write verhindert; die Beweiszeile nennt dann trotzdem `pfad=` und `suche=`, weil die Suche der Messwert ist, nicht der Druck.
- `debugfs=` im Herzschlag leer = debugfs hängt nicht; dann ist die ganze Suche Dunkelheit, kein Befund.
- `state=` geht auf `default` oder `configured` = der Host hat den Reset geschickt; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen — dieselbe Produktzahl wie v0s, v0t, v0u und v0v, eine Enumeration ist also nur über den Panel-Titel einem Bild zuzuordnen.
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

BELEGE VOR DEM Flash, alle gelaufen: Trockenlauf `patch-v0w.py` (7 Umbauten, je 1 Fundstelle, Bilanz 146 offene gegen 146 zu Paren), `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv (0 Fehler), `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild, `verify-v0w.py` **41 Beweismale / 0 Fehler** am fertigen Bild — darunter sechs Reihenfolge-Prüfungen: Suche in Zeile 355 vor der Annahme in Zeile 359, Beschreibbar-Test vor beiden Writes, kein unbedingter Pfad. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen. Die Suite (`tools/ci-arm64.sh`, 20:5x, mit dem fabrik-Spiegel als drittem Mount: `ok=145 (davon skip=4) not-ok=0 exit=0`) - dieselbe Zahl wie der v0u-Stand, gemessen im direkten Zwei-Stände-Lauf. Der Weg dorthin war eine Zahlendifferenz, keine Bildverschlechterung: 144 mit vier, dann drei, dann zwei schlafenden Pruefungen, jede einzelne ein Text, den der Block nicht nannte - nicht ein Fehler, den das Bild machte.

ZWEI NEUE REGELN AUS DIESEM BAU, beide gemessen, nicht gemeint:
1. **Ein Syntax-Test hat Vorrang vor jedem Text-Test.** Drei Herzschlag-Kandidaten wurden gegeneinander gemessen: nur der mit zwei Double-Quotes besteht `bash -n` allein. Der Kandidat in der Form des Vorgängers — drei Double-Quotes in einer Zeile — überlebt nur, weil die Folgezeile sein Literal schließt; am v0v-Bild ist genau das Zeile 74, und die nächste Zeile gehört mit in ihr Literal. Ein Text-Test war grün, während der Text syntaktisch zerstückelt war.
2. **Wer einen Beweis umbenennt, meldet ihn als fehlend.** Der Reihenfolge-Prüfer suchte das v0v-Feld und meldete die v0w-Zeile als fehlend, obwohl dieselbe Aussage dastand. Merkmalssätze wachsen mit; Beweise werden nicht umgetauft (dasselbe Muster: `write rc=` wurde zu `binde rc=` und durchtrennte die Beweiskette über drei Bilder).

## FLASH-BEREIT v0v — der weiche Verbindungspflicht, und was daran messbar ist (2026-10-30, 20:5x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0v: v0r und v0t haben je **0 Beobachtungen in 302 s** erreicht und dabei am Panel Titel und Herzschlag gezeigt; Gregors Ablesung von v0t nannte `state=not attatched` und ein leeres `gebunden=`-Feld. Ein Controller, der D+ nicht hochzieht, zeigt dem Host nichts — egal wie oft man bindet. Der Device Tree als Ursache ist ausgeschlossen (Referenz und v0t haben denselben Baum, 6290 gegen 6299 Zeilen decompiliert, der einzige Unterschied ist unser `ramoops`-Knoten). Der einzige Knopf, den diese Kernel-Version dafür hat, ist `soft_connect` in dwc3's debugfs-Zweig — am entpackten Kernel-Binary (44 498 944 Byte) gemessen: `soft_connect` **3 Fundstellen** (0x01becd05, 0x022360c8, 0x022c9162, zusammen mit `dwc3_gadget_soft_connect`, `dwc3_gadget_soft_disconnect`, `soft_connect_store`), `bDeviceState` **0 Fundstellen**. v0u hat deshalb alle vier bDeviceState-Lesungen verloren, v0v drückt den Knopf, der existiert.

SCHRITT 0, vor jedem Anruf: das Geraet braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zehlen; der Beleg kommt in den evidence-Ordner des Gerate-Zweigs, ein Name ohne Pfadnennung (den Ordner gibt es im Suite-Container nicht, und eine Pruefung, die ein Artefakt vermisst, meldet einen skip, den man an der gruenen Zahl nicht sieht)):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0v/firstlight.img 2d19241e88f61921716e3b176fdded0772e24257da894563a0e0874d5f1bd316 300
```
v0v: 21 098 496 B, sha256 `2d19241e88f61921716e3b176fdded0772e24257da894563a0e0874d5f1bd316`, herausgeloeste Init 21 417 B / 449 Zeilen, Archiv sha256 `447e250e064888790cac89e3fd8f892503cce752aea66fecb948be454d982a8d`. Vorgaenger: v0u-Bild 922a1a99… (21 094 400 B, Init 20 297 B / 436 Zeilen), v0t 4e25b525…, v0r auf demselben Stand. v0u, v0t, v0s, v0r hatten dieselbe Bildgroesse — die Bildgroesse ist kein Kennzeichen, der Hash vor dem Write ist es.
Der Runner vergleicht den Hash vor dem Write und bricht bei Abweichung ab, ohne das Geraet anzufassen. Vor jedem Partitions-Write steht zusaetzlich die Backup-Pruefung (Groesse und sha256 der Rueckweg-Datei), unabhaengig davon, dass eine Freigabe vorliegt.

Rueckweg STUFE 1 (stellt den Zustand von heute frueh exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, sha256 `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28 729 344 B — die Datei liegt auf Platte und ist vor jedem Write nachzumessen.
Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`, 67 108 864 B.

Gerat ist jetzt (2026-10-30 20:07:56, gemessen): **laeuft v0t, an keinem Bus.** `fastboot devices` meldet keinen Eintrag, `ioreg -p IOUSB | grep -ci 'android|fastboot'` meldet 0, `ping -c 2 172.16.42.1` antwortet nicht; `boot_a` haelt `4e25b525…`, und das Panel zeigt Titel und Herzschlag mit `state=not attatched` und leerem `gebunden=`-Feld (Gregors Ablesung). Fuer den Flash von v0v ist ein Tastendruck noetig: Power + Leiser ~10 s bis zum Fastboot-Schirm. Ohne Eintrag in `fastboot devices` bricht der Runner ab, ohne das Geraet anzufassen (Zeile 79 des Runners).

ERWARTUNG v0v (20:5x, vor dem Flash festgelegt; jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt `Omarchy Mobile first-light v0v - RAM only, weicher Verbindungspflicht am Controller` und in jedem Herzschlag-Block die Zeile `weicher-bind=debugfs-geoffnet pfad=` mit dem Ordnerinhalt von `/sys/kernel/debug/usb/` (Zeile 74 der Init). Die Nachbind-Runde (Zeile 365) nennt `write rc=$rc text=$err` — dieselbe Messgroesse wie v0u, absichtlich unter demselben Wort —, dazu `vorher=$scvor pfad=$SC rc0=$sc0rc text0=$sc0 rc1=$sc1rc text1=$sc1`, `UDC steht auf` und `interfaces=`. Die Fuenf-Sekunden-Zeile (368) nennt `sc1rc=`, `sc1text=`, `UDC steht auf`, `staat=` und `udc-state=`. Weiterhin da, je einmal: `typc: state=`, `udcdateien=`, `is_active=`, `controller-state=`, `letzter Schritt:`. Zwei Messgroessen, die in der Referenz vorkommen, liefert dieses Bild nicht und verspricht es auch nicht: die dwc3-Rolle und ein vbus-Feld — ihre Abwesenheit ist kein Befund, sondern Bauart. Die Faelle, die dieses Bild ohne jeden Bus trennt:
- `weicher-bind=debugfs-geoffnet pfad=` ohne Inhalt, oder `text0=`/`text1=` melden `no such file or directory` = debugfs haengt nicht oder der Ordner heißt anders als der UDC; das ist ein anderer Fall als ein Knopf, der nicht wirkt, und die Suche sitzt im Dateibaum (v0v probiert deshalb beide Kandidaten und schreibt den verwendeten in `pfad=`).
- `pfad=` gefuellt, `rc0=` und `rc1=` null, aber `state=` bleibt `not attached` = der Knopf ist erreichbar und gedrueckt, und der Host sieht trotzdem nichts: VBUS, CC, Kabel oder Port. Software kann hier nichts mehr richten.
- `rc1=` ungleich null mit `invalid argument` = der Controller traegt den gadget-Zweig in diesem Moment nicht; ein `read-only filesystem` waere debugfs nicht mounted (dann ist `pfad=` der Hinweis).
- das Herzschlag-Feld `state=` (Zeile aus dem UDC-Klassenbaum) geht auf `default` oder `configured`, oder die Fuenf-Sekunden-Zeile meldet einen dieser Werte = der Host hat den Reset geschickt und die Verbindung steht; am Bus waere dann Vendor 0x18D1 Produkt 0xD002 zu sehen — dieselbe Produktzahl wie v0s, v0t und v0u, eine Enumeration ist also nur ueber den Panel-Titel einem Bild zuzuordnen.
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

Belege vor dem Bau, alle gelaufen: Trockenlauf (`patch-v0v.py`: init 21394 B, 449 Zeilen, soft_connect 0 -> 3, done-Zaehlung gleich), `pruefe-binde-reihenfolge.py` auf dem patched Archiv (0 Fehler; Mutation gegen v0u: 2 Fehler, Exit 1), POSIX- und bash-Syntaxpruefung auf die herausgeloeste Init, `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild, `verify-v0v.py` am fertigen Bild. Die Suite (`tools/ci-arm64.sh`, das ist der kanonische Laeufer mit seinem Symlink-Raster, nicht das karge `./tests/all`) ist fuer fl-v0v noch nicht durchgelaufen.

VIER ANLAEUFE, DIE DIESE DATEI GEBRAUCHT HAT, und was sie gemeinsam haben: der Anker fuer den Bindblock wurde abgetippt statt geschnitten. Ein fehlendes Anführungszeichen, ein zu viel gesetztes, ein Fortsetzungszeichen hinter einem String, der selbst einen Backslash traegt (`tr '\n' ' ')" > /dev/kmsg`), und ein Loesch-Anker, der mitten in einer anderen Konstanten traf. Zwei davon meldete der Trockenlauf als Erfolg, weil er Anwesenheit zaehlte statt Reihenfolge — eine Beweiszeile, die `rc1=` vor ihrem Setzer nennt, ist ein Defekt, den keine Zaehlung sieht. Daraus: der Anker wird aus dem Vorgaengerbild geschnitten (`schneide-binde-anker`-Verfahren), jede Umbenennung wird mit gezehnter Fundstelle geprueft bevor geschrieben wird, der erzeugte Python-Quelltext wird mit `ast.parse` geprueft **bevor** er geschrieben wird, und die Formpriifung balanciert Klammern global und innerhalb der Echo-Ketten, nicht pro Zeile (pro Zeile klagte 28 echte Zeilen an, weil `( … ) &` über Zeilen balanciert).


## FLASH-BEREIT v0u — dieser Block traegt die Prozedur, nicht das Gedaechtnis (2026-10-30, 18:4x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

SCHRITT 0, vor jedem Anruf: **ENTFAELLT — das Geraet steht gemessen im FASTBOOT-MODUS** (`fastboot devices` meldet PIXEL3-SERIAL, zuletzt 14:16 mit `getvar battery-voltage: 4255` beantwortet). Steckt es bei deinem Anruf trotzdem nicht in fastboot: **erst `fastboot devices` lesen**, sonst greift der Tastenvorgang unten — so gemessen am 30.10.2026: die Referenz ist dunkel (ping 100 % Verlust, Port 23 und 5555 zu, ARP und adb leer), das Telefon haengt an USB und `fastboot devices` meldet `PIXEL3-SERIAL  fastboot` (firstlight/evidence/fastboot-modus-statt-orakel-2026-10-30.txt). Warum, ist nach drei Ausschlüssen ungeklärt aber eingegrenzt: mein Senden (13:07 erreichte das Geraet nie — die Sonde starb vor der Verbindung; 12:58 war nur `exit`, und das beendet die Telnet-Kind-Shell, nicht PID 1) und ein Panic mit Warmstart (Cmdline der Referenz traegt kein `panic=`) sind an der Datei ausgeschlossen, Strom ebenso — uebrig bleibt der Tastendruck, entschieden wird er durch ein Foto des Bootloader-Bildschirms (firstlight/evidence/fastboot-uebergang-kandidaten-2026-10-30.txt). Wuerfe der Runner sonst Zeile 79 raus (`not ok - kein Fastboot-Geraet`), ist Schritt 0 ein **Tastenvorgang, kein bootloader-Kommando** — gemessen 2026-10-30 (firstlight/evidence/reboot-faehigkeit-referenz-2026-10-30.txt): das Wort `bootloader` kommt im Busybox-Binary der Referenz (v1.38.0) nullmal vor; PID 1 ist dort nicht busybox init, sondern `/bin/busybox ash /init_2nd.sh` (firstlight/evidence/pid1-und-signale-referenz-2026-10-30.txt — dessen trap-Zeile 'reboot -f' TERM haelt den Signalweg offen, aber verlass dich nicht darauf: nacktes `reboot` ist eine Kette, deren Vorhandensein diesem Drehbuch eigen ist). So: im Telnet `sync` dann `reboot -f` eintippen (der `-f`-Syscall, ohne Kette; alles ist RAM, sync ist Regel-Dekor) und **dabei sofort LEISER druecken und halten, bis FASTBOOT MODE im Display steht** (Ausrede falls verschlafen: Power + Leiser ~10 s). Dann `fastboot devices` abwarten.
Er beendet das Orakel: die Referenz haelt den angehaltenen Initramfs-Start mit Debug-Shell (Uptime zuletzt 58 014 s). Die letzte Live-Messung ist gesichert (firstlight/evidence/reference-live-vor-v0r-2026-10-30.txt und reference-netzwerk-vor-v0r-2026-10-30.txt: udc-state `configured`, g1/UDC `a600000.usb`, 172.16.42.1/16 auf **usb0** — ncm0 gibt es auf der Referenz nicht —, dwc3-IRQ 5 923, Uptime-Kopf und -Fuss). Was dort nicht steht, ist nach dem Reboot nicht mehr messbar.
Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zaehlen; Protokoll nach `/Users/gregor/hermes-workspace/flash-observe/protokoll.txt`):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0u/firstlight.img 922a1a9915f400c543be82c11dff5077849ed39826d661158054144857d4dc9d 300
v0t: 21094400 B, v0s hatte dieselbe Groesse (Init 19446 B gegen 19649 B) — die Bildgroesse ist keine Versionskennung. Der Runner vergleicht den Hash vor dem Write und bricht bei Abweichung ab, ohne das Handy anzufassen. **Dieser Block wird von `tests/flash-block` gegen die Platte geprueft**, derzeit 12 Pruefpunkte / 0 Fehler; eingefroren: keine weiteren Pruefregeln, nur Reparaturen an bestehenden. Prueft: erreichbarer Pfad, Belegdatei, Hash und Groesse jedes genannten Bildes, Anrufbild mit seinem Hash, Rueckweg gegen den Runner-Default, angesagte Ausgabe im ausgelieferten Bild oder im Runner, Sammelname in der Befehlsliste des Runners, Adresse gegen den ping des Runners. Mutationen, jede ergibt `not ok` gegen eine unangetastete Kopie mit Exit 0: Hex-Ziffer, Groesse um 1, umbenanter Sammelname, verstellte Adresse, Rueckweg-Pfad, und seit heute ein Erwartungs-Titel mit 78 Zeichen. Nach jeder Aenderung an diesem Block `./tests/flash-block` laufen lassen. Beleg der letzten Reparatur: firstlight/evidence/waechter-langzeilen-blind-2026-10-30.txt.
v0r: 21094400 B. Der Runner vergleicht den Hash vor dem Write und bricht bei Abweichung ab, ohne das Handy anzufassen. **Dieser Block wird von `tests/flash-block` gegen die Platte geprueft**. Prueft: erreichbarer Pfad, Belegdatei, Hash und Groesse jedes genannten Bildes, Anrufbild mit seinem Hash, Rueckweg gegen den Runner-Default, angesagte Ausgabe im ausgelieferten Bild, Sammelname in der Befehlsliste des Runners, Adresse gegen den ping des Runners. Getrennt mit sechs Mutationen (Hex-Ziffer, Groesse, Sammelname, Adresse, Rueckweg-Pfad — je `not ok`; unangetastete Kopie Exit 0). Nach jeder Aenderung an diesem Block den Läufer laufen lassen; er ist gegen vier Mutationen getestet (eine unangetastete Kopie bleibt Exit 0) (Hex-Ziffer, Groesse um 1, umbenannter Sammelname, verstellte Adresse — jede ergibt `not ok`).
NACH DEM FLASH die drei getvars in Zeile 81–83 lesen (der Runner tut es selbst und protokollert sie): Vorher stand in der Referenz-Cmdline `slot_retry_count=2`, `slot_successful=no` (evidence/cmdline.txt), und am 30.10. direkt in fastboot nachgelesen: unveraendert `retry:a 2`, `unbootable:a no` (evidence/fastboot-modus-statt-orakel-2026-10-30.txt). Korrektur 30.10., 16:1x, zweimal am selben Datei gemessen: der Zaehler ist NICHT unveraendert 2 — er stand beim Write von 13:08 auf **3**, der `fastboot reboot` hatte ihn aufgefuettert. Ein frischer `fastboot reboot` (und ein Tasten-Reset) fuehrt das Budget also **neu auf**, statt es runterzaehlen zu lassen; es gibt nach diesem Flash wieder drei Boot-Versuche, und "es bleiben noch n" ist keine Groesse, die man aus dem Stand Vorher-Wert behaupten darf — immer `getvar slot-retry-count:a` lesen. Ein Auffuellen mit `fastboot --set-active=a` waere der uebliche Weg, ist fuer diesen Bootloader aber **UNBELEGT** und ein Meta-Daten-Write — deshalb nicht getan, sondern Gregors Entscheidung. Vor einem naechsten Versuch erst den Zaehlerstand im Protokoll lesen, nicht raten.
EINFANG nach dem Flash: der Runner sammelt die Belege selbst ueber Telnet ein — die decisive Datei ist `v0r-steps.log` (ihre Geschwister im Runner, Zeile 147–156, heissen `identitaet.txt`, `v0r-steps-ende.txt`, `v0r-gadget-udc.txt`, `v0r-gadget-func.txt`, `v0r-udc-liste.txt`, `v0r-udc-state.txt`, `v0r-uptime.txt`, `v0r-modules.txt`, `v0r-procs.txt`; alle in `$OUT`). **Korrektur 2026-10-30:** hier stand frueher `telnet-v0r-steps.log` — ein Name, den der Runner nie erzeugte (null Treffer im Runner und im Bild); wer danach suchte, fand keine Datei, obwohl der Lauf gelungen war. Die Namen prueft jetzt `tests/flash-block` gegen den Runner, nicht gegen die Erinnerung. Ihr Filter warf frueher jede Zeile, die das ERSTE WORT des Befehls enthielt, und haette damit die beiden UDC-Zeilen vernichtet, um die es geht; der neue ist am ausgelieferten Bild geprueft (tests/bisection Abschnitt 5b: 2 decisive Zeilen gerettet, der alte verlor beide) und war gegen das laufende Orakel getrockengelaufen. Eine leere Datei meldet `ACHTUNG leer` statt still Erfolg — leer ist eine Antwort, kein Bestehen.
Rueckweg STUFE 1 (Runner-Default, stellt den heutigen Zustand exakt wieder her): `/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img`, 28729344 B, `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`.
Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an — geloescht haette nur `fastboot -w` oder `flashall`): `/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img`, 67108864 B, `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`.

ERWARTUNG v0u (18:4x, vor dem Flash festgelegt, nur belegte Zeichenketten — jede Backtick-Zeichenkette ist im ausgelieferten Bild nachgesehen): das Panel zeigt `Omarchy Mobile first-light v0u - RAM only, Binden ist messbar, Typ-C am Panel` und in jedem Herzschlag-Block die Zeile `typc: state=` mit den Typ-C-Werten sowie `write rc=` nach jedem Binden. v0u unterscheidet sich von v0t ausschliesslich durch Messbares am Panel (patch-v0u.py, Trockenlauf und POSIX-Syntaxpruefung vor dem Bau durchgelaufen, 19 Beweismale / 0 Fehler am fertigen Bild, Build 922a1a99…): alle vier Lesungen des Knotens bDeviceState sind entfernt (im v0t-Bild 4 Vorkommen in 3 Zeilen, gemessen; der Knoten existiert auf diesem Kernel nicht, die Felder blieben leer) und der Bindblock schreibt seinen Rueckgabewert und den Fehlertext des binden-write selbst mit. Die vier Faelle, die dieses Bild ohne jeden Bus trennt: `write rc=` mit einem Wert ungleich null und einem der drei Fehlertexte `device or resource busy`, `invalid argument` oder `no such device` = das Binden scheitert an configfs, und der Text nennt die Ursache; `write rc=` mit null und in der Folgezeile `spaeter 5s` ein gebundener Name = das Binden gelingt, der Controller meldet aber keine Verbindung, und die Suche sitzt beim Typ-C-Port, bei VBUS oder am Kabel; `typc: state=` gefuellt (source = das Telefon speist, sink = der Rechner speist) und `is_active=` gefuellt = Port und Controller sind lesbar am Leben; eine leere `udcdateien=`-Liste = die UDC-Knoten sind weg, ein anderer Fall als ein leerer Wert derselben Datei. Panel-Titel ohne Herzschlag = PID 1 stirbt zwischen Titel- und Herzschlagzeile; gar kein Text = der Boot starb vor init. Am Bus waere ein USB-Geraet Vendor 0x18D1 Produkt 0xD002 zu sehen — dieselbe Produktzahl wie v0s und v0t, eine Enumeration ist also nur ueber den Panel-Titel einem Bild zuzuordnen.
ERGEBNIS v0t (Erwartung von 16:5x, hier herabgestuft, weil das v0t-Bild den 16:5x, vor dem Flash festgelegt, nur belegte Zeichenketten): das Panel zeigt `Omarchy Mobile first-light v0t - RAM only, Doppel-Knoten-Lesung am Panel` und in jedem Herzschlag-Block die Zeile `beide Knoten: state=` mit zwei Werten. Der eine Knoten (state) ist an einer Datei belegt — die Referenz-Livemessung las /sys/class/udc/a600000.usb/state und erhielt configured; der andere (bDeviceState) ist unbelegt und wird nur mitgelesen, damit eine leere Stelle ein Ergebnis ist und kein Lesefehler. Die Unterscheidung, die dieses Bild liefert: beide Felder leer = diese Knoten existieren nicht unter diesem Pfad, und die Suche geht an die Knotenliste, die dieselbe Zeile mitausgibt; state gefüllt = der Controller meldet seinen USB-Zustand, und der Wert ist auf dem Panel lesbar; beide gefüllt = die Panel-Ausgabe ist komplett und der Bus ist trotzdem taub, was die Suche an Typ-C-Rolle, VBUS und Kabel stellt. An der Shell hängt nichts: v0t unterscheidet sich von v0s ausschließlich durch diese eine Herzschlagzeile und den Panel-Titel (patch-v0t.py, Trockenlauf vor dem Bau durchgelaufen).
steps.log-Zeile `udc nach <n> runden gefunden`: n > 0 bestaetigt die UDC-Timing-Diagnose mit einer Zahl (Referenz: gadget setup bei 1,708 s, HOST-MAC-Bindung bei 1,734 s Kernelzeit; v0q las zu frueh und blieb 83 min weg); **n = 0 widerlegt sie**, dann sitzt der Fehler anderswo in init.
ERGEBNIS FALSCH (Enumeration da und Telnet antwortet, aber steps.log zeigt etwas anderes — Diagnose-Fall, kein Notfall): im v0r-Telnet `/bin/restart2 bootloader` (steht gemessen im v0r-Initramfs, 737 Mitglieder; ob ABOOT den Grund ehrt, ist NIE beobachtet — gilt erst als bewiesen, wenn `fastboot devices` danach antwortet; tut es das nicht, Tastenvorgang wie in Schritt 0), dann Stufe 1 auf boot_a flashen, dann `fastboot reboot`.
DUNKEL (nichts am Bus, Telnet antwortet nicht — der Notfall): Power + Leiser ~10 s halten (Power allein tut nichts), dann Stufe 1 auf boot_a flashen **und `fastboot reboot` — der Flash allein startet nicht neu**. Erst wenn auch die Referenz dunkel bleibt, Stufe 2.
ERGEBNIS DES LAUFS vom 30.10., 16:07–16:14 (Gregors Freigabe, ein Write): **ERGEBNIS FALSCH, und eine Stufe frueher als die Diagnose.** 0 Beobachtungen in 302 s — v0r war an keinem Bus (kein fastboot, 0 "Pixel 3" in ioreg, ping 100 % Verlust, nc 23 exit 1, adb leer; 16:13:53 vier Leser direkt gemessen). v0q enumirierte immerhin als USB-Geraet, v0r zeigt keine USB-Praesenz: die UDC-Warteschleife konnte ihr Ziel nicht erreichen. Nebenbefund beim Schreiben: `slot-retry-count:a` war beim Write **3**, nicht 2 — der `fastboot reboot` von 13:08 hatte den Zaehler aufgefuellt, ein Tasten-Reset gilt ABOOT nicht als Fehlstart. Rueckweg Stufe 1 stellt seither nicht mehr "den heutigen Zustand" wieder her, sondern die **Referenz** auf boot_a (Zustand vorher = v0r, dunkel). Alles Gemaessene und die zwei Lesarten (Kernel vor der UDC-Registrierierung tot / Typ-C-Rolle seit dem Tastenreset ohne Datenrolle) in firstlight/evidence/v0r-null-enumeration-2026-10-30.txt. **Was jetzt gebraucht wird: ein Foto des Panels** — das Bild schreibt Panel-Titel (Zeile 96), einen Herzschlag alle ~20 s mit udc-/gebunden-/rolle-Werten (Zeile 63–76) und den pstore-Text des letzten Bootes (Zeile 80–89) auf den Bildschirm; damit ist die Diagnose ohne jeden Bus lesbar.
Gerat ist jetzt (30.10.2026, 17:06:57): **dunkel, an keinem Bus**, `boot_a` haelt v0t (`4e25b525…`), die Referenz nur noch als Datei auf der Platte, userdata nie angefasst, kein Write seit 16:56:27. Zweiter Messlauf dieser Art: 0 Beobachtungen in 302 s, weder mit Produkt 0xD001 (v0r) noch 0xD002 (v0t), und kein Panic-Empfang im Fastboot — ein panic=60-Warmstart lief also nicht. Was allein weiterweiss: die Panel-Zeile 'beide Knoten: state=… bDeviceState=… udcdateien=…', die v0t alle ~20 s schreibt; die vier Faelle stehen in firstlight/evidence/v0t-null-enumeration-2026-10-30.txt. Das Statusdatum vier Zeilen unter diesem Block ist von 2026-10-27 und laengst ueberholt.

Status (2026-10-27): descriptor, plan and device package written; no Pixel 3
hardware in hand yet. Nothing in this file has been run on a blueline.
M1.1, the host-only first-light build, is done and evidenced below; no
fastboot or adb command has been run for it.
Upstream's board device tree is already built by our kernel: `sdm845-google-
blueline.dts` sits in the `omamobile` branch of linux-omarchy-mobile (tree
contents checked 2026-10-27), which is why this phone starts where the
Tensor ports did not: with a mainline board description whose drivers run
upstream on many other SDM845 boards.

**In one paragraph:** the Pixel 3 is the older-sibling Qualcomm phone of the
Pixel 4 family this repository already brings up. Its bootloader is ABOOT,
not Tensor ABL: it boots header-v2 images, matches appended device trees by
`qcom,msm-id`/`qcom,board-id`, keeps its slot flags in GPT partition
attributes, and has no `vendor_boot`, `init_boot` or `vendor_kernel_boot`.
The first light is therefore built from the recipe this generation's field
reports prove: an mkbootimg image at the postmarketOS deviceinfo's offsets
with the board DTB appended, our initramfs (dropbear, CDC NCM gadget, every
UFS block read-only), booted **from RAM with zero writes** before anything
touches slot B. The plan's gates then take calibration backups, write slot
B and `userdata`, and mark slot B bootable as CONTRIBUTING 3.1's named GPT
exception, captured sector by sector before and after.

## Development handset state (2026-10-27)

The way back is held off-device. **Correction 2026-10-27 (owner review):**
the first factory image pulled here, **Android 11 (RQ3A.211001.001,
Oct 2021)**, `blueline-rq3a.211001.001-factory-2cca4239.zip` (sha256
verified equal to the hash in its file name, `2cca42397f29cc3b032dbd2b627e65049ffd894be4801a39c292e663d01cbc71`),
ships bootloader **b1c1-0.3-7241706** (verified inside the unpacked zip at
`rq3a/blueline-rq3a.211001.001/bootloader-blueline-b1c1-0.3-7241706.img`)
while this handset runs **b1c1-0.4-7617406** — flashing RQ3A's flash-all
would *downgrade* the bootloader. The way back is therefore the last
official blueline factory image, **Android 12 (SP1A.210812.016.C2,
Jun 2022)**, `blueline-sp1a.210812.016.c2-factory-fa981d87.zip` —
downloaded 2026-10-27, sha256
`fa981d87b6b28a1996161accbb147f46fe29663bb2ce6cc13dc9e500cbc59c93`
verified equal to both the hash in its file name and Google's published
checksum; its payload `bootloader-blueline-b1c1-0.4-7617406.img`
(8,726,312 bytes, unpacked under `factory/sp1a/`) matches this handset's
`version-bootloader` bit for bit, so flashing it does NOT downgrade the
bootloader (the same build LineageOS documents for the b1c1-0.4 era:
`review.lineageos.org` vars/blueline, build_number 8618562).
`android-mainline/factory/` holds both zips; neither is ever flashed
without re-checking its bootloader version against `fastboot getvar
version-bootloader` first.

**Honest state of `boot_a`:** the Ubuntu Touch / postmarketOS `boot_a`
that ran this handset was overwritten by first-light flashes and the
intended `fastboot fetch` backup landed as a **0-byte file**
(`android-mainline/factory/boot_a-ut-backup.img`, verified size 0). It is
NOT bit-restorable; the way back to Android is the SP1A factory image
above, which **wipes user data** (owner accepted this on 2026-10-27).
Standing rule from this incident: **before any partition write, the
backup file for that partition must exist with nonzero size and a
recorded sha256 — verified, not assumed — or the write is logged as
destructive and re-consented.**

The port's handset arrived running **Ubuntu Touch on a postmarketOS base**
(the USB composite self-describes with serial `postmarketOS`,
`18d1:d001`, connected over a hub; `adb` on the host saw no adbd, so its
USB gadget exposes no adb function to the Mac). Stock Android therefore no
longer sits on a boot slot as-is: before any gate writes slot B, the owner
must have the matching **stock factory image saved off-device** as the way
back (BRINGUP-M1 M0/M1.5), and M1.0's getvars will show which slot the
Ubuntu Touch boot lives in. That the phone boots a postmarketOS-family
stack at all is useful evidence for M1.2 — a mainline-derived SDM845
kernel already drives this board's storage and display in that setup;
`uname -r` from it belongs in this note once a shell is reachable.

## Sources and facts

- [V, source, 2026-10-27] Upstream board DTS:
  [arch/arm64/boot/dts/qcom/sdm845-google-blueline.dts](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom/sdm845-google-blueline.dts)
  with `sdm845-google-common.dtsi` beside it: root `compatible =
  "google,blueline", "qcom,sdm845"`; `qcom,msm-id = <SDM845 0x20001>` and
  `qcom,board-id = <0x00021505 0>` for ABOOT's matching; `chosen`
  `stdout-path = "serial0:115200n8"` with `serial0 = &uart9`; a
  `simple-framebuffer` (`a8r8g8b8`) on the bootloader's splash region
  (`cont_splash_mem`, `0x9d400000` + 36 MiB) sized 1080x2160 by the board
  file; the panel node (`lg,sw43408`, reset GPIO 6, TE GPIO 12); `i2c2`
  enabled with a `ST,FTS @ 49` comment but no touch node yet; and the
  Wi-Fi node asking calibration variant `Google_blueline`. The same DTS is
  in [linux-omarchy-mobile](https://github.com/derekross/linux-omarchy-mobile)
  `omamobile` (directory listing checked 2026-10-27), so our kernel already
  builds the DTB; nothing has run it on a Pixel 3.
- [V, source] Boot image recipe proven on this phone by field reports
  (postmarketOS deviceinfo for `google-blueline`): fastboot flashing,
  `console=ttyMSM0,115200`, kernel offset `0x8000`, ramdisk offset
  `0x1000000`, tags offset `0x100`, base `0x0`, page size 4096, no
  Qualcomm QCDT, the board DTB **appended** to the image, and UFS sector
  size 4096. Its firmware packages (`firmware-google-blueline`,
  `firmware-google-blueline-dtbo`) are an inventory of which stock blobs
  exist, not a license to ship them: our rule stands, they come from the
  owner's own factory image.
- [V, this repo] The Pixel 4 notes
  ([BRINGUP-M1.md](../flame/BRINGUP-M1.md)) verified with `fastboot` on a
  real SM8150 phone of the same boot generation: `boot_a/b`, `dtbo_a/b`
  and `userdata` exist, there is no `vendor_boot`, `init_boot` or
  `vendor_kernel_boot`, and slot selection is GPT partition attributes
  (CONTRIBUTING 3.1, which still names no device). Blueline is expected to
  match; gate M1.0 checks the claim on this phone before anything is
  written.
- [V, reports, not ours] Published field notes for a mainline-kernel Pixel
  3 running as a daily phone
  ([device records](https://forge.caseytunturi.com/Fimeg/SouveraineOS/src/branch/public/saf/device/README.md),
  2026-07/08) report calls, SMS and LTE data working on it, and three
  operational notes for SDM845 mainline setups we adopt as risks to
  verify, not as facts: warm reboots can leave TrustZone/remoteproc state
  poisoned so they boot cold only; the WCN3990 ships no Bluetooth BD
  address and needs a persisted generated one; and the X20 modem answers
  QMI only once the `modemsmem` SMEM item is populated, else the probe
  waits with `DeviceNotReady`. None of it is claimed for our kernel here.

## The phone after first light

Slot A is stock Android and the way back, never written. Slot B holds our
`boot_b` (kernel + appended DTB + our initramfs) and, if gate M1.5 proves
the stock overlay interferes, our `dtbo_b`. `userdata` becomes the Arch
root. Every other block stays read-only behind the initramfs guard; the
allowlist the guard will carry is `boot_b dtbo_b userdata`. USB is the
only link during bring-up: CDC NCM at 172.16.42.1, like every other device
here.

## Gates

One change per boot, read-only first, human approves every write and every
reboot (AGENTS 1). No gate may run its write before the gate before it
passed on this phone, with the date and `uname -r` recorded beside it.

### M1.0 — arrive, unlock, capture (no writes beyond the unlock)

- Stock boot, `adb` on; record `ro.product.device`, `ro.boot.slot_suffix`,
  `ro.boot.flash.locked`, the bootloader version and active slot into
  `~/android/reference` (never committed). From fastboot, `getvar all`
  (scrub the serial) and `getvar partition-size:*`: this confirms or
  refutes the boot_a/b, dtbo_a/b, no-vendor_boot layout from the Pixel 4
  notes, and sizes `boot_b` for the image gate.
- Unlock is the owner's call and wipes `userdata` (Android's data, not
  the calibration partitions): `fastboot flashing unlock`, with written
  acceptance that until M1.6 the phone has only its stock slot. If the
  phone arrives locked with a stale Android, take the getvars first.
- Pass: partition table, sizes and slot state recorded. Risk: none beyond
  the unlock itself.

### M1.1 — build the first-light image (host only) — DONE 2026-10-27, no phone

**Kernel.** `omamobile` branch of [linux-omarchy-mobile](https://github.com/derekross/linux-omarchy-mobile) shallow-cloned to `~/hermes-workspace/android-mainline/kernel` (outside the repo); release `7.3.0-rc6-omamobile-push1-g33267e524f97-dirty` (`include/config/kernel.release`; `-dirty` is an artifact of the shallow clone's `git describe`, no source was edited). The board DT is upstream, no blueline-specific patch. The repo's `docker/Dockerfile` does not install on arm64 (`g++-multilib`, `gcc-multilib`, `lib32readline-dev`, `lib32z1-dev` have no aarch64 candidates — the image was built for x86_64 hosts), so the build ran in a trim of it for arm64 (`android-mainline/buildenv-Dockerfile.arm64`, same Ubuntu 24.04 minus the multilib packages): gcc 13.3.0, GNU Make 4.3, binutils 2.42, native `--platform linux/arm64` on this Apple-silicon machine, no `LLVM=1`.

Config: arm64 `defconfig` + `kernel/configs/omamobile.config` with `scripts/kconfig/merge_config.sh -m` exactly as `bin/omamobile kernel` does. **The fragment builds clean for sdm845** — arm64 is multi-platform, so the Tensor options are additive; no fallback config was needed. `scripts/config -e` pinned three symbols the defconfig leaves `=m` and the initramfs needs built-in (it loads no modules): `SCSI_UFS_QCOM`, `USB_CONFIGFS`, `QCOM_WDT` (ABOOT-generation watchdog; flame takes it over with a module, first light cannot). `EXT4_FS`, `USB_DWC3_QCOM`, `USB_CONFIGFS_NCM/ACM`, `DEVTMPFS_MOUNT`, `BLK_DEV_INITRD`, `DRM_SIMPLEDRM`, geni serial and the RPMH/ICC/IOMMU sdm845 stack were already `=y` from defconfig or the fragment (`olddefconfig` kept every pin). `modules` was not built (first light loads nothing); the target DTB needed its own `make` invocation — combining `Image.gz arch/arm64/boot/dts/qcom/….dtb` in one call trips kbuild's target-prefix duplication (`No rule to make target 'arch/arm64/boot/dts/arch/arm64/boot/dts/…'`).

```
make ARCH=arm64 O=out-blueline-kernel defconfig
scripts/kconfig/merge_config.sh -m -O out-blueline-kernel \
    out-blueline-kernel/.config kernel/configs/omamobile.config
scripts/config --file out-blueline-kernel/.config -e SCSI_UFS_QCOM -e USB_CONFIGFS -e QCOM_WDT
make ARCH=arm64 O=out-blueline-kernel olddefconfig
make ARCH=arm64 O=out-blueline-kernel -j18 Image.gz
make ARCH=arm64 O=out-blueline-kernel dtbs
```

**Image builder.** `device/blueline/firstlight/build` (host CLI, `build-flame-probe` style) runs `device/blueline/firstlight/initramfs/build` in a disposable aarch64 Alpine container and assembles with AOSP `mkbootimg.py` (AOSP `system/tools/mkbootimg`, shallow clone beside the kernel). The initramfs is Alpine `alpine-baselayout busybox dropbear iproute2 util-linux busybox-extras` (729 cpio entries) with `device/blueline/firstlight/initramfs/init`: banner, tmpfs/devtmpfs root, **every** UFS block `blockdev --setro` before anything mounts (per-device failures logged, re-asserted by a 1 s loop), an **empty** `/etc/omamobile-ufs-rw` with fail-closed init (missing or non-empty file also means all-read-only), no module loads, no userdata mount, CDC NCM `usb0` 172.16.42.1/24 + CDC ACM, product string from the descriptor's `NAME` (`/etc/omamobile-usb-product`; busybox `tr` has no `[:print:]` class — the printable-ASCII octal range is used), dropbear key-only on 172.16.42.1, shells on `ttyMSM0` and `ttyGS0`. Assembly:

```
device/blueline/firstlight/build --kernel …/Image.gz \
  --dtb …/sdm845-google-blueline.dtb --ssh-key ~/.ssh/id_ed25519.pub \
  --mkbootimg …/mkbootimg/mkbootimg.py --out out-blueline
# in the container:
mkbootimg.py --header_version 2 --base 0x0 --kernel_offset 0x00008000 \
  --ramdisk_offset 0x01000000 --tags_offset 0x100 --pagesize 4096 \
  --kernel Image.gz --ramdisk initramfs.cpio.gz --dtb sdm845-google-blueline.dtb \
  --cmdline 'console=ttyMSM0,115200n8 panic=10 androidboot.hardware=qcom androidboot.board=blueline' \
  -o out-blueline/firstlight.img
```

The DTB goes through `--dtb` (appended, header-v2 dtb fields), not the second stage — the field-proven recipe for this phone appends the board DTB (`append_dtb`, no QCDT). Output is `firstlight.img`, never `boot.img`, and the builder refuses an existing file.

**Validation, no phone (all logged to `logs-blueline/`, gitignored):**

(a) header parse (`python3` + `struct`; script in scratch, output verbatim):

```
magic           : ANDROID!
header_version  : 2 (header 1660 bytes in a 4096-byte page)
page_size       : 4096
kernel          : 16216010 bytes @ 0x8000
ramdisk         : 4757262 bytes @ 0x1000000
second          : 0 bytes
tags_addr       : 0x100
recovery_dtbo   : 0 bytes @ 0x0
dtb             : 105798 bytes @ 0x1f00000
cmdline         : console=ttyMSM0,115200n8 panic=10 androidboot.hardware=qcom androidboot.board=blueline
size            : 21086208 bytes (sections end at 21086208)
OK: header v2 layout, all sections present and page-aligned
```

`mkbootimg.py` wrote `header_version 2` (the v2 layout with the dtb size/addr fields; "header v2" on this generation means this layout, which ABOOT accepts — postmarketOS builds exactly this). `os_version/patch` is 0: the header fields are informational for ABOOT and no deviceinfo value for them was cited, so none was invented. `dtb @ 0x1f00000` is mkbootimg's default `--dtb_offset` load address; ABOOT relocates the appended DTB itself. 21.1 MiB fits a Pixel-3-size boot partition with room to spare; the builder enforces 64 MiB until M1.0's `getvar partition-size:boot_b` replaces the budget.

(b) appended DTB split out of the image and decompiled:

```
$ dtc -I dtb -O dts /chk/dtb (root node)
	qcom,board-id = <0x21505 0x00>;
	qcom,msm-id = <0x141 0x20001>;
	model = "Google Pixel 3";
	compatible = "google,blueline", "qcom,sdm845";
```

(c) ramdisk extracted and listed: 729 entries incl. `init`, `usr/sbin/dropbear`, `usr/bin/dropbearkey`, `sbin/blockdev`, `sbin/getty`, `usr/sbin/udhcpd`, `bin/ip*`, `root/.ssh/authorized_keys` (the one supplied public key), `/etc/omamobile-usb-product = [Google Pixel 3]`, `/etc/omamobile-ufs-rw: 0 bytes` (empty allowlist).

(d) `sha256 out-blueline/firstlight.img`:
`dcbd1bcdd935cd4dba50b969d006be64c71c6ad28e67e219b219e01d2a9fab53`

- Pass: image builds and parses as header v2 with the board DTB appended and
  a dropbear-bearing initramfs; re-running the builder refuses the existing
  `firstlight.img`. `avbtool info_image` is not expected to find a footer;
  ABOOT on an unlocked phone does not require one. **Nothing touched a
  phone: no fastboot or adb was ever invoked for this gate.**

### M1.2 — boot from RAM, zero writes

- Announce to whoever holds the phone: the screen will show our boot text.
- `fastboot boot <firstlight.img>` — ABOOT runs it without flashing
  (field reports show this path works on this generation; if the phone's
  ABOOT refuses, that is a stop, not a license to flash: re-check with
  `fastboot --help`-visible options and the getvars, then ask).
- Expect: the splash console hands over to kernel boot text; within 90 s
  the host has `usb0` and `ssh root@172.16.42.1`.
- Pass: `uname -a` names our build and
  `cat /proc/device-tree/compatible` starts with `google,blueline`;
  `lsblk -o NAME,RO,RM,SIZE` shows every UFS disk and partition
  read-only; the modem, Wi-Fi and ADSP remoteprocs are untouched
  (`/sys/class/remoteproc` untouched); no `ufshcd` or `abr` errors in
  `dmesg`; the `simple-framebuffer` console is the screen we are reading.
- Stop: no USB link after 90 s → hold Power ~30 s, then Power (stock
  slot A was never written; this is always survivable here). Record
  pstore after the restart.
- Risk: none — no block is written in this gate.

#### Attempt 2026-10-27: ABOOT refuses the RAM boot — gate pivots to a temporary flash

`fastboot boot` with the built image failed as
`Booting FAILED (remote: 'Error verifying the received boot.img: Invalid
Parameter')` — every time, after ABOOT had already accepted the transfer.
Controls run on the handset, in order:

1. Stock RQ3A `boot.img` from the verified factory zip via the identical
   `fastboot boot`: **OKAY**. The port, cable, and fastboot work; the
   verdict is about our image.
2. AVB hash footer (test key, `SHA256_RSA2048`, boot partition size from
   the factory image's 64 MiB budget) added around our image: refused.
3. `os_version` header field set byte-identical to stock
   (`0x1600015a`): refused.
4. The arm64 Image inside our build carries `text_offset = 0x0`
   (mainline default since the 5.8 era) while the header said
   `kernel_addr = 0x8000`. A UART log in pmaports !3932 shows this exact
   mismatch as `KernelDecompress failed: Invalid Parameter / Kernel
   TextOffset does not match`, and mobile-nixos !361 patches for it; the
   builder was rebuilt with `--kernel_offset 0x0` (header now matches the
   Image's own text_offset). Refused again — the mismatch was real but
   not the only gate.

The community record is consistent that this ABOOT generation (Android
10+ bootloader, Pixel 3/3a/3XL family) refuses *temporary* booting of any
image not built against its exact vbmeta era — TWRP never regained
`fastboot boot` there (TeamWin/android_device_google_crosshatch#5,
twrpme#109, several unresolved reports through Android 12) — while
`fastboot flash` of the same images works. Per this gate's own rule the
refusal is a stop: no further RAM-boot permutations.

**Plan deviation, decided 2026-10-27 (not a reversible shortcut):** M1.2
was written as zero-write and later gates were to touch only slot B.
This handset's ABOOT refuses RAM boot outright and there is no second
bootable mainline slot (slot A holds the only working stack, slot B is
not Ubuntu Touch's boot source here), so bring-up flashes **`boot_a`
directly**. That is destructive by design: the Ubuntu Touch `boot_a` was
overwritten without a valid backup (see the 0-byte-file correction
above), the way back is the SP1A factory image at the cost of user data,
and the owner consented to exactly this trade. Every later partition
write follows the verify-backup-first rule stated at the top of this
document.

#### Attempt 2026-10-27 (second): concatenated-DTB boots alive but mute — the PHYs were modules

Flashed to `boot_a` and rebooted (`fastboot flash` + `fastboot reboot`):
with the DTB concatenated onto the kernel blob the phone stopped dying —
no return to ABOOT for minutes, while every header-section-DTB boot was
back in ~4 s. But it booted **mute**: no NCM link, no ACM port, black
panel. Two causes, both readable from the built `.config` without the
phone:

1. First light loads **no kernel modules**, yet `arm64 defconfig` leaves
   the two PHYs the DWC3 controller needs as `=m`:
   `CONFIG_PHY_QCOM_QUSB2` (USB2 PHY, `qcom,qusb2-v2-phy`) and
   `CONFIG_PHY_QCOM_QMP_USB` (USB3 QMP PHY). The controller's probe is
   deferred forever, no UDC ever appears under `/sys/class/udc`, init's
   gadget bind has nothing to bind, and there is no instrument left.
   Fixed by `scripts/config -e PHY_QCOM_QUSB2 -e PHY_QCOM_QMP_USB
   -e PHY_QCOM_QMP` + `olddefconfig` + Image rebuild, same pin mechanism
   as M1.1's three pins. (`qcom,dwc3` glue itself was already `=y` via
   `USB_DWC3_QCOM`; the Google common DTS carries no Type-C/TPM nodes, so
   peripheral mode needs no TCPM stack.)
2. The panel console (`console=tty1` + `simple-framebuffer` over the
   splash region) stays dark on this reboot path: ABOOT kills the
   bootloader splash on handoff from fastboot mode, and first light
   ships no DSI driver. The panel is therefore **not** an instrument on
   this gate; the heartbeat/pstore loop keeps writing to kmsg anyway
   (harmless) and to ttyGS0 once the PHY fix lets the gadget bind.

#### Attempt 2026-10-27 (third): every instrument silent — the USB glue never probed

Three fixes landed in this round, all found from the host side:

1. **configfs never mounted.** The init mounted `configfs` on
   `/sys/kernel/config`, but that directory is created by *userspace*,
   not by the kernel — nothing in `init/` or `fs/sysfs` makes it — so the
   mount failed against a hidden `/dev/null` file and the gadget was
   never built. Fixed by `mkdir -p /config` + `mount -t configfs configfs
   /config` (postmarketOS' initfs path; flame's initramfs has the same
   latent bug and escapes only because its boot chain pre-creates the
   directory).
2. **The real blocker: the DWC3 glue had no matching driver.** Since the
   flatten series (v7.0/7.1) `drivers/usb/dwc3/dwc3-qcom.c` matches only
   `"qcom,snps-dwc3"` (`dwc3_qcom_of_match` in 7.3.0-rc6-omamobile, one
   entry), and `dwc3-of-simple.c` carries no Qualcomm entry at all — but
   this Android-based tree's `sdm845.dtsi` still labels both wrapper
   nodes `"qcom,sdm845-dwc3", "qcom,dwc3"`. No driver claimed `usb_1`:
   no DWC3 core, no `/sys/class/udc`, no probe error, nothing on any
   instrument. The community Pixel 3 ports run the *old* driver with the
   old compatible (pmOS' fork pins `sdm845-6.11`/`sdm845-7.1-rc1-r0`), so
   the binding rename simply never surfaced there. Fixed by
   `compatible = "qcom,snps-dwc3", "qcom,sdm845-dwc3", "qcom,dwc3"` on
   `usb_1`/`usb_2` (old strings kept as fallback). The `vdda-phy`/
   `vdda-pll` swap suspicion from an early diff of the two forks was
   checked against the 7.1 reference and dropped: mainline order and
   pmOS order are identical (phy=l26a_1p2, pll=l1a_0p875).
3. **Instruments added where the plan was mute-by-design:** heartbeat
   echo onto ttyGS0, pstore ramoops node in the blueline DTS (1 MiB at
   0x9ff00000, `console-ramoops` readable after the next boot), and a
   `console=tty0` fbcon line — ABOOT's fastboot splash teardown kills
   `keep_bootcon`, so `console=tty0` is the only way kernel text can
   reach the panel at first light.

Side experiment worth recording: a self-built pmOS 6.11 kernel
(`kernel/sdm845-6.11` tag, their defconfig, our initramfs, same
concat-DTB v2 pack) booted alive but mute — with `CONFIG_EFI_ZBOOT=y`
the packaged `Image.gz` is an EFI-stub binary, so that build is *not*
proof for the reference stack, only for our packaging path. The pmOS
packaging detail they rely on (initfs, bootimg v2 with DTB appended per
their `initfs` + `deviceinfo` bootargs) is now reproduced stepwise.

#### Attempt 2026-10-27 (fourth): 7-second ABOOT return localizes the death to the QSCRATCH map — flatten's offset is wrong for SDM845

The timed panic probe worked as designed: flashing the probe image (panic
45 s after init) and the plain listener (no probe) both returned the
handset to FASTBOOT MODE **7 s** after the reboot command — while the
stock SP1A `boot.img` under the identical `fastboot reboot` booted on to
its logo (the owner saw it) and never returned. So the death is ours,
it happens well before 45 s, and with `panic=10` it is a *panic or abort*
in the first seconds of driver probe.

Reading the flatten driver closed the loop. `dwc3_qcom_probe()` in
7.3.0-rc6-omamobile computes the QSCRATCH window as
`res.start + SDM845_QSCRATCH_BASE_OFFSET` (0xf8800) — written for SoCs
whose wrapper node sits 0xf8800 below its QSCRATCH block. On SDM845 the
wrapper node's `reg` **is** the QSCRATCH region itself: every
working 6.11-era driver (ours in `kernel-pmos`, vanilla mainline's)
ioremaps `reg[0]` unshifted, and the two trees' QSCRATCH register
offsets are byte-identical — only the base computation changed. With
the shift, `qscratch_base` lands at `0xa7f1000`, inside the 0xa600000
wrapper range but in no man's land: `devm_ioremap()` checks no conflict,
so the first `GENERAL_CFG`/`vbus_override` write hits a block its GDSC
does not own, and the SoC aborts. Every symptom lines up:

- PHY-pin builds (glue unbound, no QSCRATCH write) lived minutes;
- the snps-dwc3-compatible build (glue bound, write at probe —
  `vbus_override` runs from probe in peripheral mode) dies in seconds;
- the pmOS 6.11 reference build (old driver, unshifted map) survived
  and just stayed mute for its own packaging reasons;
- stock boots the Google logo under the same reboot command.

**Fix (driver, not device tree):** the qscratch offset becomes match
data — `qcom,sdm845-dwc3` maps `reg[0]` at offset 0, `qcom,snps-dwc3`
keeps the 0xf8800 shift. The third round's DTS prepend of
`qcom,snps-dwc3` is reverted: it papered over the driver bug and pointed
the wrong (shifted) map at exactly the hardware that does not want it.
The probe stays armed on the test images: gadget first, panic at 45 s
second — the fastboot return is the boot's period at the end of sentence.

#### Attempt 2026-10-27 (fifth): the QSCRATCH map was half the bug — flatten anchors the *core* window at the wrapper reg too

The per-SoC QSCRATCH offset (fourth entry) changed nothing: probe and
listener images died at 5–6 s exactly like before. The flatten rework
does not only read QSCRATCH relative to the wrapper `reg` start — it
passes `probe_data.res` straight into `dwc3_core_probe()`, which maps
the DWC3 core globals at `res.start + 0xc100` and xHCI at `res.start`,
and then `dwc3_core_is_valid()` issues the first readl. The flattened
binding's SoCs anchor their wrapper node at the **core base** (eliza:
`usb@a600000`, reg `0xfc100`, QSCRATCH at `+0xf8800`); SDM845 anchors it
at **QSCRATCH** (`usb@a6f8800`, reg `0x400`). So on SDM845 the core read
hit `0xa709800` — the QSCRATCH-only fix had moved `qscratch_base` to the
right block while the first fatal access was never QSCRATCH but the core
probe's own validity readl. `devm_ioremap()` checks no conflict, so
nothing failed until the access; the abort needs no QSCRATCH write at
all, which is why every PHY-only diagnosis from the outside looked
alive-but-mute until the glue bound.

**Fix:** derive both windows from the QSCRATCH address — `ioremap`
QSCRATCH directly (match data: 0 for `qcom,sdm845-dwc3`, `0xf8800` for
`qcom,snps-dwc3`) and pass the core resource anchored at
`QSCRATCH − SDM845_QSCRATCH_BASE_OFFSET`. For the flattened SoCs both
computations are the identity; for SDM845 they reproduce exactly the
layout the 6.11-era driver used via the child node (`dwc3@…` reg) —
which is the tree every working Pixel 3 USB gadget boots on. Kernel
commits `16897c828` (driver), `7c0318228` (QMP PHY rails), `b5278c8ef`
(ramoops).

**The instrument now works unattended:** with `panic=10` a dead boot
warm-reboots into FASTBOOT MODE within seconds by itself, so the
flash → reboot → observe cycle needs no button holds anymore; a boot
that survives the probe's 45 s proves driver-probe aliveness, and a
surviving gadget must show ACM/NCM/SSH from then on.

#### Attempt 2026-10-27 (sixth): the driver is innocent — the whole 7.3 kernel line dies at 4-6 s, 6.11 survives

Three instruments ran back to back, all automatic (panic=10 turns every
death into a fastboot reappearance within seconds):

| build | boot args | outcome |
|---|---|---|
| fixA2 (dual-window fix + clocks-before-reset reorder) | bind active, probe 45 s | dead, ABOOT back at 4 s |
| same kernel | `--no-gadget` (UDC never written) | dead at 4 s — the bind never ran, so the death is not the gadget start |
| fl-phy (yesterday's "mute but alive" build, same bytes) | — | now dead at 4 s |
| fl-pmos (postmarketOS 6.11 kernel, same first-light initramfs) | — | alive through the whole 240 s window |

**Interpolation bug found mid-evening:** the `--cmdline` in
`initramfs/build` was single-quoted, so every `omadwc3q=` (and any
`${OMAMOBILE_EXTRA_CMDLINE}`) run above actually booted the literal text
`${OMAMOBILE_EXTRA_CMDLINE:-}` — the kernel ignored it and the driver ran
at full power. The scratch-only/off falsifications from the first
pass of this table are therefore VOID, not evidence; the fixed
interpolation (expand in shell, byte-assert the knob in the shipped
header) re-runs as off12. The two rows that never used the knob stand:
the 7.3 line dies at 4 s even with the gadget bind skipped, and the
6.11 kernel survives 240 s. The dwc3 window fixes stay (correct against
the binding either way, checkpatch clean); whether the driver is also a
trigger is exactly what off12's now-real `omadwc3q=off` decides.  Note:
the dtbo-restoration flash cycles both timed out waiting for the
handset — `dtbo_a` is still erased, which the 6.11 survival proves is
survivable and keeps as the one known state difference the 7.3 deaths
and the 6.11 survival share.

> **Klarstellung 2026-11-01, nachdem dieselbe Zeile heute beinahe in die
> Irre gefuehrt haette:** „6.11 ueberlebt mit geloeschtem dtbo_a" gilt weiter,
> aber der Satz ist duenn: er beruht auf EINEM 6.11er-ueberleben am 28.10.
> Die 7.1.0-rc1-Referenz ist am 01.11. mit exakt diesem geloeschten dtbo_a
> viermal innerhalb ~13 s gestorben (14:06, 14:09, 14:11, 14:18, gleiche
> Bytes ed2c225f, gleiches Kabel) und hat NACH dem Fuellen von dtbo_a mit dem
> Factory-dtbo (ff7bd6da, Schreib 16:31) zweimal ueberlebt: RAM-Boot ab slot_a
> 16:34 mit jetzt voller dtbo_a (Telnet 76 s). (Der ueberlebte RAM-Boot 15:35
> lief ab slot_b mit vollem dtbo_b und zaehlt nicht als Gegenfall.)
> Ob der 6.11er
> mit dem heutigen Bootloader/dtbo-Zustand noch ueberlebt, ist ungemessen —
> „loeschbares dtbo_a ist ueblich" ist damit KEINE sichere Voraussetzung mehr.
> Regel von jetzt an: dtbo_a und dtbo_b gehalten (Factory-Inhalt), vor jedem
> Experiment getvars incl. beider Retry-Zaehler lesen (um 16:27 war
> ueberraschend auch slot-unbootable:b ja).

#### Attempt 2026-10-28: off12 measures — with the dwc3-qcom driver fully off the 7.3 kernel still dies at 5 s

The fixed interpolation put a real `omadwc3q=off` into the header
(byte-checked in the shipped image), the driver binded nothing, no
register of the USB block was touched — and the ABOOT came back at 5 s,
before the 10 s userspace probe could fire.  The 6.11 kernel with the
same first-light initramfs lived through the whole 240 s window.  The
dwc3-qcom probe is therefore exonerated as the killer of the 7.3 line
(the window-anchoring fixes remain correct upstream hygiene), and what
remains is kernel-wide: 7.3.0-rc6-omamobile-push1 vs postmarketOS 6.11,
with the config the only cheap axis.  Next measurement: 7.3-rc6 built
from the pmOS 6.11 reference config (`out-blueline-pmoscfg`, pins kept,
panic probe 120 s) — survives: config, bisect symbols; dies: code,
bisect commits.

**pmoscfg measured (2026-10-28, image a9cd3b0f…):** the 7.3-rc6 kernel
built from the full 3501-symbol 6.11 reference config (olddefconfig
clean, all bring-up pins verified =y afterwards) died at 5 s, twice,
independently flashed.  Config is exonerated.  Note arm64 has no
`OF_APPENDED_DTB` — the concatenated-DTB layout is config-free, the
head.S probe always runs.  Next axis, one flash each: 6.11 kernel with
the 7.3-built DTB (`pmosdtb`); dies => the device tree (prime suspect:
the ramoops reservation), survives => a 6.12..7.3 code regression and
a commit bisect with the panic-probe loop as the test harness.

**pmosdtb was NOT a measurement (2026-10-28).** The image lived silently
for 400 s — but its probe sat at the END of init, behind the 30 s UDC
wait and `dropbear -R` keygen, so "probe never fired" and "kernel dead"
were indistinguishable.  The probe is now armed as a background timer
immediately after the pseudo-fs mounts (commit 8e9d8ae): a fired probe
proves kernel + PID 1 aliveness even when the main flow hangs.  The
`dr_mode` theory died on inspection: the 7.3 tree's
sdm845-google-common.dtsi carries `dr_mode = "peripheral"` exactly like
pmOS — the device trees agree on the role.

**pmosdtb was NOT a measurement (2026-10-28).** The image lived silently
for 400 s — but its probe sat at the END of init, behind the 30 s UDC
wait and `dropbear -R` keygen, so "probe never fired" and "kernel dead"
were indistinguishable.  The probe is now armed as a background timer
immediately after the pseudo-fs mounts (commit 8e9d8ae): a fired probe
proves kernel + PID 1 aliveness even when the main flow hangs.  The
`dr_mode` theory died on inspection: the 7.3 tree's
sdm845-google-common.dtsi carries `dr_mode = "peripheral"` exactly like
pmOS — the device trees agree on the role.

**The tree is upstream v7.3.0-rc6, squashed, plus only our four commits
(2026-10-28).** `git tag` is empty and the root commit 33267e524 is a
96114-file squash of the whole 7.3.0-rc6 tree; on top sit 16897c828
(dual-window), 349f27b (ramoops dts), beaeaf73e (`omadwc3q=` knob),
eddee2db (pointer cast).  There is no upstream 6.12..7.3 history in this
clone, so a code bisect cannot run inside it — the suspect set inside the
tree is exactly those four commits, and the "kernel code" axis otherwise
means an upstream 6.11 -> 7.3-rc6 regression that would need the real
upstream history fetched.

**dtb73 result corrected (2026-10-28).** The probe was armed for 25 s and
ABOOT returned at 5 s — that is a DEATH before the probe, not a fired
probe; the watcher's `<= 90 s` label was wrong and is now `<= 25 s`.  So
the 7.3 kernel on the pmOS 6.11 blueline device tree (no ramoops) also
dies at 5 s: the device tree does not rescue it.  Config (pmoscfg, two
independent flashes at 4-5 s), the dwc3 driver state (off12, 5 s), and
now the device tree (dtb73, 5 s) are all exonerated; every surviving
first-light boot we have measured was a 6.11 kernel, and every death was
a 7.3 kernel.

**Config delta, informational (2026-10-28).** Comparing the surviving
6.11 self-build `.config` to the 7.3 `pmoscfg` `.config`: 160 symbols set
in 6.11 are absent in 7.3, 672 new in 7.3.  Most are auto-selected
crypto/CPU-feature symbols, but the absent set includes arm64 base
symbols — ARM64_PAN, ARM64_LSE_ATOMICS, ARM64_USE_LSE_ATOMICS,
ARM64_WORKAROUND_REPEAT_TLBI — whose behaviour differs at boot; the bare
build prints these explicitly to see whether olddefconfig keeps or drops
them on the 7.3 tree.

**Decisive single-variable test armed (2026-10-28): `rc6-bare`.** A
`git worktree` at the squashed root 33267e524 (bare upstream 7.3.0-rc6,
none of our four commits, ramoops-free dts confirmed) built from the same
pmOS 6.11 config + 21 pins, packed with the early 25 s probe.  This is
the maximal-innocence 7.3 image.  Dies at 5 s => our four commits are
innocent and the regression is upstream 6.11 -> 7.3-rc6 (fetch upstream
history to bisect).  Survives => one of our four commits is the killer
(ramoops dts being the prime suspect; bisect those five).

**rc6-bare — our four commits are exonerated (2026-10-28, image
1ca8177a…).**  [Review 2026-10-28: same caveat — "exonerated" holds only
once the 4 s ABOOT return is proven to mean kernel death; see the review
section.  The build-content facts (no bring-up commits in the tree) are
verified regardless.]  A `git worktree` at the squashed root 33267e524 — bare
upstream v7.3.0-rc6, none of 16897c828/349f27b/beaeaf73e/eddee2db, the
dts carrying no ramoops node — built from the same pmOS 6.11 config + 21
pins, flashed, died at 4 s (before its 25 s probe).  So the death is not
anything we wrote: it is an upstream regression in the range 6.11 (every
survivor) -> 7.3.0-rc6 (every death), reproducible at 4-5 s regardless of
config, device tree, or dwc3 driver state.  The clone is a tarball squash
(`git rev-list --count HEAD` = 6, no tags, root touches 96114 files), so
it carries no v6.12..v7.2 history; a mainline bisect means fetching the
real upstream history and bisecting there, building each suspect with our
config + first-light initramfs, oracle = the early panic-probe's ABOOT
return window (survives the probe window = good, dies before it = bad;
the probe->panic=10->fastboot path needs no USB, so the oracle works even
with USB compiled out).

**Next cheap single-variable step before that multi-hour bisect: rc6-nousb
(armed).** v7.3.0-rc6, pmOS config with the whole USB stack disabled
(CONFIG_USB + DWC3/xHCI/configfs off; PHYs, clocks, interconnect, pstore
left on), early probe.  Survives => the regression is inside the 7.3 USB
core/xHCI/dwc3 stack (narrow within it next).  Dies => it is 7.3 core
(arm64 head, clocks, cpuidle/PSCI, mm, scheduler), a much wider search,
and the bisect should start on core subsystems, not USB.

**rc6-nousb — the 7.3 death is CORE, not USB (2026-10-28).**  [Review
2026-10-28: retitle honestly — "CORE" here means "the ABOOT-return-at-
4 s signal persisted with USB compiled out"; it is only evidence of a
CORE cause once the signal's meaning is proven by the deterministic
probe.  Treat as hypothesis.]  Same
v7.3.0-rc6 + pmOS config with the entire USB stack compiled out
(`USB-Symbole gesetzt: 0`; clocks/interconnect/pstore/PHY left on), early
probe 20 s: died at 4 s, before the probe.  So the 4-5 s death is not the
dwc3/xHCI/configfs stack either — it is 7.3 core that faults on this
board before userspace.  A mainline commit bisect 6.11 -> 7.3-rc6 is the
only way to name it and is a multi-hour effort that, by itself, makes the
phone no more usable.

**The panic-probe oracle is only good for EARLY hard deaths (2026-10-28,
the `alive` run).** The known-good 6.11 (kernel-pmos) + the pmOS 6.11
device tree + OUR first-light initramfs (early probe armed right after
the mounts, USB on): 300 s with NEITHER the 172.16.42.1 NCM link NOR any
ABOOT return, and no ACM.  Two readings, and they matter more than the
7.3 bisect: (a) our configfs gadget has bound a UDC on NO kernel we have
ever booted, including the pmOS known-good — so the gadget bring-up is
the real, still-open blocker, independent of the 7.3 death; and (b) the
probe's `echo c > /proc/sysrq-trigger` + `panic=10` may warm-reboot a
post-init panic straight back into boot_a (a self-rebooting boot loop)
rather than into FASTBOOT MODE, so "no fastboot return" is ambiguous
between "alive and looping" and "hung before the probe".  The 7.3 deaths
we timed were pre-init (4-5 s) and DID surface as fastboot; a post-init
panic's landing has never been proven to be fastboot.

**Decisive instrumentation fix armed next: land the probe in FASTBOOT
deterministically.** Replace the probe action `echo c > sysrq-trigger`
with `reboot bootloader` (LINUX_REBOOT_CMD_RESTART2 to ABOOT; fall back
`reboot recovery`/`reboot fastboot`), so a kernel whose init reaches the
probe is GUARANTEED to show fastboot within seconds, and one whose fastboot
return we then time becomes a true "init ran" oracle.  Then re-run the
6.11-alive flash: fastboot in ~20-40 s => init runs and it is purely the
gadget that never binds (pivot 100% to configfs/UDC bring-up); still
nothing in 300 s => even the known-good 6.11 does not reach our init, so
the initramfs/bootargs packaging is the bug, not the kernel at all.

## Review 2026-10-28 (owner): the 7.3 findings are a HYPOTHESIS, not a measurement

**One signal, two readings (review point 1, accepted).** Every "TOT nach
4-7 s" in the tables above really means: after `fastboot reboot` the
handset answered FASTBOOT again 4-7 s later, without us asking.  Nobody
ever saw why ABOOT came back.  The working assumption is a panic ->
`machine_restart`/PSCI restart carrying the restart2 command line
("bootloader" from ABOOT's own reboot) -> ABOOT shows fastboot; but a
watchdog reset that ABOOT treats as boot failure landing in fastboot is
equally consistent with everything measured.  With that ambiguity, the
"7.3 core regression" chain rests on a signal with zero kernel log lines
behind it.  Until the deterministic probe (below) fires on a boot we
control, ALL rows above are measurements of *the signal*, not of the
kernel; no 6.11 -> 7.3 bisect before this is settled.

**"6.11 lebt" was never proven either (review point 2, accepted).** The
early probe never observably fired on any 6.11 boot: the 240 s fl-pmos run
shipped no probe at all, and the 300/400 s silent runs had the probe
armed in the initramfs but produced no observable outcome.  "Kernel lebt
240 s" was an absence-of-death inference; "hangt vor init" is equally
open.  Consequently "the gadget is the real front" was premature — it is
one reading of silence.  The alive2 run (probe issues `reboot bootloader`
explicitly via busybox RESTART2 instead of hoping a panic lands in
fastboot) is the arbiter: fastboot inside ~20-40 s proves the kernel
reaches our init and only the gadget fails; continued silence proves our
initramfs never reaches init (bootargs/packaging bug) — evaluate before
concluding anything.

**Ground truth is missing (review point 3, source verified today).** No
image we ever flashed was unmodified vendor/distro output: even "fl-pmos"
was OUR first-light initramfs packed by OUR mkbootimg call.  The official
pmOS route for blueline builds its own image (`pmbootstrap install` +
`pmbootstrap flasher flash_rootfs/flash_kernel`, wiki
Google_Pixel_3_(google-blueline)#Installation); the prebuilt image
farms have sargo/beryllium but return 404 for google-blueline
(images.nura.eco/bpo/edge/google-blueline, v25.12, v26.06 checked
2026-10-28).  So the reference = build it with pmbootstrap in a docker
workaround (device-google-blueline 7-r? at gitlab.postmarketos.org
pmaports master; kernel linux-postmarketos-qcom-sdm845 pkgver
**7.1_rc1-r4**, fork gitlab.com/sdm845-mainline/linux tag
`sdm845-7.1-rc1-r0`), record source URL + sha512 of the deviceinfo
(`d67a19ae…`, in the APKBUILD) and of the produced boot.img, flash it
unmodified, check NCM/172.16.42.1.  Only after that passes do we swap
our pieces in, one per boot.

**The pmOS packaging facts differ from ours and are candidates (found
while verifying point 3):** deviceinfo sets `kernel_offset 0x8000` (we
flash 0x0 after the ABOOT rejection experiment) and
`deviceinfo_append_dtb=true` (same concat layout we converged on); the
device's official `kernel-cmdline.conf` is exactly
`console=ttyMSM0,115200` — no `console=tty0`, no `printk.devkmsg`, no
`androidboot.*` args, while every image we ever shipped carried them.
None of them is suspect or innocent by measurement; the reference image
settles which of our deviations matter.

**Serial console is available on this handset (review point 4, wiki +
AOSP docs verified today).** pmOS wiki, same device page: USB-C breakout,
A1 GND -> adapter GND, A8 SBU1 -> adapter RXD, B8 SBU2 -> TXD,
**115200 baud**, 3.3 V nominal (1.8 V also works); Google's own serial
debug cable + Peter-Easton's android-debug-cable-howto document the same
pins for Pixel-class devices.  AOSP's Pixel kernel docs list
`fastboot oem uart enable` + `fastboot oem uart config 3000000`; whether
this b1c1-0.4 LK ABOOT implements `uart`/`uart-enable` has NEVER been
checked on this handset — next time it sits in fastboot, run the
read-only probe `fastboot oem help` and record the exact output (a bare
`fastboot oem uart enable` may be a persistent bit flip, so it needs its
own decision).  With a real console we read the death instead of timing
it; the breakout is a ~10 € part and the honest fix for the "one signal,
two readings" problem at its root.

**alive2 verdict (2026-10-28, /private/tmp/fl-alive, 6.11 pmOS kernel +
pmOS DTB + reboot-bootloader probe armed at init start, 20 s):** 300 s
after `fastboot reboot`: no FASTBOOT, no NCM, no ACM. Two readings stay
open and we do NOT pick one: (a) our initramfs/packaging keeps even the
known-good 6.11 from ever reaching `init` — consistent with review point
2's "hängt wahrscheinlich vor init"; (b) init ran but the probe's way
back (`reboot` with RESTART2 command "bootloader", fallbacks
fastboot/recovery, last sysrq+panic=10) does not make THIS ABOOT show
fastboot — mainline pmic-restart handlers commonly drop the restart
command, so "probe fired but nobody saw it" is fully possible. The
signal has no witness without a console; that is the review's point 4
made concrete. (The watcher script's own printed verdict — "selbst der
bekannte 6.11 erreicht unser init NICHT => Initramfs/Bootargs-Packen ist
der Fehler" — is reading (a) hard-coded into its if/else thresholds
(`t<=12`/`t<=90` leave only silence ⇒ blame the packaging); it is
evidence of the ambiguity, not of the cause.) The owner ordered the
USB-C SBU breakout + 3.3 V USB-UART
adapter today (see einkaufsliste-uart-pixel3.md next to this file).

**`fastboot oem help` on this ABOOT (read-only probe, 2026-10-28):**
`FAILED (remote: 'Invalid oem command help')` — b1c1-0.4-7617406 has no
verb to enumerate OEM commands, so whether `oem uart enable` exists here
is unknowable without trying it (which is a write). pmOS's blueline
recipe uses the SBU serial console purely via `console=ttyMSM0,115200`
in the kernel cmdline without any oem switch, so the cable alone is the
planned path; we leave the uart bit untouched.

**Two one-variable packing tests, both negative (2026-10-28, owner
instructed to run them before any long reference build).** Both on the
current 7.3 kernel (dual-window + knob, our config), early probe 20 s,
gadget on, one flash each, byte-verified in the shipped v2 header
(kernel_addr at +12 of this mkbootimg's layout — the assert in
initramfs/build now checks it):
- `off8000` (sha 94705b9d…, --kernel-offset 0x8000 like
  deviceinfo_flash_offset_kernel, rest of our cmdline): FASTBOOT back at
  **4 s** — same as the 0x0 baseline. The pmOS offset does not save 7.3.
- `cmdpmos` (sha ab61ff12…, cmdline replaced by exactly pmOS
  `console=ttyMSM0,115200`, no tty0/devkmsg/androidboot/panic): FASTBOOT
  back at **4 s**. The cmdline stack does not save 7.3 either.
Reading under the review's hypothesis label: the ABOOT-return signal is
now byte-for-byte IDENTICAL for {offset 0x0, 0x8000} × {our cmdline,
pmOS cmdline} × {full config, pmOS config, USB-less, bare rc6}. Whatever
it is, no packing knob on our side changes it. (Kernel-7.1 fork next —
if THAT survives at 4 s with the same packing, the signal was never the
packing and the kernel-version axis gets its first clean contrast.)

**Kernel basis switched to the proven fork (owner decision 2026-10-28,
replaces any 6.11→7.3 bisect):** pmOS ships blueline on
`https://gitlab.com/sdm845-mainline/linux` tag `sdm845-7.1-rc1-r0`
(APKBUILD pkgver 7.1_rc1-r4). Tarball downloaded from the tag archive
URL; sha256 of OUR download is 4389f4ae6f5b80174a4b2d2da93ab5afc1d3922db215ebabf7c01436494eb9f2
while the APKBUILD records 94da173aaf74dd33ef8ff9015e92759481cd0da5bd8a1e52c8664fd372d48a1155655001ad2e9d26557733c71ae8bc448e4ebdf1372b8f32159907a35f0306a9
— GitLab's archive endpoint is not byte-reproducible across servers, the
content is the tag. Extracted to `android-mainline/kernel-71` (1.7 GiB).
Basis .config = the DISTRO config `config-postmarketos-qcom-sdm845.aarch64`
straight out of the pmaports shallow clone: all 21 bring-up pins are
already =y except `USB_CONFIGFS` and `USB_LIBCOMPOSITE` which upstream
carries as =m — flipped to =y with MODULES off (first light loads no
modules). Building Image.gz + DTBs in the arm64 container
(`out-blueline-71`) as this is committed. First flash plan after the
build: pack with OUR firstlight initramfs + probe 20 s at the pmOS
deviceinfo offset 0x8000, gadget on. Timebox from the owner: if the
reference build plus these tests still show no NCM after 2–3 more
flashes, no further guessing — we wait for the serial console.

**sdm845-mainline 7.1 fork flashed: the 4-5 s return follows it too
(2026-10-28, four flashes, images byte-verified, sha of first flash
52a1db6c…).** The owner's kernel-basis switch is built exactly per the
pmOS recipe — tag archive `sdm845-7.1-rc1-r0`, DISTRO config
(21 pins: all already =y except USB_CONFIGFS/USB_LIBCOMPOSITE, flipped
=y with MODULES off), deviceinfo offset 0x8000, our firstlight initramfs
with early probe. Results: probe 8 s → FASTBOOT at 4 s; probe 20 s → at
4 s; probe 40 s → at 5 s; **no probe file at all (panic=10 still on the
cmdline) → at 4 s**. The probe NEVER tracks the return time on the fork,
and the fork's own distro config has `QCOM_WDT=y` built-in, so "we never
feed the PMIC watchdog" fails as an explanation for the fork's return
too. Meanwhile the only 300 s-silent run in the whole campaign is the
6.11 with the probe armed early — and every kernel that ever returned at
4-5 s carried panic=10 on its cmdline, as did alive2. So after 11+
flashes the signal is still
exactly as ambiguous as the review said, just sharper: a kernel
returning fastboot at 4-5 s is consistent with panic-death AND with an
ABOOT-side return without any kernel ever running (the documented ABOOT
text-offset rejection — observed as an instant refusal in RAM-boot mode
at 0x8000 — was never proven absent in flash mode; and a
watchdog-boot landing in fastboot is standard LK policy at 0x0). Per the owner's own timebox (no NCM after the two packing tests
plus ~2-3 further flashes): **flash storm over, no more guessing.** The
discriminator is one serial read at power-on: ABOOT prints its own boot
reason ("reboot reason"/"fastboot mode" vs watchdog vs textoffset
complaints), the kernel prints whatever survives — and the fork kernel,
currently the most promising basis (it is the distro's shipped config,
packing matches theirs, only OUR initramfs and cmdline deviate), gets
its next flash ONLY with the console attached. Also documented honestly:
the host-side `make olddefconfig` incident (macOS make dirties the tree,
O= builds then refuse it — rebuilt on a container-side copy; skill
updated). The fork build itself is green: Image.gz 26,192,165 bytes +
DTB + config-71-actual in `android-mainline/out-blueline-71`, sha256s in
`SHA256SUMS-build`.

**Ground-truth package facts for the pmbootstrap reference (verified
2026-10-28, no phone involved).** `pmbootstrap init` in the pmos-ref
container (Alpine edge, pmbootstrap 3.12.1) completed via a piped
answer file once the v3 config keys were known — final config:
device=google-blueline, channel=edge, work=/work/pmbootstrap-work
(host: pmos-ref-build/), UI fell back to `console` (the intended
`console-mobile` must be re-piped at the UI prompt). Repo facts from the
live edge index: the mirror moved (mirror.postmarketos.org 301s to
mirror.nura.eco); the distro ships the fork as a PREBUILT aarch64
package `linux-postmarketos-qcom-sdm845 7.1_rc1-r4` (57 MiB, source
tag sdm845-7.1-rc1-r0 — same tarball we built ourselves) plus
`postmarketos-initramfs`. So the truest reference boot does not need a
kernel build at all: unpack their apk, take their initramfs through the
device's initfs recipe, pack with THEIR bootimg hook at THEIR offsets.
(Scratched after checking: the initramfs package's cmdline parser has
no ssh-key handling — grepping `authorized` in its sources is empty —
so a reference image's SSH access comes from the installed rootfs user,
not from a cmdline knob.)
This stays QUEUED behind the serial console per the owner's timebox —
no further phone flashes until the boot reason is readable.

**Ground-truth reference build in flight (2026-10-28 evening, owner said
"weiter").** Per the owner's correction we do NOT drive pmbootstrap with
an answer loop any more: the container's `/root/.config/pmbootstrap_v3.cfg`
is written directly (pmbootstrap 3.12.1 v3 keys: aports/work/device/ui/
user/hostname/timezone/locale/service_manager/build_pkgs_on_install),
channel comes from the pmaports branch. First `install --split` run then
failed with `postmarketos-ui-console-mobile (no such package)` — that UI
name does not exist in edge (index shows `postmarketos-ui-console[-openrc]`);
the cfg now says `ui = console` + `service_manager = openrc`. Recorded
sources and hashes for the reference (review point 3 demanded exactly
this): pmaports shallow clone HEAD `1eb4dce28ef2d0ecc8651914bcb4972083eefb0f`
(branch main = edge); device-google-blueline files sha256 deviceinfo
`3a0d981f682b6d180c70a6a53744defcf5488051b2c802f42be22517f89dd0df`,
kernel-cmdline.conf `3a8b7899cbb294e12f6b7bb38f620553b9beb9bf57a0d1d31e19b45bcf2c0eb0`,
APKBUILD `1f9524e0b13c58133032debbb6b30b42520e9a609682c0f2e307cfa921e2e01b`,
modules-initfs `5018e59bf656fef16800667a8bd0347bfbfa8a35ed8653a037c23494e11d4578`;
the distro's PREBUILT kernel apk `linux-postmarketos-qcom-sdm845-7.1_rc1-r4.17d6ae79.apk`
(57,994,142 bytes, sha256 `d0b4b950a500cede73fe5ce094060b1f9d608e3b4cbcb9d59bf2d876b2dc9804`)
from the moved mirror `https://mirror.nura.eco/postmarketos/main/aarch64/`;
our fork tarball sha256 `4389f4ae6f5b80174a4b2d2da93ab5afc1d3922db215ebabf7c01436494eb9f2`.
`install --split` ends with THEIR boot.img built by THEIR initfs/mkinitfs
pipeline at THEIR deviceinfo offsets — that file, byte-verified and
hashed, is the single flash that decides whether this handset and ABOOT
are fine and our own initramfs/packing is the failing component (or
whether even the untouched distro artifact shows the same 4-5 s return,
which would move the suspicion to the handset's state, e.g. the erased
dtbo_a). Nothing is flashed before that file exists and is checked.

**Ordering from this review (replaces the previous next-steps text):**
1. alive2 verdict (armed, deterministic `reboot bootloader` probe) —
   defines what silence and timing mean at all.
2. pmbootstrap reference build, flashed unmodified, NCM check — ground
   truth, with source + hashes recorded here.
3. serial console: cable + `fastboot oem help` probe; then read instead
   of infer.
4. only then: bisect decisions, if any axis still needs one.

**Next two measurements, both built and byte-verified (2026-10-28):**
`pmosh` (fl-pmosh, 81941839…): self-built 6.11 kernel + our 7.3 DTB,
early probe 25 s — is the self-built reference kernel alive at all, and
does its UDC finally bind (NCM watch added: 172.16.42.1 ends the cycle
early and SSH collects the boot log)?  `dtb73` (fl-dtb73, 3816a149…):
7.3 Image.gz (dual-window fix + knob) + the pmOS 6.11 blueline DTB,
early probe 25 s, verified byte-level to carry both blobs — if it dies
at 5 s like pmoscfg did, device tree AND config are exonerated and the
7.3 kernel code is the sole remaining axis: commit bisect with the
probe loop as harness.  This also tests how far the self-built 6.11
diverges from pmOS's shipped boot.img; if the shipped image survives
where the self-build dies, suspect the build/packaging, not the code.

### M1.3 — the LUN map and the calibration backups (read-only)

- Record which UFS LUN carries the partition table, `userdata` and each
  calibration partition (`persist`, the modem's `efs`/`modemst*` as their
  PARTNAMEs appear in `/sys/class/block/*/uevent`): this phone's answer
  is the `MAIN_LUN` key's value (docs/RELEASES.md 3.2) and the GPT
  exception entry's LUN. The Pixel 4 XL notes in review
  ([#52](https://github.com/derekross/omarchy-mobile/pull/52)) name seven
  UFS LUNs on its SM8150 phone; expect a similar map here.
- Back the calibration partitions up over SSH with `dd iflag=direct`
  (checksummed, to the laptop, off-repo; sha256 recorded). Before the
  first slot-flag write, no gate may run without these.
- Pass: backups complete and checksummed twice. Risk: reads only.

### M1.4 — capture the GPT before any slot-flag write

- For every LUN found in M1.3: save sectors around the primary and backup
  GPT (LBA 1, 2, last-1, last and the header regions), record the slot
  priority, successful and trial bits of every partition's attributes,
  and have `gdisk v` report both headers' CRCs. The Pixel 3 generation
  has field reports of slot-flag writes leaving the backup GPT header
  inconsistent, which bricks boot selection — the before/after capture is
  what lets this plan see it and put it back.
- This gate also fills CONTRIBUTING 3.1's exception entry for blueline:
  LUN, the four LBAs, the attribute bits, the CRCs it rewrites, the
  rollback (dd the saved sectors back), and the way back (stock slot A,
  or EDL with the unlocked phone). The entry lands in the repository
  before the write that uses it.
- Risk: none yet; it only reads.

### M1.5 — write slot B (the first writes)

- Build the root image with `ROOTFS_PACKAGES` from the descriptor's
  package (`tools/build-rootfs` — its first user outside Tensor), flash
  `userdata` through `tools/install-phone`'s guards and `boot_b` by hand
  at M1.1's recipe, now with the persistent root config.
- Keep stock `dtbo_b` at first: ABOOT applies it onto the boot image's
  appended DTB. The Pixel 4 XL notes in review
  ([#52](https://github.com/derekross/omarchy-mobile/pull/52)) tame that
  overlay with a matching 12-entry no-op dtbo; if the stock overlay
  fights our nodes, flash our own `dtbo_b` (a matching table with our
  one change) and record which entry changed.
- Pass criteria as M1.2 plus: the root mounts `rw` on `userdata`, every
  other partition still reports `ro` after boot, and the guard's
  allowlist file matches the descriptor's three names.
- Risk: `userdata` was already wiped by the unlock; `boot_b` held a stock
  copy that the factory image can restore (flash-all restores both slots'
  images including GPT-independent state; the factory image is saved
  off-device before this gate).

### M1.6 — mark slot B bootable (CONTRIBUTING 3.1's named exception)

- The only risky write of this plan, by hand, once, never from a service.
  Set slot B's bootable attributes on the LUN M1.3 named, exactly the
  bits the merged exception entry names.
- Before and after: dd the four LBAs, re-run `gdisk v`, compare CRCs;
  **refuse the reboot unless both headers parse and the headers outside
  the written entries are byte-identical to the saved ones.**
- Pass: the phone boots slot B by itself (`androidboot.slot_suffix=_b` in
  `/proc/cmdline`); after a healthy boot, `reboot-to bootloader` still
  reaches fastboot; after the success bit is applied (the same named
  write, second use), `getvar all` reports slot B successful.
- Rollback: dd the saved sectors back (attended, storage guard cannot
  block this write). Way back: slot A stock still boots throughout.
- Risk: high; this is the gate the M1.4 capture exists for.

### M1.7 — stay booted

- systemd reaches the session on the software renderer; the device
  package's policy (power key ignored for logind, `usb0` unmanaged by
  NetworkManager, whole-disk node hidden from desktop tools) is in place
  from the package, not hand-copied.
- A systemd reboot and a `reboot-to bootloader` round trip survive; the
  field reports' warm-reboot warning is verified on this phone and its
  result recorded (if warm reboots are poisoned, the reboot path gets a
  cold-boot policy and this line cites the evidence).
- `tools/phone-smoke` runs and its report opens the pull request.

## Reference build result (2026-10-28): the unmodified distro boot.img BOOTS — and the 4-5 s signal dies as a device property

Review point 3 executed: built the distro's own image rather than our
packing, so a known-good artefact exists at last.

Build (all inside Docker, Alpine edge arm64, `pmbootstrap` 3.12.1,
pmaports `main`/edge HEAD `1eb4dce28ef2d0ecc8651914bcb4972083eefb0f`,
device `google-blueline`, `ui = console`, `service_manager = openrc`):
`pmbootstrap install --split`. The distro packed its own boot image with its
own bootimg hook — kernel + DTB + initramfs + offsets, nothing of ours
involved.

- `boot.img` 28,729,344 B, sha256
  `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`
  (from `chroot_rootfs_google-blueline/boot/boot.img`), sha verified on the
  host after the copy, before the write.
- kernel inside: `linux-postmarketos-qcom-sdm845 7.1_rc1-r4` — the same fork
  we rebuild from source.
- rootfs images also produced (`google-blueline-boot.img` 536,870,912 B,
  `google-blueline-root.img` 1,205,862,400 B) but NOT flashed: only `boot_a`
  was written, the handset's rootfs partition is still the Ubuntu
  Touch/pmOS one.
- Build gotcha worth keeping: pmbootstrap on the macOS bind mount left stale
  directory entries (readdir lists a name whose `stat` is ENOENT, same inode)
  that made its own `du -ks` size step fail, and `rm -rf` could not clear it
  (ENOTEMPTY). Moving the whole work path onto a named docker volume fixed
  it. Do not debug such a phantom file — move the work path.

**Measured:** `fastboot flash boot_a` + `fastboot reboot` -> the handset did
NOT come back to fastboot within 300 s, and the Mac saw no USB attach at all
in that window (no fastboot, no `172.16.42.1` NCM, no adb). The owner looked
at the handset: **the panel shows a pmOS text console / login.** So this
image is alive and driving the display while our images "die".

What that settles:

1. **The handset, slot A, ABOOT and the fork kernel are good.** A distro
   image boots to a login and stays up for minutes.
2. **The 4-5 s fastboot return is image-specific, not a device or slot
   policy.** If ABOOT were returning because slot A was flagged unbootable
   or because of a boot-failure/watchdog policy, the reference image would
   have returned in the same seconds. It did not.
3. **`172.16.42.1` NCM is not a liveness oracle.** The known-good reference
   never presents it to this host either (its console is the panel +
   `ttyMSM0`, and its network config is not the gadget config we assumed).
   File evidence for that sentence, checked 2026-10-29 rather than from
   memory: the only surviving result file of that run,
   `pmos-ref-build/ref/ERGEBNIS-REF.txt`, reads verbatim `kein boot.img in
   /work/export gefunden` — the flasher bailed out before its observation
   loop, and the later-copied `boot.img` (20:12, sha256 `ed2c225f…`) is the
   one that was flashed. Searching every surviving file under /private/tmp
   for `172.16.42` returns only the scripts that were supposed to look for
   it — not one hit from the evening itself. So the reference was just as
   mute on the bus as v0q: **USB peripheral on this handset + this Mac has
   never been observed with ANY mainline image.** M1 ("NCM gives us the
   console") therefore rests on two unproven claims in series — that our
   gadget binds, and that a binding gadget would show up at this port at
   all. Neither panel nor host can separate them; only a second,
   independent wire can.
   Every past verdict that leaned on a missing NCM was measuring the gadget,
   not the kernel — this retroactively weakens every "TOT" row above, exactly
   as the owner's review predicted.
4. **The `panic=10` arithmetic (owner's point) holds**: the no-probe k71 run
   carried `panic=10` and still came back at 4 s, so panic -> 10 s wait ->
   restart cannot explain that row. Either ABOOT returns on its own for our
   images, or the reboot path never goes through the panic timer.

What it does NOT say: why our images return at 4-5 s. The panel is now a
free console for exactly this question — the fork kernel drives the panel,
so a boot with `console=tty0` prints the kernel log (and any panic text) on
the display. Next: part-for-part swap starting from this reference, reading
the panel instead of guessing —

| step | kernel + DTB | initramfs | packing | reads the panel |
|---|---|---|---|---|
| 1 (done) | distro | distro | distro | login, alive |
| 2 | distro (unpacked from `ed2c225f`) | OURS | distro offsets | our prints? panic? |
| 3 | OUR fork build | distro initramfs | distro offsets | distro boot? |

`fastboot getvar all` (read-only) is still owed at the next fastboot window
to rule slot retry/unbootable flags in or out as a second variable.

## 2026-10-29 14:40 — what the device page actually says (quoted, not read into)

Source, checkable: **postmarketOS wiki, page `Google_Pixel_3_(google-blueline)`,
revision oldid 93743**, permanent copy
`https://web.archive.org/web/20260610002652/https://wiki.postmarketos.org/wiki/Google_Pixel_3_(google-blueline)`
(fetched 2026-10-29). Reading `https://wiki.postmarketos.org/...` directly on
2026-10-29 answers Anubis (bot wall) and redirects to `wiki.nura.eco`, which is
why a first reading of this page came back wearing another wiki's name; the
cells below are the archived pmOS revision, and the live mirror showed the same
values. Cell contents verbatim:

* **USB Networking: `Works`** — legend text: "After connecting the device with
  USB to your PC, you can connect to it via telnet (initramfs) or SSH (booted
  system)."
* **USB OTG: `Broken`** — "USB On-The-Go or USB-C Role switching."
* Flashing, Internal storage, Screen, Touchscreen, Battery, FDE: `Works`.
* Kernel package on the page: `linux-postmarketos-qcom-sdm845` — the same fork
  our blob comes from (`7.1.0-rc1-sdm845`).

Honest limit: the page names no host OS and no test date, and it says nothing
about this Mac. `Works` means somebody got it over mainline — it does not
excuse our gadget side, it only moves the burden of proof to a place where it
can be measured independently. Which makes the exact wording of our own
finding important: the reference was not measured mute at the bus, it was
**never measured** there (see the `ERGEBNIS-REF.txt` quote above - the flasher
left before its loop). "ungemessen", not "stumm".

### The second channel, documented for exactly this handset

From the same page, section "UART", taken over verbatim:

1. USB-C breakout with SBU1/SBU2 broken out + a serial adapter. Wiring:
   `A1 (GND) - GND`, `A8 (SBU1) - RXD`, `B8 (SBU2) - TXD`.
2. Levels: "Voltage is 3.3V, although 1.8V seems to work as well." Baud 115200
   — exactly our kernel cmdline `console=ttyMSM0,115200n8`.
3. Direction: "it won't work if the plug is reversed on one side"; in the
   original wording a TB3/USB-3 capable cable, with the Thunderbolt logos on
   the same side as the phone's screen and the `A` side of the breakout out.
4. **Why this is the channel:** phone in fastboot, then `fastboot oem uart
   enable`, then power off. Two further sources confirm the command for this
   exact device: AOSP "Build Pixel kernels" ("If you have a serial dongle and
   want to enable serial logs … `fastboot oem uart enable`", device table
   names Pixel 3 blueline) and `Peter-Easton/android-debug-cable-howto` ("If
   all goes well, fastboot will report OKAY", same orientation rule).

The command writes no partition, so it cannot damage the fallback. What it
does leave behind is documented on the cable howto: uart stays enabled across
a bootloader re-lock until `fastboot oem uart disable`, and the same command
undoes it.

### Orderable parts (a "Google debug cable for Pixel 3" is not a product)

SuzyQ is the Chromebook/CCD cable and does not fit this phone; what the page
describes is a plain SBU breakout. Concrete list:

1. **USB-C male breakout board with SBU1/SBU2 on header pins** — search terms
   "USB-C male breakout board SBU", "USB 3.1 Type-C male break out PCB". A bare
   USB-2 male breakout has no SBU pins and cannot work.
2. **USB-UART adapter with a 3.3 V/1.8 V selectable VIO** — CP2102 or FT232R/R3
   based (FT232RL breakout, CP2102 breakout); jumper set to 3.3 V, which the
   page says works, 1.8 V per the same sentence is also tolerated. Connect
   adapter VIO/VTTL to the breakout's 3V3 **only if the breakout feeds it**;
   otherwise leave the phone's VBUS pin unconnected and link only GND, SBU1,
   SBU2 — the phone is its own power source.
3. **A thick USB-A/C-to-C cable marked USB 3 / TB3** — the page's own words:
   thin charge cables do not carry SBU ("I had to use a thicker TB3/USB 3.0
   capable cable").

Wiring (the page's table, drawn):

```
   phone USB-C                  breakout            UART adapter
   ----------                   ---------           ------------
   A1  GND          ─────────── GND        ─────── GND
   A8  SBU1         ─────────── SBU1       ─────── RXD
   B8  SBU2         ─────────── SBU2       ─────── TXD
   B5/B9 VBUS 5V    (leave open unless the adapter needs a shared GND ref)
   A4/A9 TX/RX USB2 (leave open - that is the side that never enumerated)
```

Direction: the cable is symmetric, SBU1/SBU2 swap with plug orientation; if the
terminal stays empty, flip the plug at one end before believing anything is
broken (page: "it won't work if the plug is reversed on one side").

### Cheapest measurement first, and it is a boot_a write

Before any hardware arrives, one flash answers the host-side question outright
(the reference was never measured at the bus, see above): flash
`pmos-ref-build/ref/boot.img` — sha256 re-measured 2026-10-29 as
`ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82`, 28729344 B,
matching `SHA256SUMS-ref` — and poll **every** USB enumeration for 5 min
(`ioreg -p IOUSB -l` + `system_profiler SPUSBDataType` diffed against a
before-snapshot), not only `172.16.42.1`. If the reference enumerates in full
mode, the difference is our v0q image; if it never appears, the answer is
host/cable/macOS and every gadget build from here is shouting into a wall.
Runner: `device/blueline/firstlight/ref-enumeration-test.sh`.

**Consequence for the order of work:** no further gadget build on hope. UART
first — the parts sit with the owner, ordering is the one open hand — and only
then, with a console in hand, decide whether the gadget binds and whether this
Mac could ever have seen it.

## The packing was the 4-5 s signal; the fixed ~79 s return is a second, different signal

`getvar all` at the next fastboot window (read-only, as asked):

    current-slot:a   slot-retry-count:a:2   slot-unbootable:a:no   slot-successful:a:no
    version-bootloader:b1c1-0.4-7617406   max-download-size:0x10000000   secure-boot:PRODUCTION

So the "slot A flagged unbootable -> every image lands in fastboot" reading is
**refuted by measurement**: the slot is bootable, retry count is not exhausted.

Measured return times, same initramfs, same kernel bytes, packing as noted:

| packing | kernel | probe | return |
|---|---|---|---|
| v2 (`--header_version 2` in the page_size field, sections padded to 4096) | 7.3, 7.1-fork, pmOS-config, bare rc6, no-USB | 8/20/40 s, none | **4-5 s, flat** |
| v0 (mirrored distro layout) | distro kernel bytes | 45 s | **78 s** |
| v0 | distro kernel bytes | 300 s | **79 s** |

Two clean separations fall out:

1. **The 4-5 s return is a property of OUR v2 packing**, not of the kernel: with
   the layout mirrored from the known-good image, the same kernel bytes stay up
   ~80 s instead of 4-5 s. `reboot bootloader`/panic also now demonstrably works
   (ABOOT returns on command), which every earlier "the probe is unobservable"
   note had to leave open.
2. **The ~79 s return does NOT track the probe** (45 s -> 78 s, 300 s -> 79 s) and
   cannot be the probe's `panic=10` path either (that would give ~55 s and ~310 s).
   It is a fixed timer. **Hypothese, nicht Befund:** the SoC's boot-enabled
   watchdog, started by ABOOT and never taken over. Supporting evidence, not
   proof: both the distro config and our builds carry
   `CONFIG_WATCHDOG=y`, `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`,
   `CONFIG_WATCHDOG_OPEN_TIMEOUT=0`, the DTB has
   `compatible = "qcom,apss-wdt-sdm845", "qcom,kpss-wdt"` at `watchdog@17980000`,
   and our init ships no watchdog feeder (no `WATCHDOG_QCOM` in either build,
   no feeder process). The known-good distro image boots through it — whether it
   feeds the timer or never arms it is **not yet measured**, and the distro
   package's own config fragment lists no Qualcomm watchdog driver at all, so
   the mechanism may be ABOOT-side rather than driver-side.

## USB truth from the reference ramdisk (read byte by byte, 2026-10-28)

`init_functions.sh` ships **two** gadget paths:
`setup_usb_network_android()` runs only when `/sys/class/android_usb/android0`
exists — the out-of-tree android_usb driver, which the 6.11/7.x kernels no longer
have (grep over the reference kernel section finds zero `android_usb` strings) —
and `setup_usb_network_configfs()` which mounts configfs at
`/sys/kernel/config` (the distro's `CONFIGFS` constant) and writes
`idVendor`/`idProduct`, `strings/0x409`, `functions/ncm.usb0` (fallback
`rndis.usb0`), `configs/c.1` + symlink, then `echo $(ls /sys/class/udc | head -1) > UDC`.
No `os_desc`, no extra per-function attributes — structurally the same configfs
sequence our init runs at `/config`, so our gadget recipe is not missing a knob.

Decisive corollary, measured twice: **the known-good distro image shows no NCM
and no `172.16.42.1` on the host either**, while the user watches it boot to a
login on the panel. Every past "no NCM => dead" verdict — including the whole
`alive2` run — was therefore weak evidence, not a measurement of liveness. The
readable channel in this state is the **panel** (`console=tty0`), which the
`nowatchdog` build confirmed: with the timer suppressed the user reads kernel
log lines, including our own `Omarchy Mobile first-light` banner, on a device
that never enumerates USB. Panel reading is now the primary oracle; a UART
adapter stays on the shopping list as the channel that survives a kernel hang.

The reference cmdline, read verbatim from the image:

    quiet splash plymouth.ignore-serial-consoles plymouth.prefer-fbcon console=ttyMSM0,115200 pmos_boot_uuid=… pmos_root_uuid=… pmos_rootfsopts=defaults

It contains no watchdog or USB knob at all, so whatever keeps the reference
alive past 80 s is not a cmdline switch — which is what makes the next two
measurements worth their flash time.

## The fixed ~79 s timer is the watchdog: feeding it in PID 1 survives (measured)

| build | what changed | outcome |
|---|---|---|
| v0c | v0 packing, distro kernel, our init, probe 300 s | FASTBOOT at **79 s** |
| v0e | same + `nowatchdog noreboot.not` on the cmdline, probe 300 s | FASTBOOT at **71 s**, and the panel showed **kernel log lines** (user read them) — so the kernel proper runs and prints |
| v0g | same cmdline + **watchdog feeder in PID 1** (`echo V > /dev/watchdogN` every second) + a panel status block every 20 s, probe off | **no FASTBOOT return in 361 s** — the observation window simply ran out |

**Correction, same evening, from the panel (user's eyes):** the v0g screen shows
the boot banner several times, a framebuffer warning, a filesystem error line and
a **call trace** — i.e. the kernel oopsed inside our init path and then *halted*,
which is what a panic without `panic=` does. That reading explains the timer table
without a watchdog at all: v0c and v0e carried `panic=10` on the cmdline, so an
oops at ~69 s / ~61 s became a warm reboot into FASTBOOT at 79 s / 71 s; v0g was
built without `panic=` (see its cmdline) and therefore stayed on the trace
instead of returning. The feeder was never the variable — the two builds differ
in **two** things (feeder added, `panic=` removed), so "feeding it survives" was
a two-variable comparison read as one. The watchdog reading is hereby demoted to
unproven; `# CONFIG_WATCHDOG_QCOM is not set` in the distro config fragment
(checked: only `# CONFIG_KPSS_XCC is not set` matches there) makes it weaker
still: no driver, no `/dev/watchdogN`, nothing to feed.

`nowatchdog` on the cmdline does not save it (71 s), feeding from userspace does
(361 s and counting). Read together: the boot-enabled watchdog the bootloader
leaves running keeps firing, the kernel's own
`CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y` plus `OPEN_TIMEOUT=0` means nothing
takes it over until userspace opens the device, and our init never did. That
is the whole of the ~79 s class of failure — a watchdog reset, not a hang —
and the recipe consequence is a feeder process that outlives every step: the
build's init must open the watchdog node as its first action, before mounts,
before the gadget, before anything that can block.

`v0f` is a cautionary note in the same table: its first attempt packed a
silently broken initramfs, because macOS `bsdtar` cannot create device nodes as
an unprivileged user — it prints `Can't create 'dev/console': Operation not
permitted`, exits 1, and the pipeline's `gzip` still produces a valid archive of
what it managed to write (5 entries instead of 731). The 57 s return of that
build measured a crippled ramdisk, not the feeder. The ramdisk rebuild now goes
through `firstlight/newc.py`, a pure-Python newc rewriter that keeps every entry
byte-exact, writes device nodes with their rdev, and reads its own output back
to prove the replacement landed (`tests/newc-roundtrip`).

## Panel reading of the v0g run, and what the Tux count implies

What the user's eyes reported from the v0g screen (no photo yet, so this is a
witness account, not a capture): the boot banner repeated **eight times**, one
framebuffer warning line, one filesystem error line, and a **call trace**.

The count is itself a measurement. A warm reset neither clears the panel
framebuffer nor the log, so every boot that reaches fbcon paints one more Tux
over the last one. Eight Tuxes after roughly 23 minutes of observation
(`v0g` flashed 21:21, watcher ended 21:36, panel read ~21:44) means about
**2-3 minutes per cycle**, not the 79 s of the v0c/v0e return. So there are at
least two different timers in play, and this is the part of the picture the
fastboot-return timestamps alone could not show:

| timer | evidence | period |
|---|---|---|
| kernel `panic=N` reboot | v0c (79 s), v0e (71 s) with a 45/300 s probe that never fired | panic=10, so the oops is at ~69/61 s |
| a reset nobody in userspace asked for | v0g (no `panic=` on its cmdline, feeder present) — eight Tuxes in ~23 min | ~170 s, which is in the range a Qualcomm watchdog takes over after ABOOT leaves it armed |

Both readings share one cause and it is not the packing any more: **the kernel
reaches our init, prints, and oopses somewhere in it.** The packing question is
closed (the same kernel bytes boot to a login with the distro's own initramfs).
What the fix has to answer is which of our init's steps the trace sits under,
and the instrument that can say so without a UART is already flashed: the panel
shows the last `omamobile-blueline: <step>` line before the trace, and v0h
mirrors `/sys/fs/pstore` (ramoops) so the *previous* boot's tail comes back even
after a reset.

Hypothesis, not finding, to be killed or kept by the v0h panel: the trace is
under the USB gadget bind (`mark 'binding UDC …'` last). v0h builds with
`/etc/omamobile-nogadget`, so if it boots past 5 min with the gadget off, the
bind path is the oops site and the remaining fix is the dwc3 story already
documented above; if it still oopses, the gadget is exonerated for good and the
framebuffer/filesystem lines are the lead.

## The panel is a one-shot log; a ramoops field in the DTB makes it repeatable

Two things read out of the shipped device tree and kernel, both checked rather
than assumed:

- The distro's `blueline.dtb` has **no ramoops region**. Its `reserved-memory`
  holds hyp-mem, xbl-mem, aop-mem, aop-cmd-db, smem, tz, qseecom, camera-mem,
  ipa-fw, ipa-gsi, gpu, adsp, wlan-msa, splash, memory, venus, cdsp-mem, mba,
  slpi, spss and rmtfs — none named ramoops, and the string `ramoops` does not
  occur in the 111,641-byte DTB. So `mount -t pstore` succeeds and
  `/sys/fs/pstore` is **empty**: a warm reset loses the crash text, and every
  "read the panel now or lose it" cycle costs a human.
- The kernel *does* carry the code: 56 occurrences of `ramoops` and 104 of
  `pstore` in the decompressed kernel stream, plus 15 of `qcom_wdt` — which
  also corrects a line above: the Qualcomm watchdog driver **is** in this
  kernel, so "no driver, nothing to feed" was wrong, and the ~79 s timer is
  back to being a live candidate.

`v0i` therefore ships the same image with one byte-level change: a
`ramoops@9f800000` child at the end of `reserved-memory` — 1 MiB, `no-map`,
`record-size` 64 KiB, `console-size` 512 KiB, `pmsg-size` 256 KiB. Chosen
because the splash region ends at `0x9f800000` and paints only
1080·2160·4 = 0x8e1000 bytes from `0x9d400000`, so the log area sits far outside
what the bootloader overwrites at the *next* boot, and no other child claims it.
Built with `dtc -I dtb -O dts` + recompile; `dtc` refuses a property after a
subnode, so the insert goes before the parent's closing brace, not after its
opening one.

Verified before flashing (`unpack-bootimg.py` plus a byte comparison, not a
header trust): gzip stream 16,042,611 B unchanged, DTB behind it 111,812 B, the
two sum to `kernel_size` 16,154,423 with zero slack, `page_size@40` still 0, the
DTB inside the image byte-identical to the built one and containing the
`ramoops` string, the ramdisk **byte-identical to v0h's** — so v0h and v0i
differ in exactly one thing, the device tree. v0h was not flashed: v0i answers
the same question (gadget off) and adds the crash log, so it replaces that
cycle rather than adding one.

With `panic=60` the return time becomes a measurement of the crash time: an
oops at T sends the handset back to FASTBOOT at T+60, so a comeback at e.g.
125 s means the panic sat at ~65 s. And once anything panics, the *next* boot of
the same image prints the previous boot's last 512 KiB of console onto the
panel by itself — one photo per crash, no button dance in the middle.

Arbiter under measurement (flashed while this was written): the same v0 image
with `nowatchdog noreboot.not` appended to the cmdline. Survives > 120 s => the
fixed timer is the watchdog and the fix belongs in the recipe (a feeder in init,
or the knob in the cmdline); returns at 79 s anyway => the timer is not the
watchdog core and the panel/pstore channels have to say what it is.


### Anatomy of the reference image (measured byte by byte, 2026-10-28)

Read out of `ed2c225f…` itself, not out of a header's own claim:

| byte offset | content |
|---|---|
| 0..8 | `ANDROID!` |
| 8, 12 | `kernel_size` 16,154,252 / `kernel_addr` **0x8000** |
| 16, 20 | `ramdisk_size` 12,569,303 / `ramdisk_addr` 0x1000000 |
| 32, 36 | `tags_size` 256 / `tags_addr` 0x1000 |
| 40 | `page_size` = **0** |
| 44 | 0 |
| 48 | `name` — all zero |
| 64 | `cmdline` (218 Zeichen, v0-Layout) |
| 576 / 608 | sha1 id / `extra_cmdline` (leer) |
| 4096 | gzip-Strom, **16,042,611 B komprimiert -> 44,498,944 B entpackt** |
| 16,046,707 | `d00dfeed` DTB, 111,641 B -> Strom + DTB = 16,154,252 = `kernel_size`, **0 Bytes Rest** |
| 16,158,348 | ramdisk, ohne jede Seiten-Auffuellung, **kein Kompressions-Magic** am Anfang |
| 28,727,651.. | 1,693 B Schweif, Datei endet auf einer 2048er-Grenze |

Beweis, woher unsere 2 an Offset 40 stammt (Nachbau 2026-10-28, Fixture durch
`android-mainline/mkbootimg/mkbootimg.py`): dieses Werkzeug schreibt
`--header_version 2` **an Offset 40** und die cmdline **an 64**, also nach dem
alten Kopf-Layout ohne header_version-Feld. Nach dem AOSP-Kopf, den ABOOT liest,
steht an 40 die Seitengroesse. Unsere Datei polsterte dabei auf das `--pagesize
4096`, das wir mitgegeben hatten — Feld (2) und Datei (4096) describing two
different page sizes, and the known-good image carries 0 in that field with
sections that are not padded at all.

**Was davon Hypothese ist:** dass genau dieses Feld den 4-5-s-Rueckprung
verursacht. Das geflashte v0a-Bild aendert zwei Dinge gegenueber der Referenz —
Feldwert/Padding *und* das Initramfs —, also zeigt erst sein Ergebnis, ob die
Feldtheorie stimmt. Ein BOOT-Image-Kopf ist ein Vertrag ueber Offsets; welches
Feld ABOOT wirklich liest, ist hier nicht dokumentiert, nur aus dem
bekannt-guten Bild ablesbar.

Three consequences that change earlier readings:

- **`append_dtb` is proven**, byte-exact: the gzip stream ends at +16,042,611
  and the DTB fills the rest of `kernel_size`. That is the pmaports recipe.
- The sections carry **no page alignment at all**. A bootloader that follows
  `page_size` therefore cannot be aligning anything either — with the field at
  0 the distro's own packer puts the ramdisk directly behind the kernel, and
  our `pack-v0.py` mirrors that. Our old v2 images instead padded each section
  to 4096 **while writing 2 into the `page_size` field**: two independent
  reasons for ABOOT to look somewhere the file has nothing.
- The distro's **ramdisk has no gzip/cpio magic at its first byte** (372 zero
  bytes first). A loader that sniffs compression instead of trusting the header
  would reject it — a reminder that this format is read by size, not by magic.

`tools/`-Gegenstueck im Repo: `firstlight/unpack-bootimg.py` (vermisst den Strom
statt dem Kopf zu glauben) und `tests/bootimg-v0` (in `tests/all`), das alle vier
Fehlerklassen verweigert: header_version an der page_size-Stelle, Abweichung gegen
ein Referenzbild, gepolsterte Sektionen, abgeschnittener Kernel-Strom.
Verifikation am echten Referenzbild (Ad-hoc, 20 Pruefungen): Rueckpacken liefert
kernel- und ramdisk-Sektion **byte-identisch**, Kopf-Unterschiede nur in den 20
ID-Bytes und im Schweif. Suite: **103 ok, 0 not ok, 2 skip** (Alpine-Container mit
`perl`, GNU `tar`, `gcc`/`musl-dev`; mit busybox-tar scheitert
`tests/phone-provision` an `--owner=`, ohne perl `tests/kernel-pr-check` — das ist
die Umgebung, nicht der Code).

## What first light does not claim

Wi-Fi (WCN3990 needs the `Google_blueline` calibration from the owner's
firmware and `rmtfs` served read-only), Bluetooth (the BD-address note
above), modem and calls (the X20 comes up through PIL/QMI; calls are
weeks after data, like every device here), audio (WCD9340 codec), the
panel driver behind the simplefb console (DPMS is the display plan's
job), touch (upstream's DTS has **no touch node yet** — the FocalTech at
i2c2-0x49 is the bring-up's first real device-tree job after first
light), sensors, GNSS (it lives in the modem), cameras, fingerprint (rear
sensor, no upstream driver this kernel drives), suspend. First light is:
slot B, our kernel, the guard, SSH over USB, our root on `userdata`.

## Why this phone is worth the GPT risk

SDM845 is the mainline-est phone SoC in this tree, and the Pixel 3 is its
cheapest complete body: GPU (A630), display, USB, storage, remoteproc and
the QMI modem path all run upstream on dragonboard-class boards today.
The field notes cited above report a mainline Pixel 3 that makes and
receives real calls — the milestone the Pixel 7 Pro's own plan is weeks
to months from, on hardware where the modem is a Google S5300 over PCIe
with no field-proven path yet. On blueline the plan's whole risky asset
is one GPT write; everything after M1.6 is the same road cheetah took.

## 2026-10-29 00:26 — zweite root cause: der ramdisk-Offset (v0j, erster Boot bis /init)

Das Foto von 22:14 (v0g auf dem Panel): `Kernel panic - not syncing: VFS:
Unable to mount root fs on unknown-block(0,0)`, PID 1 `swapper/0`, Call trace
über `mount_bdev` → `mount_root` → `kernel_init_freeable`. Das heißt: **unser
/init ist nie gelaufen** — den Kernel erreichte kein lesbares Initramfs, er
fiel auf `mount_root` zurück. Kein Fehler in unserem Init, kein Watchdog.

Messung (offline, byte-genau, am Referenzbild ed2c225f... und an v0h):

| Grösse | Referenz | unsere Bilder v0a–v0i |
|---|---|---|
| kernel_size | 16154252 | identisch (derselbe Kernel) |
| Kernel-Sektion endet bei | 16158348 | identisch |
| ramdisk liegt bei | **16158720** = nächste 4096er-Seitengrenze, 372 Nullbytes Füllung davor | 16158348 = **372 Bytes zu früh** (Spiegel-Modus: Sektionen byte-auf-byte) |
| ramdisk-Magic dort | zstd (die Distro packt zstd) | gzip |

ABOOT rechnet den ramdisk-Offset aus kernel_size und Seitengrösse und
übergibt den Blob ab der Seitengrenze. Ohne Auffüllung bekam der Kernel
einen Ausschnitt, der 372 Bytes mitten im gzip-Strom begann:
`Initramfs unpacking failed`, kein /init, Panic. An der Ramdisk selbst lag
es nie: `cpio-ls.py` (neu, läuft die Einträge exakt wie der Kernel) zählt
in unserer Ramdisk 731 Einträge, `init` 0755/13350 B im Archivgrund,
TRAILER byte-genau am Ende; im Referenzbild 366 Einträge, `init`
0755/2093 B.

Alle bisherigen „Comeback"-Messungen waren derselbe Panic: Panic bei ~8 s;
mit `panic=10` war ABOOT nach den Slot-Retries bei ~71–79 s in fastboot
(v0a/v0c/v0e); ohne `panic=` hielt der Kernel an und das Panel behielt den
Trace (v0g → Foto); mit `panic=60` passte v0hs 229 s exakt auf
3 × (Boot ~8 s + 60 s Panic-Warten) + ABOOT.

Fix: Sektionen auf die Seitengrenze mit Nullbytes auffüllen — jetzt
Standard in `pack-v0.py` (Alter Modus: `--no-pad-sections`). Der Reader
erkennt seitenbündige Lage (auch zstd) und verwirft eine ramdisk mitten in
der Seite mit Exit 1; `tests/bootimg-v0` prüft beide Klassen (5 ok,
Arch-Alpine-Container, Exit 0).

Messung: v0j = Kernel und Ramdisk byte-identisch zu v0h, cmdline nur um
`rdinit=/init` ergänzt, Packing seitenbündig (sha256
5ee02f4c975e221ed76f166da012d6753fceba72a6b658702cd8acb4deb5998e,
20922368 B) auf boot_a, `fastboot reboot` 00:26:14 → **408 s kein
Fastboot-Comeback** (v0h kam bei 229 s wieder). ACM: keins (Gadget
abgeschaltet, Panel ist der einzige Leser).

Nachlese: der Packer prüft die Lage jetzt selbst nach dem Schreiben
(`ramdisk-Magic (gzip) liegt auf der Seitengrenze 16158720`) und liest dafür
die ganze Datei — die erste Nachprüfung las nur die Kopfseite und meldete bei
seitenbündigen Bildern selbst „mitten in der Seite" (die Ad-hoc-Verifikation
2026-10-29 fand genau das, zuerst rot). Neugepackt mit dem finalen Packer:
**byte-identisch zum geflashten v0j** (cmp, sha256 5ee02f4c…). Ad-hoc-
Verifikation `hermes-verify-seclay.py`: 11 Prüfpunkte grün, Exit 0.
`tests/bootimg-v0` 5 ok / Exit 0 und `tests/newc-roundtrip` Exit 0 im
Alpine-arm64-Container; `tests/all` im Arch-Container läuft noch nach.

## 2026-10-29 01:4x — v0l: Sonde, Gadget-Lage und Statusblock nach dem Check-in

Zwei Schlusskorrekturen aus dem Check-in, beide angenommen:

1. **"408 s kein Comeback = /init läuft" ist kein Beleg** — dieselbe Klasse
   Stille wie alive2. Und **"ABOOT ehrt `reboot bootloader`" war
   unbelegt**: v0as Comeback bei 78 s war der VFS-Panic mit `panic=10`,
   nie eine Sonde. Neuer Stand: v0k trug (Baufehler, unten) die Sonde bei
   300 s; das Beobachtungsfenster endete um 304 s mit `fastboot=0`, und als
   wir zurückkamen, **stand das Telefon in FASTBOOT** — zeitlich genau das
   Feuern der 300-s-Sonde + `reboot bootloader` (~310 s, sechs Sekunden
   nach Fensterende). Einzelbeobachtung, nicht Messung: v0l misst es mit
   Sonde 90 s in einem 240-s-Fenster sauber nach.
2. **Ramoops-Überlappung, nachgemessen** (`check-ramoops.py`, alle
   reserved-memory-Kinder des Distro-DTB, 21 Bereiche): der Kandidat
   0x9f800000..0x9f900000 berührt nur die untere Grenze des
   36-MiB-Carveouts 0x9d400000..0x9f800000 (splash) und überlappt nichts;
   der nächste Carveout beginnt bei 0xf2700000, dazwischen 1327 MiB frei.

**Baufehler v0k, dokumentiert:** der erste Pack-Durchlauf lief ohne
`-v …/ref:/ref` und brach nach dem Ramdisk-Umbau im Packer ab; das danach
gepackte und geflashte Bild trug wieder `300` statt `120` (im fertigen
Bild nachgelesen: `Sonden-Sekunden im laufenden Bild: b'300'`). Lehre:
`pack-v0.py`-Ausgabe und Sondeninhalt werden jetzt *aus dem fertigen Bild*
gegengelesen, nicht aus der Baubeschreibung. (Zusätzlich: `set -eo
pipefail` — `python3 … | tail -2` verschluckte den Packer-Abbruch.)

**v0l = v0k-Kernel (ramoops-DTB) + Init mit drei Änderungen:**

* Gadgetbaum an dem Ort und mit dem Namen der Distro-Referenz:
  `/sys/kernel/config/usb_gadget/g1`, idVendor/idProduct 0x18D1/0xD001,
  und Binden exakt wie `setup_usb_configfs_udc`: erst `echo "" > UDC`
  wenn eines gebunden steht, dann die UDC schreiben.
* Der Statusblock (alle 20 s aufs Panel) trägt, was ein einzelnes Foto
  über USB entscheiden lassen soll: Uptime, `comm`/`state`/Kinderzahl von
  PID 1, `ls /sys/class/udc` **und** der Inhalt von `g1/UDC`,
  Rolle/Modus jedes `*dwc3*`-Plattformgeräts, Typec-Zustand und VBUS,
  Watchdog-Status, letzter Schritt.
* Sonde auf **90 s**; danach bleibt die Kette `reboot bootloader` →
  `fastboot` → `recovery` → sysrq-crash. Mit `panic=60` heißt ein
  Foto: Fastboot-Comeback bei ~100 s = Sonde + ABOOT bewiesen; sonst
  steht die Crash-Spur fürs Foto auf dem Panel.

Bild: sha256 265c492077b476d5172c983968cdd9afbe268d32028e70a5b8c88edffe086411,
20922368 B, Ramdisk seitenbündig ab 16158720, Schalter und Sondeninhalt aus
dem fertigen Bild vorgelesen. Flash auf boot_a läuft; die Messung steht in
`/private/tmp/fl-v0l/ERGEBNIS.txt`.

## 2026-10-29 02:49 — Zeitfenster-Rechnung: v0ls Init erreicht die 90-s-Sonde

ABOOT-Zählung als Nebenoracle: `--set-active=a` setzt slot-retry-count:a auf
3 und löscht slot-unbootable (um 02:40 gemessen: `retry:a 3, unbootable:no`).
[Korrigiert am 10:48 desselben Tages, siehe Abschnitt 09:31: Die Zuschreibung
an `--set-active=a` steht in keiner erhaltenen Datei, und der gelöschte
unbootable-Flag ist unbelegt — in jedem Log, das diese Nacht überlebt hat, war
der Flag schon `no` (`fl-v0a/getvar-all.txt` vom 28.10.: `retry:a:2,
unbootable:a:no`; `fl-v0q/ERGEBNIS.txt` vor dem Flash am 29.10.: ebenso `no`;
10:48 gelesen: ebenso). Ein einzelnes `yes, retry:a:0` aus der Sitzung um 03:06
existiert nur im Gespräch, nicht in einer Datei. Der Anstieg 2 -> 3 ist seit
dem 09:31-Fenster erstmals sauber isoliert: dort lag zwischen den beiden
Lesungen **nur** ein `fastboot flash boot_a`, ohne `--set-active` und ohne
erfolgreichen Boot — eine Stichprobe, als Regel noch nicht brauchbar. Die
Zeitfenster-Rechnung unten hängt nicht an der Zuschreibung und bleibt gültig.]
Danach v0l (Sonde 90 s, Notnagel sysrq-crash, `panic=60`) gebootet und der
Host hat das Fastboot-Menü auf die Sekunde passend zum Sonden-Zyklus
gesehen:

| Hypothese | erwarteter Fastboot-Auftritt | beobachtet |
|---|---|---|
| Init lebt, Sonde feuert bei 90 s, Kette endet am sysrq-crash, ABOOT gibt nach 3 Fehlschlägen auf (Boot ~10 s + 90 s + 60 s panic-Warten + ~15 s ABOOT ≈ 175 s/Zyklus) | 02:40:09 + 3×175 s ≈ **02:48:54** | zwischen 02:48:23 (noch 0) und **02:49:15 (da)** ✓ |
| Init hängt im UDC-Bind (~t+12 s), Firmware-Watchdog beisst ~70–80 s, 3 Zyklen | ≈ **02:44:0x** (und 02:41–02:45 waren sechs Polls mit fastboot=0) | ✗ |

Das ist die erste tragfähige Aussage seit dem Packing-Fix: **unser Init läuft
nach dem seitenbündigen Packing über 90 s hinaus** — also auch durch den
Gadget-Bind an der Referenz-Position `g1` durch (der dwc3-Bind tötet den Boot
nicht, der alte Bisect-Verdacht ist damit vom Tisch), und `busybox reboot`
machte die ganze Nacht über Warmboots ohne Grund: busybox ruft
`reboot(..., LINUX_REBOOT_CMD_RESTART, NULL)` — das Wort `bootloader` erreichte
den Kernel nie. Dazu passt der DTB-Befund: **im Distro-DTB gibt es keinen
poweroff-/pon-/restart-Knoten**, es registriert also gar kein Treiber einen
restart-Handler mit Grund auf diesem Kernel — pmOS selbst nutzt diesen Pfad
nicht. v0m misst mit einem 162-KiB-Standalone (`restart2.c`, direkter
`SYS_reboot` mit RESTART2-Kommando, Konstanten hartkodiert, da musl kein
`linux/reboot.h` hat) den ehrlichen Fall: Fastboot-Auftritt bei ~155 s =
ABOOT ehrt den Grund trotz fehlendem Knoten (PSCI-Reset schreibt ABOOTs eige-
nes SCR-Feld); Auftritt bei ~440 s = Grund ignoriert, wieder nur die
Erschöpfung nach drei Zyklen. Panelfotos (Statusblock jetzt mit PID-1-Status,
UDC-Bindung, dwc3-Rolle) lesen die Zwischenschritte.

## 2026-10-29 03:2x — v0ms restart2 war nie im Bild: der TRAILER-Falle

Nachlese zum v0m-Bild (Sonde 150, Kette auf `/bin/restart2 bootloader`
umgestellt): das fertige Bild hat **731 Einträge, `bin/restart2` keins** —
der Init rief eine Datei, die das Archiv nicht enthielt. Die
Baustellen-Meldung „Archiv umgebaut: restart2 (162336 B)" war eine Lüge,
die der Code sich selbst erzählte: `newc.read_cpio` liefert den
`TRAILER!!!` als **letzten** Eintrag und `emit` schreibt, was die Liste
hergibt — ein `es.append(tool)` landet hinter dem TRAILER, wird beim
Rücklesen nie erreicht, und die Größen-Ketten (`wc -c`, gzip-Länge)
stimmen trotzdem, weil das Wort „bin/restart2" als String im Init steht.
Der 900-s-Lauf von v0m (kein Fastboot, `panic=120` = 150 s + 120 s pro
Zyklus) war damit ein normaler, ruhender Boot — keine RESTART2-Messung.

`emit` wirft jetzt, wenn der TRAILER nicht der letzte Eintrag ist
(Falle im Code benannt, nicht nur im Log). v0n setzt die Datei **vor**
den TRAILER und liest das **fertige Bild** gegen: `restart2 162336 B
(0755) direkt vor TRAILER, keine Sonde, panic=60` — sha256
c188f20ed09b6f175d79a151e6ac7391ef862265004ec3e83d975e4503ebd770,
20963328 B, Watchdog wieder **an** (kein `nowatchdog`).

Messung v0n: der Init ruft `restart2 bootloader` **sofort** (ohne Sonde).
Erscheint das Fastboot-Menü beim Host binnen ~60 s, ehrt ABOOT RESTART2
trotz fehlendem poweroff-Knoten im DTB (PSCI-Reset-Schleife schreibt ABOOTs
SCR-Feld selbst); sonst ist der Grund tote Hose und das Panel zeigt
Watchdog-Neustakte. Flash auf boot_a, `--set-active=a` (retry 3) läuft.

## 2026-10-29 03:2x — Zwei selbstgebaute Blindheiten: no-gadget und RESTART2

**RESTART2 gemessen (v0m/v0n).** v0ms `restart2` war nie im Bild (TRAILER-
Falle, Abschnitt davor). v0n — Datei vor dem TRAILER, aus dem **fertigen**
Bild gegenlesen (`restart2 162336 B (0755) an Position 731/732`) — rief
`restart2 bootloader` **sofort** beim Init-Start, Watchdog an, `panic=60`.
Ergebnis: **600 s kein Fastboot-Comeback** und in dem Fenster **keine
einzige USB-Enumeration** am Host. Der RESTART2-Grund `"bootloader"` läuft
ins Leere: ohne `poweroff`-Knoten im DTB (PSCI-Reset) schreibt kein
SCR-Feld, ABOOT sieht einen ganz normalen Neustart. Panel zeigt also einen
Neustakt-Zyklus, kein Menü — photo-confirm steht aus.

**Warum NCM je dunkel war: Zeile 36.** Der v0h-Instrumentierungs-Build
hatte `touch /etc/omamobile-nogadget` in den Init geschrieben (Zeile 36),
und der Gadget-Block läuft hinter `if [ ! -e /etc/omamobile-nogadget ]`
(Zeile 134). **Jeder** Build danach — v0h, i, j, k, l, m, n — lief mit
Gadget-Bindung **AUS**, auch nachdem der Init längst bis zum Gadget lebte.
Der Host sah nie ein `172.16.42.1`, weil wir es selbst abgeschaltet hatten,
nicht weil das Phone es nicht konnte. Lehrstück: ein Instrumentierungs-
Schalter, der in nachfolgende Inits kopiert wird, überlebt den Grund, warum er
 gesetzt wurde, und hält die folgenden Builds blind.

**v0o** (sha256 049345f7…, 20963328 B) schaltet den Schalter aus (touch
gelöscht, Guard bleibt), stellt den restart2-Zweig auf *bleiben* um und
misst als erstes echtes First Light: Host-Poll alle 4 s auf
`ifconfig`-`172.16.42`-Interface, USB-Enumeration, Fastboot. Erstmals seit
v0d (ACM) wieder ein aktives Gadget im Boot. Baurezept:
`device/blueline/firstlight/build-v0o.sh`.

## 2026-10-29 03:4x — v0p: die Gadget-Sequenz der Referenz, wortgetreu

Der Check-in hieß, `setup_usb_network_configfs` **1:1 zu übernehmen statt neu
zu erfinden**. Nachgemessen am Wortlaut (`pmos-ref-build/pminit/root/
init_functions.sh`, Zeilen 12, 831, 816, 967) und gegen das geflashte Bild
unterschied sich unsere Sequenz in drei Punkten — jeder allein genug, damit am
Host kein NCM-Interface auftaucht:

| | Referenz | unser Stand bis v0o |
|---|---|---|
| configfs-Hang | `mount -t configfs -o nodev,noexec,nosuid configfs "$(dirname $CONFIGFS)"` → `/sys/kernel/config` | `mount -t configfs configfs /config` |
| Gadgetname | `g1` | `omamobile` |
| VID/PID | `0x18D1` / `0xD001` | `0x1d6b` / `0x0104` |
| Binden | erst `echo "" > g1/UDC` (im Quelltext gegen *write error: Resource busy*), dann den Controller | Controller direkt, alles nach `2>/dev/null` |

**Korrektur einer eigenen Falschaussage:** der v0l-Abschnitt oben (und Commit
`a722889`) behauptet, das Gadget sei auf `g1`/`0x18D1` mit UDC-clear umgezogen.
Das geflashte Bild sagt etwas anderes — aus `fl-v0l/firstlight.img`
vorgelesen: `g=/config/usb_gadget/omamobile`, `echo 0x1d6b`, `echo 0x0104`,
kein Leeren des UDC. Beschrieben und committet war die Änderung, gebaut nie.
Dieselbe Klasse wie die TRAILER-Falle: der Baustein erzählt sich selbst, was
er tut, und das Bild weiß es nicht.

**v0p** (sha256 `5b285a6ba13505a03cff1af7a13515cab7e143f4baa513e079cdb19a458d677e`,
20963328 B) legt den Block deshalb als Datei im Repo ab —
`firstlight/gadget-reference.sh` — und baut ihn unverändert ein; die
Nachprüfung verlangt den **Block als Ganzes** im fertigen Bild, nicht ein
paar Einzelzeichen. Dazu `firstlight/panel-status.sh`, vier Zeilen, die ein
Foto allein entscheiden lassen: Uptime und Watchdog, `ls /sys/class/udc` plus
der Inhalt von `g1/UDC`, `dwc3`-Rolle/Typec/VBUS, `pid1`-`comm`/`state`/
Kinderzahl, letzter Schritt. Paneltext wird zwanghaft ASCII geprüft
(`t.isascii()`), ein UTF-8-Gedankenstrich ist auf dem Panel Müll.

Kompression braucht kein `modprobe`: `USB_LIBCOMPOSITE`, `USB_CONFIGFS*`,
`USB_F_NCM`, `USB_F_ACM`, `USB_DWC3*` stehen im Kernel auf `=y`, und das
Ramdisk hat keine einzige `.ko` — die Referenz modprobt nur sicherheitshalber.

**Und noch eine selbstgemachte Versehrtheit, von den neuen Tests gefangen:**
`gadget-reference.sh` trug in allen drei Bauten, die es gab, auf **jeder**
Zeile eine `ZEILE|`-Ziffernfolge voran — der Datei-Rückgabewert eines
Lese-Werkzeugs war mit seinen eigenen Zeilennummern zurückgeschrieben worden. Der
Wortgenau-Vergleich im Bau fand den Block trotzdem, weil er denselben
Rückgabewert einsetzte; nur der Shell-Init im Bild war verstümmelt (aus ZEILE
12 wäre eine Pipeline in ein Kommando `12` geworden). `tests/gadget-reference`
verankert die Referenz-Zeilen mit `^CONFIGFS=` und Zeilenanfang-`grep -qF` —
ein praefixierter Block fällt daran sofort auf, der Wortgenau-Vergleich fiel
nie auf.

`read_cpio` prüft jetzt auch die **Leseseite** der Falle: Daten hinter dem
`TRAILER!!!`, die kein Leser sieht — bei v0m 184 Bytes — lassen das Öffnen
scheitern statt stille Bestände zu versprechen (`emit()` wirft beim Schreiben
seit `1147869`). Neu `tests/gadget-reference`, in `tests/all` eingehängt:
Referenzzeilen mit Zeilenanfang-Anker (`^CONFIGFS=` — ein praefixierter Block
fällt durch), Reihenfolge Netzwerk vor ACM und UDC leeren vor UDC binden,
Panelblock-Vollständigkeit, ASCII-Zwang und ein End-to-End-Durchsatz
`emit → gzip → pack-v0 → Rücklesen` durch die eigene Kette. Kanonische
Arch-Tonne: `tests/gadget-reference` Exit 0, `tests/newc-roundtrip` Exit 0,
`tests/bootimg-v0` Exit 0, `tests/all` **121 ok / 0 not ok / Exit 0**. Der
Build nach der Verschärfung liefert byte-identisch dasselbe Bild — die Prüfung
liest unseren eigenen Null-Auffüllrest und lässt ihn gelten.
Ad-hoc-Verifikation gegen das fertige Bild: 24 Prüfpunkte, 0 Fehler
(`hermes-verify-v0p.py`, nach dem Lauf gelöscht). Der Beobachter (`/private/tmp/fl-v0p/run.sh`)
sucht jetzt auch `/dev/cu.usbmodem*`: bindet `acm.GS0`, haben wir eine
Konsole über USB und brauchten für den nächsten Befund gar kein Foto.
Zurück nach Fastboot geht es ohne Funktionstaste nicht — RESTART2 ist hier
ein No-op (Root Cause #3), also Power + Leiser.

## 2026-10-29 04:2x — dritte selbstverschuldete Dunkelheit: die Gadget-Module fehlten

Der Check-in von Claude behauptete, `CONFIG_USB_F_NCM=m` in der Distro-Config
mache unser NCM unmöglich, und unsere Aussage „USB_F_NCM steht auf =y, die
Ramdisk braucht keine .ko" gelte nur für den Selbstbaukernel. Nachgemessen, und
er hat recht — mit einer Verschärfung, die schlimmer ist als sein Befund.

### Beweis, welcher Kernel in unseren v0-Bildern steckt

`kernel-config-from-image.py` versucht den eingebetteten IKCONFIG-Block aus dem
Bild zu lesen (wie `scripts/extract-ikconfig`): **kein IKCONFIG in beiden
Bildern** — die Distro-Config setzt `CONFIG_IKCONFIG=n`. Aus dem Bild alone ist
die Config also nicht beweisbar. Der Blob-Vergleich schon:

| Bild | gzip-Strom des Kernels | sha256 (gekürzt) |
|---|---|---|
| `pmos-ref-build/ref/boot.img` | 16042611 B | `7112decbddcbe235` |
| `fl-v0p/firstlight.img` | 16042611 B | `7112decbddcbe235` |
| DTB-Anhang dahinter | 111641 B vs 111812 B | differs only by ramoops |

Der decompilierte DTB-Unterschied sind 18 Diff-Zeilen: unser `ramoops@9f800000`
plus its `no-map` block — sonst ist der Device Tree identisch, including
`dr_mode = "peripheral"` at `usb_1_dwc3`.

Die Config, die zu diesem Kernel gehört
(`config-postmarketos-qcom-sdm845.aarch64`), setzt:
`CONFIG_MODULES=y`, `USB_LIBCOMPOSITE=m`, `U_ETHER=m`, `U_SERIAL=m`,
`USB_F_NCM=m`, `USB_F_ACM=m`, `USB_F_RNDIS=m`, `USB_CONFIGFS=m`.

`android-mainline/out-blueline-kernel/.config` — die Quelle unseres „ist
eingebaut" — ist ein **anderer Kernel** (ebenda `USB_F_NCM=y`, `USB_F_ACM=y`,
`USB_LIBCOMPOSITE=y`). Wir haben nie mit ihm gebootet.

### Was das bedeutet, und wo es still war

`USB_CONFIGFS=m` heißt: ohne `libcomposite.ko` schlägt schon
`mount -t configfs` fehl. Unser Init tat das mit `2>/dev/null` und markierte
nur „usb_gadget not found in configfs". Die Funktions-Mkdirs themselves ran
without redirection (Zeile 138, 152) — their error went to the kernel log, which
we had no console for and never read. So the sequence was correct and empty.

`dr_mode` als Erklärung ist damit vom Tisch (peripheral in beiden DTBs), and the
missing `TYPEC_*` modules cannot be the difference between the reference (boots
to login) and us: they are absent in both initramfs images, and the reference
gets its peripheral role from the DTB, not from a driver.

**RESTART2 stays unproven, not confirmed.** v0n ran with the same module
darkness *and* the no-gadget switch, so its 600 s of silence separate two
hypotheses no more: either ABOOT ignores the restart reason, or the restart2
call was never reached. The PSCI argument (no `poweroff`/`qcom,pon` node in the
DTB, so nothing writes the ABOOT SCR field) is reasoning from the tree, not a
measurement. Only UART or a panel photo decides.

### v0q: Module rein, und zwar aus der Referenz selbst

`refmodules.py` liest die Schliessung aus `modules.dep` des
**Referenz-Initramfs** (nicht abgeschrieben) und legt sie entpackt nach
`/private/tmp/refmod`:

    libcomposite.ko   149865 B   u_ether.ko   65065 B   u_serial.ko   58993 B
    usb_f_ncm.ko       66241 B   usb_f_acm.ko 38585 B   usb_f_rndis.ko 93009 B

Alle `vermagic=7.1.0-rc1-sdm845 SMP preempt mod_unload aarch64` — derselbe
Kernel, der bootet. `patch-v0q.py` setzt sie unter dem Referenzpfad
`usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb/gadget/…` ein, Modus 0644,
direkt vor `TRAILER!!!`, und schreibt in den Init vor den configfs-Mount:

    MODDIR=/usr/lib/modules/7.1.0-rc1-sdm845/kernel/drivers/usb/gadget
    for m in "$MODDIR/libcomposite.ko" "$MODDIR/function/u_ether.ko" \
             "$MODDIR/function/usb_f_ncm.ko" "$MODDIR/function/u_serial.ko" \
             "$MODDIR/function/usb_f_acm.ko"; do
        if insmod "$m" 2>/dev/null; then mark "modul $(basename "$m") geladen"
        else mark "modul $(basename "$m") FEHLER $?"; fi
    done
    mark "moduli: $(ls /proc/modules | wc -l) geladen, usb_f_ncm $(grep -c usb_f_ncm /proc/modules)"

busybox-insmod ist da (sbin/insmod ist ein Hardlink auf /bin/busybox), kann
kein zstd — deshalb ohne `.zst` — und prüft den vermagic selbst.
Reihenfolge im fertigen Init: insmod (126) → configfs-Mount (145) →
`functions/$netfunc` (161) → `functions/acm.GS0` (175) → UDC-Write (182).

Bild: `/private/tmp/fl-v0q/firstlight.img`, 21094400 B (neu gemessen, 05:44 —
die zuvor notierten 20963328 B waren das v0p-Bild),
sha256 `2911e6f7666299639e0a712604fe3ae0427802f875b319f47146d93826fd3ee1`.
`verify-v0q.py`: 28 Prüfpunkte, 0 Fehler. **Reproduzierbarkeit gemessen 05:44:**
derselbe eingecheckte Umbau in einen leeren Zielordner gebaut (kein
Wiederverwenden des bestehenden Archivs) ergibt bitgleich `2911e6f7…`.

Dabei ist ein dritter Prüfer-Fehler aufgefallen und behoben worden:
`kernel-config-from-image.py` hatte eine sha256-Vorgabe, die **nie erreicht**
wurde — sie stand hinter dem `return None` des IKCONFIG-Frühreturns, und
genau dieses Bild hat kein eingebettetes IKCONFIG. Ein Prüfer, der eine Vorgabe
übersieht, meldet `ok`. Jetzt liegt die Prüfung vor dem Frühreturn, und
`tests/gadget-modules` Schritt 5 verlangt beides: `TREFFER` gegen die wirkliche
sha256 **und** Abbruch gegen eine bewusste Falschangabe.

CI-Messungen im Arch-Container, jeweils frisch: 04:3x — `tests/gadget-modules`
5 ok, `tests/all` 126 ok / 0 not ok / 3 skip. Nach dem Prüfer-Fix, 05:5x —
`tests/gadget-modules` 7 ok / 0 not ok, `tests/all` 128 ok / 0 not ok / 3 skip
(Skips: docker, AOSP mkbootimg, rootfs-Image), `tools/pr-check HEAD~1` Exit 0.

### Vier methodische Funde nebenbei

1. **Heredoc ohne Quotes frisst den Init-Block.** Denselben insmod-Block einmal
   als `<<PY` in ein Shellskript geschrieben: `$m`, `$(basename "$m")` und
   `$?` wurden vom Shell expandiert — `SyntaxError: unterminated
   triple-quoted string`. Baurezepte mit Init-Text gehören in Python-Dateien,
   nicht in Shell-Heredocs.
2. **Byte-Literale mit `bytes.fromhex()` schreiben.** In
   `kernel-blob-from-image.py` stand das gzip-Magic-Literal mit einem
   verdoppelten Backslash im Quelltext; der Vergleich prüfte Text gegen Bytes
   und scheiterte, während derselbe Bytesatz eine Zeile höher korrekt gedruckt
   wurde. `bytes.fromhex("1f8b08")` ist gegen Rückspiel-Unfälle immun.
3. **`make-init-v0l.py` fast selbst vergiftet.** Beim Suchen dieses Escape-Fehlers
   habe ich mit einem Flächen-Ersetzen beinahe das `tr '\\n'/'/'` des
   Statusblocks ruiniert (Zeile 39) — zurück auf HEAD, Diff gelesen, vorher/nachher
   verglichen. Flächen-Umbauten in Datei-Inhalten, die auf ein Telefon gehen,
   brauchen vorab den Diff.
4. **Ein Prüfer mit Blindem Fleck meldet `ok`.** Die sha256-Vorgabe in
   `kernel-config-from-image.py` stand hinter dem `return None` des
   IKCONFIG-Frühreturns — und dieses Bild hat kein eingebettetes IKCONFIG,
   also wurde die Prüfung nie erreicht. Ein Test, der eine Vorgabe übersieht,
   ist wertloser als gar keiner: er bestätigt, was der Prüfer zufällig sieht.
   Deshalb verlangt `tests/gadget-modules` jetzt beide Richtungen — TREFFER
   gegen die wirkliche sha256 und Abbruch gegen eine falsch eingetragene.

## 2026-10-29 06:2x — der Slot-Write braucht eine ausdrueckliche Freigabe

Mein v0q-Runner führte `fastboot --set-active=a` automatisch aus, nachdem ich
auf zwei Fragen keine Antwort bekommen hatte. Das war ein Eigentor: **Schweigen
ist keine Zustimmung**, und ein Slot-Flag ist der eine Write, den hier kein
Datei-Backup zurueckdreht. Der Runner (`firstlight/run.sh`) flasht jetzt
`boot_a` und bleibt dann stehen, bis die Freigabe-Datei existiert:

    FREIGABE=$HOME/ok-set-active        # ohne diese Datei: kein set-active, kein Neustart
    boot_a geflasht. /Users/gregor/ok-set-active fehlt: --set-active=a und Neustart bleiben aus.
      Freigabe: touch /Users/gregor/ok-set-active    (der Lauf wartet 15 Minuten)
      oder selbst: fastboot --set-active=a && fastboot reboot

Gegengeprueft ohne Telefon mit einem `fastboot`-Attrapenfalle auf PATH und
leerem HOME (`firstlight/gate-test.sh`, 25 s, alle drei Zweige):

| Fall | Erwartung | Messung |
|---|---|---|
| A: Freigabe fehlt | kein set-active, kein Neustart, Exit 3 | ok; die Aktionsdatei des Mocks bleibt leer |
| B: Freigabe nach 4 s | erst set-active, dann Neustart | ok; Mock sieht `gesetzt`, danach `neuangestossen` |
| C: ACM-Knoten erscheint | ACM-Zweig statt Fastboot-Zweig | ok; `SERIELLE KONSOLE bei 3s (1 Knoten)` |

Zwei Fallen beim Testen, beide selbstgebaut: das awk-Fenster von
`mk_case()` auf die erste `}` in einer Zeile endet zu frueh ab, weil awk
fuehrende Leerzeichen ignoriert und die Regex die
eingerueckte `}` eines `{ ...; exit 3; }` im Funktionsrumpf matcht - das
abgeschnittene Stueck legte beim `eval` eine cachealte Funktion ueber die neue.
Und in `sed` bedeutet `&` in der Ersetzung "der Match": aus `T0=` wurde
`T$V=`, und weil der Zielpfad ein `V` enthaelt, lief die gekuerzte Kopie mit
einer ungebundenen Variablen. Deshalb prueft der Test jetzt die gekuerzte
Datei selbst (`grep -n 'T0='`), bevor er ihrem Urteil traut.

**Der naechste Schritt nach dem Foto ist nicht noch ein Bild.** Wenn
`libcomposite` laedt und trotzdem kein NCM am Host erscheint, ist die
Entscheidung gefallen: serielle Konsole. `fastboot oem uart enable` auf
Qualcomm-ABOOT, USB-C-Adapter ueber SBU1/SBU2, 1.8 V Logikpegel (nie 5 V an
den SoC), 115200 8N1; die Pixel-UART ist informativ und blockiert Fastboot
nicht. Kein Blindbau mehr, solange das Telefon nicht lesbar ist.

## 2026-10-29 09:31 — v0q ist in `boot_a`; der Slot-Write war uberflussig — und meine Begruendung dafuer war falsch

Der Runner hat das Bild um 09:31:37 geflasht (Vorher-Prüfung: 21094400 B,
sha256 `2911e6f7…`, soll = ist), dann 15 min auf `~/ok-set-active` gewartet —
keine Freigabe, Exit 3, **kein Slot-Write, kein Neustart**.

Was tatsächlich gemessen ist, steht allein in `fl-v0q/ERGEBNIS.txt` (Zeilen 4–6,
vor dem Write) und im read-only-Nachlesen um 10:48, Telefon weiter in Fastboot:

| getvar | **vor** dem Flash (09:31, im Log) | nach dem Flash (10:48, im Terminal) |
|---|---|---|
| `current-slot` | a | a |
| `slot-retry-count:a` | **2** | 3 |
| `slot-unbootable:a` | **no** | no |
| `version-bootloader` | — | b1c1-0.4-7617406 |

Erste Fassung dieses Abschnitts behauptete, **das Flashen habe den
unbootable-Flag gelöscht** — das war aus der Erinnerung geraten. Der Flag war
vor dem Flash schon `no`. In keinem Log, das diese Nacht überlebt hat, stand er
je auf `yes`: `fl-v0a/getvar-all.txt` (28.10., read-only) meldet
`retry:a:2, unbootable:a:no, successful:a:no`, `fl-v0q/ERGEBNIS.txt` (Zeile 6,
vor dem Flash) meldet `no`, und 10:48 ebenfalls `no`. Das einzige
`unbootable:a: yes, retry:a: 0` stammt aus der Sitzung um 03:06 und existiert
nur im Gespräch — `grep -rn unbootable /private/tmp/fl-v0*/ERGEBNIS.txt
/private/tmp/fl-v0*/kanal.txt` findet genau eine Zeile, und die sagt `no`. Eine
Prämisse, die nur im Kopf und nicht im Log steht, ist keine Messung — Commit
`819d162` hat genau das verdient.

Was die Logs hergeben und was nicht:

* **Herzugeben:** Slot a war vor dem Flash schon der aktive und war nicht als
  unbootable gemeldet. `--set-active=a` war damit überflüssig — nicht weil der
  Flash ihn geändert hätte, sondern weil er nie gesetzt werden musste. Was
  fehlt, ist ein Start, und ein Start ist kein Partitionsschreibvorgang.
* **Nur ein einzelner Messpunkt:** der Retry-Zähler stand vor dem Flash auf 2
  und nachher auf 3. Das passt zu „ABOOT füllt den Zähler bei einem erfolgreichen
  Flash auf", ist aber **eine** Stichprobe ohne Kontrollmessung — ich habe nicht
  bewiesen, dass der Flash ihn angehoben hat (ein Neustart, der den Zähler
  verringert, lag in der Zwischenzeit nicht vor). Nicht als Regel weitergeben.
* **Nicht herzugeben:** ob ABOOT `RESTART2` mit Grund `bootloader` ehrt.

`run.sh` schreibt die drei getvars jetzt **auch nach** dem Flash in
`ERGEBNIS.txt`; vorher standen sie nur davor drin, und genau diese Lücke hat
die Falschaussage möglich gemacht.

Nebenbei die Rückwegs-Frage sauber gemacht: die Datei
`android-mainline/factory/boot_a-ut-backup.img` war **0 Byte** (sha256
`e3b0c442…`, der Hash von nichts) und lag damit als Schein-Sicherung herum —
nach `quarantine/2026-10-29/` verschoben, umbenannt auf `…leer-0B`. Der
originale `boot_a`-Inhalt ist als **`factory/sp1a/boot.img`, 67108864 B,
sha256 `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e`**
vorhanden: `fastboot flash boot_a` mit diesem Bild stellt den Auslieferungszustand
von Slot a wieder her, **ohne** `userdata` zu löschen. Der Factory-Flash, der
Nutzerdaten kostet, ist also nicht der einzige Rückweg — das war in den Notizen
zu pessimistisch.

## 2026-10-29 12:30 — erster Boot seit v0q, und er bleibt weg: 10 min kein USB-Gerät

Der Beobachter (`/private/tmp/fl-v0q/beobachtung.txt`, 10-s-Raster) hat als
einziger Übergang in 6 1/2 Stunden Fastboot-Präsenz:

    t=6043s fastboot=1 ncm=0 seriell=0 12:29:51
    t=6053s fastboot=0 ncm=0 seriell=0 12:30:01     <- hier ist gestartet worden

Von da an bis 12:40:30 (Nachzählen am Host): `fastboot=0`, `ncm=0`,
`seriell=0`, `adb=0`, und das Telefon erscheint in **keiner** ioreg-USB-Liste
mehr. Zehn Minuten komplette Abwesenheit vom Bus — nicht "hängt im
Fastboot-Menü", nicht "NCM bleibt aus": weg.

Das ist ein bisher nicht beobachteter Boot-Zustand, und was v0q darin tut, ist
im Bild nachgelesen, nicht aus meiner Erinnerung (Init aus `firstlight.img`
zurückgelesen, 370 Zeilen):

* Zeile 93–109: der `restart2`-Block hängt in v0q an `if [ -f
  /etc/omamobile-panic-probe ]`, und **diese Datei ist im Bild nicht enthalten**
  (alle 737 cpio-Einträge durchsucht: kein `omamobile-panic-probe`, kein
  `omamobile-nogadget`). Der Block ist toter Code — es gibt keinen zweiten Weg
  hinaus.
* Zeile 361: `mark 'init main flow complete; PID 1 parking'`, Zeile 368–370:
  `while :; do sleep 60; done`. **PID 1 verlässt den Init nie**, kein Panic,
  kein Watchdog-Fressen: v0q hat keinen Mechanismus, der das Telefon von selbst
  zurück ins Fastboot bringt. Zehn Minuten Abwesenheit sind also **kein**
  Beweis gegen das Booten — sie sind mit einem lebenden, stummen Init verträglich.
* Lesefolge im Init, die das Foto zeigen kann: Zeile 119–123 meldet
  `gadget-module-dir gefunden` oder `KEIN /usr/lib/modules/... `, Zeile 124–132
  jede `.ko` einzeln (`modul usb_f_ncm.ko geladen` / `FEHLER <rc>`), Zeile 133
  `moduli: <n> geladen, usb_f_ncm <0|1>`, Zeile 150/182–183 `udc=…` und
  `binding UDC …`. Fehlt der Block völlig, entscheidet das Foto nichts.
* Was das Foto **nicht** unterscheidet: (a) Kernel lebt, Gadget bindet nicht,
  Panel zeigt etwas — (b) Kernel hängt früh, Panel dunkel. Der einzige Weg, das
  zu trennen, ist das Panel-Foto (Lesetabelle: `FOTO-LESETABELLE.md`) oder eine
  serielle Konsole. Kein weiterer Blindbau: v0q ist der erste Build, der Module
  und Gadget-Sequenz nachweislich im Bild hat, und er bootet gerade.

## 2026-10-29 13:51 — Beobachter zu Ende: 1080 Messungen, ein Umschlag

Das 10-s-Raster ist vollständig gelaufen (10:49:08 → 13:51:39, 1080 Zeilen,
gesichert: `quarantine/2026-10-29/beobachtung-v0q-3h.txt`):

* **ein** Umschlag in 3 h: `fastboot=1` → `fastboot=0` um **12:30:01**
* **null** Umschläge bei `ncm` und `seriell` — die beiden Sonden waren nie da
* danach 81 min bis zum Schluss ohne jedes Erscheinung am Bus

Der ERGEBNIS-Text des Laufes sagte „40 min" — das war der geerbte Satz aus der
40-min-Fassung des Skripts, gemessen waren 10951 s. In der Datei nachgezogen.

Was das heißt, ohne etwas hineinzulegen: v0q ist seit 12:30 am Booten oder tot,
und der Host kann beides nicht unterscheiden (Init endet in `sleep 60`,
restart2 ist toter Code). Die einzige trennende Beobachtung ist das Panel.
Kein Prozess läuft mehr; es wartet jetzt nichts auf etwas.

## Open questions for the maintainers

1. Is `android-v2` (the Pixel 4 XL's descriptor names it) the word this
   repository standardizes on for Qualcomm header-v2 phones, so
   `bin/omamobile`, `tools/install-phone` and `tools/build-rootfs` learn
   one method for this whole generation?
2. The shared `initramfs/init` reads its guard's allowlist the same way,
   but its probes are Tensor-keyed. Blueline-local init (flame's model)
   or one init with per-SoC sections?
3. The `MAIN_LUN`, `FIRMWARE_MAP`, `FACTORY_PRODUCT` and `USERDATA_FS`
   keys reserved in docs/RELEASES.md 3.2 fit this device exactly; values
   come from M1.3 and the owner's factory image.


## Reference enumeration test: the gadget WORKS, on this Mac, in 21 seconds (2026-10-29 18:11-18:17)

Claude's third correction was right: the reference had never been *measured*,
only assumed silent. `device/blueline/firstlight/ref-enumeration-test.sh`
measures it. The owner approved the one `boot_a` write at 18:10.

Hashes re-checked with `shasum -a 256` before the write, as agreed:

| file | bytes | sha256 |
|---|---|---|
| `pmos-ref-build/ref/boot.img` (reference, written to `boot_a`) | 28729344 | `ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82` |
| `android-mainline/factory/sp1a/boot.img` (the way back) | 67108864 | `5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e` |

Measured on the Mac, `ioreg -p IOUSB -l` plus `system_profiler SPUSBDataType`
every 5 s, comparing against a "before" snapshot:

| time | event |
|---|---|
| 18:11:18 | `fastboot flash boot_a` |
| 18:11:36 | t=16 s: new device `Google Pixel 3`, `fastboot=0` |
| 18:11:41 | t=21 s: `ncm=1` |
| 18:12:09 | macOS has interface `en11` with `172.16.42.2/24`, `status: active` |
| 18:12:09 | `ping 172.16.42.1`: 3/3 answers, avg 1.45 ms |
| 18:17:18 | `nc -z 172.16.42.1 22` closed; port 23 answers with a **root shell** |

So the answer to the question Claude posed is unambiguous: **the reference
appears — it is v0q, not the host, the cable, or macOS.** USB peripheral mode
works on this handset with this Mac, and it works 21 s after the kernel starts.

Details read *from the running reference* (telnet, `id` = `uid=0 gid=0`):

- `USB Product Name = "Google Pixel 3"`, `idVendor = 6353` = `0x18D1`,
  `idProduct = 53249` = `0xD001`. Same VID/PID as the fastboot device, so the
  host cannot tell the two states apart by VID/PID; the interface set can.
- The ramdisk is postmarketOS initramfs `3.12.5-r0`, OS `edge`, kernel
  `7.1.0-rc1-sdm845 #5-postmarketos-qcom-sdm845`, device string
  `Google Pixel 3 (google-blueline)`.
- `/pmOS_init.log` (transcript: `firstlight/evidence/pmos-init-log-reference.txt`):
  `Setting up USB gadget through configfs` -> `Server IP addr: 172.16.42.1:67,
  client IP addr: 172.16.42.2, interface: usb0` -> `Setting framebuffer mode
  to: U:1080x2160p-0` -> `Mount subpartitions of /dev/sda21` x7 -> `ERROR:
  failed to mount subpartitions!` -> `Creating logs disk` (32 MiB) -> `Making
  logs available via mass storage` -> `Entering debug shell`. It never reaches
  a Linux rootfs here: our `userdata` holds no postmarketOS install.
- Live configfs: `UDC = a600000.usb`, functions `acm.usb0`, `mass_storage.0`,
  `ncm.usb0`, all three linked into `configs/c.1`.
- Live `lsmod`: `usb_f_acm`, `u_serial`, `usb_f_mass_storage`, `usb_f_ncm`,
  `u_ether`, `libcomposite` — exactly the closure `refmodules.py` computed for
  v0q, plus `usb_f_mass_storage`.
- `ip addr`: `usb0: ... state UP ... inet 172.16.42.1/16`.
- The kernel log of this boot carries `console=null`. The reference suppresses
  the kernel console on a normal boot, which is a second, independent reason
  serial stayed dark and why `fastboot oem uart enable` is needed.
- Kernel ring buffer of this boot: `firstlight/evidence/dmesg-reference-2026-10-29.txt`
  (798 lines; the buffer had already wrapped, the gadget bind at 1.734 s
  survives in it).

**The difference that matters is not the gadget, it is the exit.** When the
reference cannot mount a rootfs, its PID 1 drops into a root shell *and sells
that shell over NCM on TCP 23*. Our init parks in `while :; do sleep 60; done`
and hands the host nothing. Three hours of `ioreg` could therefore never tell
"init stalled before the gadget" apart from "gadget bound and nobody was
listening": not one `grep` in `beobachtung.txt`, `ERGEBNIS.txt` or `kanal.txt`
matches a TCP probe, port 23 was never tried in 1080 samples.

Two corollaries for the next build:

1. `udhcpd` on the phone is what hands the host `172.16.42.2`; macOS claims the
   NCM interface on its own (`AppleUSBNCMControl`/`AppleUSBNCMData` bind
   without a kext). A static IP on the Mac is a fallback, not a requirement.
2. Our init's gadget block *is* the reference sequence (compare
   `firstlight/gadget-reference.sh`), and the module closure is right. What it
   lacks is the debug shell. If `mkdir functions/ncm.usb0` failed, `usb0` never
   appears, and every later `ifconfig usb0 ...` then fails into `/dev/null`
   with no trace. A debug shell answers that question in one telnet.

`console=null` also means: the panel photo and the UART are the *only* windows
into a normal reference boot; the NCM shell exists because this boot *failed*.

### Why the reference lands in a debug shell: `userdata` carries no filesystem

`blkid.txt` from that same logs disk (`firstlight/evidence/blkid-reference-2026-10-29.txt`,
dumped live over the NCM shell) answers the `Mount subpartitions` failure without
any guessing:

```
/dev/sda21: PTUUID="33035703-47b7-4be4-8555-905469b7ec46" PTTYPE="gpt" \
            PARTLABEL="userdata" PARTUUID="c9fe01bb-61af-4c04-895d-52bf22917764"
```

`PARTLABEL=userdata` with a GPT and **no `TYPE=`** — no filesystem signature at
all. `partitions.txt` sizes it at 54091756 KiB, i.e. ~52 GiB of raw GPT. Every other UFS partition reports its `TYPE` (`ext4`, `vfat`).
So postmarketOS is not failing to *read* a rootfs, it is failing to *find* one:
`pmos_root_uuid=d3ac3603-5b30-4869-91a4-ffbd570f115b` from the reference cmdline
exists nowhere on this handset, and the debug shell is the correct behaviour of a
boot that has a kernel, a gadget and no distro. The whole table (LUNs `sdb`/`sdd`/`sde`/`sdf` and all 21 `sda`
partitions) is `firstlight/evidence/partitions-reference-2026-10-29.txt`, read
out of the logs disk (`mount -o loop /tmp/logs.img /mnt/lg` inside the phone).

That reframes the goal once: to get past `Entering debug shell` this device needs
a rootfs written into `userdata` (or a `super`/`vendor_boot` route), not more
gadget work. The gadget is proven.

## The phone as oracle: 21 evidence files from the live debug shell (2026-10-29 18:45-18:55)

Claude's check-in: use the running reference as an oracle *before anyone reboots
it*. Done — `device/blueline/firstlight/oracle-capture.py` drives the telnet
shell (it strips the echoed command lines, which is what makes these files
readable) and captured into `firstlight/evidence/`:

`cmdline.txt`, `modules.txt`, `lsmod.txt`, `udc-list.txt`, `udc-state.txt`,
`udc-soft-bus.txt`, `gadget-tree.txt`, `gadget-values.txt`, `gadget-links.txt`,
`configfs-mount.txt`, `ncm-iface.txt`, `typec.txt`, `dwc3.txt`, `ttyGS.txt`,
`serial-getty.txt`, `uname.txt`, `proc-partitions.txt`, `init-find.txt`,
`dtb-board.txt`, `partitions-reference-2026-10-29.txt`,
`pmos-setupusb-source.txt` — plus `dmesg` (797 lines, buffer had already
wrapped) and `/pmOS_init.log` captured earlier. `pmos-setupusb-source.txt` is
the gadget source *as it exists in the shipped image's `init_functions.sh`*
(366-entry extraction of `/private/tmp/ref-ramdisk.cpio`), cross-checked line
for line against the live sysfs values below.

What the oracle says, in one breath:

- `state = configured`, `UDC = a600000.usb`, configfs mounted `rw,nosuid,
  nodev,noexec`; functions `ncm.usb0` + `acm.usb0` (`console=1`, `port_num 0`)
  + `mass_storage.0`, all three linked into `c.1`; `idVendor 0x18d1`,
  `idProduct 0xd001`, strings `Google`/`Google Pixel 3`/`postmarketOS`;
  `bcdUSB 0x0210`, `max_speed super-speed-plus`, `bmAttributes 0x80`.
- The DHCP server on the phone is **`unudhcpd -i usb0 -s 172.16.42.1
  -c 172.16.42.2`** (`serial-getty.txt`) — not busybox `udhcpd`. The shell is
  `telnetd -b 172.16.42.1:23 -l /sbin/pmos_getty`.
- `/sys/class/typec/` is **empty** — no class devices at all on this boot
  (`typec.txt` is just the unexpanded glob). Whatever role logic exists, the
  gadget does not need a typec class entry to reach `configured`.
- **The number that changes the diagnosis: the reference reaches
  `Setting up USB gadget through configfs` at 1.708 s and the gadget's
  `HOST MAC` line at 1.734 s.** pmOS stage1 starts at ~1.155 s; its stage2
  still does rootfs probing first. Our v0q init is PID 1 directly with no
  stage1 detour — it reached `udc=$(ls /sys/class/udc | head -1)` **once**,
  early, and if dwc3 had not finished probing at that instant it printed
  `No UDC found, skipping gadget setup` and skipped the gadget for the entire
  boot, then parked in `sleep 60`. 83 minutes of total bus absence, no panic,
  no come-back: exactly what that code path produces. The dmesg ring had
  already wrapped, so the dwc3 probe timestamp itself is gone — the 1.734 s
  bind is the earliest positive proof the UDC existed, not a proof it existed
  earlier. That is why the fix is a wait loop, not a guessed constant.

## Bisection from the good side, two images built (not yet flashed)

Per Claude: one change per flash, starting from the known-good side.

**Bild A** — `ref-packer` content, our packer. Built by
`firstlight/build-refpacked.sh` (alpine arm64, same pack-v0.py call as every
v0 build). `cmp -l` against the reference: **exactly 20 bytes differ, offset
577–596 — that is the `id[]` field and nothing else.** Same file size
(28729344 B), same header fields (incl. `page_size@40 = 0` — the reference
itself carries 0 there, our v0 layout discovery was already the distro's),
byte-identical kernel+DTB section (16154252 B), byte-identical zstd ramdisk
section (12569303 B at the 4096-boundary `16158720`), byte-identical embedded
cmdline (218 chars, `pmos_boot_uuid`/`pmos_root_uuid` included, `extra_cmdline`
empty on both). sha256 `346a96dac53567f60f1fe6645f5021a0b73197a3d8e0aafb347eefbdd1d9f13a`.

**Bild v0r** — v0q plus two changes in `init` only
(`firstlight/patch-v0r.py`, build `build-v0r.sh`, checks `verify-v0r.py` +
the unchanged 28-point `verify-v0q.py`, `bash -n` clean). 1: UDC wait loop,
60 half-second rounds instead of one read; 2: debug shell
`telnetd -l /bin/sh` respawned forever, armed before dropbear, listening on
*:23 even if usb0 never appears. Panel title now says `first-light v0r` so a
photo identifies the build. sha256 `44d4f2648a328b964db1b1f2e9e4cec58d8d54ae26985db32ff38713f9e06a75`
(image 21094400 B, init 17230 B, 6 modules intact).

Three harness faults surfaced while building v0r, all mine, all now guarded by
files instead of heredocs: (1) I repeated the mistake that stands warned in
build-v0q.sh's own header — a `<<PY` heredoc *inside* `sh -euc` lets ash
expand `$(ls /sys/class/udc …)` and die on `$_i: parameter not set` before
python ever sees the line; checks moved to `verify-v0r.py`. (2) verify-v0q.py
silently compared modules against a missing `/m` mount and reported `not ok`
for it — a container mount is part of the test surface. (3) The anchor
indentation: the init in the archive is indented 4 spaces, a full terminal
dump had shown it with more; anchors must come from the archive, never from
the screen.

Predicted readings, fixed BEFORE the flashes so nobody can bend them after:
A must enumerate like the reference (~16 s device, ~21 s NCM, telnet 23 =
pmOS debug shell). v0r must enumerate (`Google Pixel 3` with
0x18d1:0xd001) AND answer telnet 23 with an Omarchy Mobile shell whose
`/run/steps.log` ends in `debug shell armed` — if it enumerates late
(not before ~1.7 s), the UDC-timing diagnosis is confirmed with a number.
If v0r enumerates but the shell is dark, init died between gadget bind and
telnetd. If v0r stays dark on the bus while A is bright, the difference is
inside our ramdisk's init again, and steps.log will finally be readable to
say where.

UART: Claude and the evidence agree it is no longer urgent — NCM+telnet is a
proven channel on this handset, and v0r carries its own shell.

## Ad-hoc verification of the bisection tools (30 ok / 0 not ok), two faults it caught

The suite says the tree is sound; it does not yet know these files. A focused
script (ad-hoc, tempfile-scoped, since deleted — not suite-green by definition)
checked what this round actually created: Bild A byte-invariants against the
reference, `patch-v0r.py` reproducing the shipped v0r archive byte-exact,
`verify-v0r.py` accepting v0r and *refusing* the old v0q image (a counter-check,
not only a happy path), the runner's exit branches against a fake fastboot, and
`strip_echo` against a real captured prompt transcript, including a wrapped
command line. 30 ok / 0 not ok, exit 0. Two real faults fell out:

1. **`run-flash-observe.sh` died at its devices gate, and my first diagnosis of
   it was wrong.** I blamed `fb=$(count)` (`grep -c` exits 1 on zero matches,
   `pipefail` carries it). The mutation test refuted that: the raw count() had
   `| head -1` behind the grep, so the pipeline always ended in `head` — exit 0
   — and the mutated runner ran the full loop to `ERGEBNIS:` anyway. The real
   kill was fault 2 below: the unconditional platform-tools prepend let the
   *real* fastboot answer `devices` (phone running, not in fastboot) and the
   gate exited 1. The `|| true` stays as cheap insurance, now commented as
   precaution, not as the fix. This is the same mistake class as the
   slot-unbootable narration: a mechanism asserted from a single reading
   without a test that isolates it.
2. **My own PATH-prepend trap, now inside my own runner:** the script prepended
   `platform-tools` to PATH unconditionally, so a fake placed there by a test
   lost to the real fastboot — the same fault class `tests/ref-enumeration`
   documents for `ref-enumeration-test.sh`. The runner now prepends only when
   no fastboot is already on PATH, counter-checked under
   `env -i PATH=/usr/bin:/bin` — with a clean environment it still finds the
   real binary and exits honestly (`kein Fastboot-Geraet`, because the phone
   is *running*, not in fastboot). A fix that only works under the test's PATH
   is a disablement, not a fix.

One of my own check lines was also wrong before it ever ran: I asserted `_i`
must not appear in init at all — an invented constraint; v0q already used `_i`
in the bootdev search and init runs without `set -u`. The real check is that
the *new* loop counts with `udc_wort` and the two existing `_i` counters are
untouched. And the honest re-scan of Claude's CJK point: the full tree holds
4794 CJK-range characters in exactly **one** file,
`packages/omamobile-owl-widgets/index.json` (pre-existing, committed at
`4eafa28`, not from this bring-up); every file this bring-up touched is clean.

Suite re-run for the runner fix on native arm64: 121 ok / 0 not ok / 4 skip /
exit 0.

## The ad-hoc checks became `tests/bisection` — and a mutation retracted one of my diagnoses

Rather than re-running a throwaway script every round, the 30 ad-hoc checks were
promoted into the canonical suite as `tests/bisection` (wired into `tests/all`).
It pins: Bild A differing from the reference **only inside `id[]`** (every other
byte of 28729344 equal), `patch-v0r.py` reproducing the shipped v0r archive
byte-exact with `init` the only changed member, `verify-v0r.py` accepting v0r
*and refusing* v0q (a checker without a counter-check is a blind spot), the
runner's exit branches against a fake fastboot (hash gate before any `fastboot`
call, missing-image gate, way-back confirmed, getvars read back after the write,
loop surviving zero new bus entries), and `strip_echo` removing the phone shell's
echo — including a command wrapped at 79 columns. Two mutations: a byte flipped
outside `id[]` in Bild A, and the fake-fastboot directory removed — both caught.

**The second mutation caught *me*, not the code.** When I stripped `|| true` from
the runner's `count()`, the suite still passed — because the real `count()` ends
in `| head -1`, and `head` exits 0 whatever `grep -c` did. So my logged cause of
death ("`grep -c` exits 1 on zero matches, `pipefail` carried it into the loop")
was never the killer; the unconditional platform-tools PATH prepend was — the
*real* fastboot answered `devices` (the phone was running, not in fastboot) and
the gate exited. I had written a postmortem from a single reading without an
isolating test — the same fault class as the slot-unbootable narration, now
recorded in SKILL.md both directions: assert mechanism only when a test isolates
it, and let a mutation say which guard actually bears load. The `|| true` stays
as labelled insurance.


## Claudis Check-in #9 und die Messinstrumentierung — vier Harness-Fehler, einer pro Fassung

Claudis drei Punkte, alle angenommen:

1. **Bild A liefert fast keine Information.** Bei entsperrtem Bootloader prueft
   ABOOT die `id[]` nicht; 20 Bytes, die nichts entscheiden, kosten einen
   Bootzyklus. Empfehlung an Gregor ist deshalb **direkt v0r**, Bild A bleibt
   Fallback, falls v0r dunkel bleibt.
2. **Die Zeitmessung muss im Geraet entstehen.** Die 16 s am Host enthalten
   ABOOT und Kernel-Start; „Enumeration spaeter als 1,7 s" ist von aussen nicht
   entscheidbar. Die Warteschleife schreibt jetzt in `steps.log`:
   `udc-lesung 1: uptime <x>s, inhalt: <ls-Ausgabe>` bei der ersten Lesung und
   `udc nach <n> runden gefunden: <udc>, uptime <y>s` beim Fund. **Runde 0 =
   der UDC war sofort da = die Timing-Diagnose ist widerlegt** und der Fehler
   sitzt woanders. Dazu drei fruehe `dmesg`-Dumps nach `/run` (2/12/42 s
   kumulierte Wartezeit), weil der Ring bei der Referenz schon uebergelaufen
   war, bevor ihn jemand las.
3. **v0r enthaelt zwei Aenderungen** (Warteschleife + Debug-Shell). Als
   Instrumentierung akzeptabel, trennbar genau durch Punkt 2. Rueckweg aus der
   Telnet-Shell: `reboot bootloader` — vorgeschlagener Standard statt
   Tastendruecken.

Das neue v0r: init 18146 B, Bild 21094400 B,
`sha256 daf56a12cca1af3d05444eaad7008dd01e8fb14266ffc32f6f419ef0aff5060b`
(v0r vorher: `44d4f264…`, ohne Messung). Das Balance-Assertion in
`patch-v0r.py` steht von +2 auf +3 `done` — die Zahl ist jetzt gemessen
(v0q hat 19 `done`), nicht aus der Erinnerung behauptet.

### Vier echte Harness-Fehler, einer pro Fassung

Der Runner lief auf Alpine nie, und jede Fassung meiner Korrektur hatte einen
neuen Fehler, den der vorherige Test nicht sehen konnte:

1. **`shasum` hart aufgerufen** — Linux kennt nur `sha256sum`; die Hashzeile
   lief leer, das Gate meldete `Hash  != …` und stieg aus, ohne `fastboot` je
   zu rufen. Fix: `sha()` mit Weiche.
2. **`stat -f %z` als „nur macOS" missverstanden** — auf Linux ist `-f` GNUs
   `--file-system`: kein Fehler, sondern ein mehrzeiliger Filesystem-Report auf
   stdout. Der `|| stat -c`-Fallback griff damit nie.
3. **Die Sonde auf `/dev/null`** — die BSD-Datei ist 0 Bytes gross, ihr
   richtiger Wert ist von einem Fehlschlag nicht zu unterscheiden; meine
   korrigierte Fassung meldete „Rueckweg 0 B" auf macOS.
4. **`stat -f%s`** — Alpine lehnt `-f%s` mit `invalid option -- '%'` ab
   (`-f` nimmt dort kein Argument), macOS kennt `-c` nicht. Jede stat-Variante
   verbiegt sich woanders.

Endstand: `fsize()` ist `python3 -c 'os.path.getsize'` — auf beiden Seiten
dasselbe Werkzeug, dasselbe Ergebnis. Zwei Lehren:

* **Ein Feature-Test muss auf einer Datei mit von 0 verschiedenem Wert
  sondieren**, sonst ist „kein Fehler" nicht von „falsche Antwort" zu
  unterscheiden.
* **Eine schwache Pruefstelle verschleiert die folgende.** Der Test fragte nur
  `grep -q "Rueckweg steht"` — die Zeile erschien auch mit kaputter Zahl.
  Jetzt wird die Zahl selbst gegen `os.path.getsize` verglichen, und beide
  Plattformen muessen sie liefern.

Nebenbei: `RKSHA` war im Container-Zweig von `tests/bisection` ungebunden
(`set -u`), und der shasum-Pauschal-Null-Hash in `tools/ci-arm64.sh` liess den
Runner den *korrekten* Bild-Hash verwerfen — der Harness log, nicht das Geraet.
Der Fake liefert jetzt echte Hashes. `inetutils` existiert in alpine:edge
nicht und haette mit einem Pauschalfehler die ganze apk-Transaktion still
sterben lassen: das `>/dev/null 2>&1` verbarg „unable to select packages", das
Ergebnis war Exit 127 „bash: not found".

## Der Nebenpfad hat den Strang verlassen (2026-10-29, nach Check-in #10)

Vorwurf aus dem Check-in: seit 20:48 laeuft ein Nebenpfad mit 27 uncommitteten
Dateien, darunter die install-Streifen von cheetah, felix, husky, modem und
waydroid — Pakete anderer Geraete, nur damit `tests/all` auf der BSD-Shell des
Rechners laeuft. Um 18:42 hatte ich selbst festgehalten, dass der Container der
kanonische Laeufer ist. Der Vorwurf stimmt, und der Nebenpfad ist jetzt ein
eigener Zweig: `host-portability` (`79f836e` → `7247dd3` → `c6dd6f4`),
Arbeitsflaeche `/private/tmp/wt-hostport` (git worktree, damit kein Umschalten
unter einem laufenden Test hindurchfaellt).

Beide Zweige sind gemessen, nicht behauptet:

* **Strang `4689a32`, kanonischer Laeufer** (alpine arm64, Baum bei Laufstart
  `4689a32`, 0 Aenderungen): `SUITE: ok=129 (davon skip=4) not-ok=0 exit=0`,
  SUITE GRUEN. Der Nebenpfad ist darin nicht enthalten — mechanisch nachgesehen
  statt erinnert: `git show 4689a32:tests/all` kennt `tests/host-portability`
  nicht (0 Treffer) und die Datei existiert an dem Commit nicht.
* **Zweig `c6dd6f4` auf dem Rechner** (bash 3.2, BSD find, BSD install):
  129 ok, 0 nackige `not ok`, Exit 0, Startzustand im Protokoll selbst
  ausgewiesen (`Baum bei Laufstart: c6dd6f4, Aenderungen: 0`).

Was der Zweig gegen den Strang einbuessen wollte und was er nicht verliert: die
Paket-Streifen sind auf dem Zweig **wieder unangetastet** — `git diff --name-only
4689a32 c6dd6f4 -- packages/` ist leer, der Fang ist 12 Dateien, alle unter
`tests/` und `tools/`. Die portable install-Funktion wird zentral in `tests/all`
aktiviert und wirkt ueber `export -f` bis in die Kind-Skripte der Paket-Tests
(gemessen: Kind und Enkel schreiben, ohne Export fehlt jede Datei). Der Anlass
 fuer den Rueckbau war ein `not ok - build or install reaches outside the
package directory`: vier Paket-Tests pruefen per `grep -q '\.\./\.\.'`, dass ihr
Skript das Paketverzeichnis nicht verlaesst, und meine Einbindezeile enthielt
`../../` woertlich.

Drei Laeufe, die ich vorher als Beleg zaehlen wollte und die keiner sind:
129 ok und 136 ok stammen aus Container-Laeufen, die im uncommitteten Baum
starteten und in die ich hineineditiert habe, und ein sechzigminuetiger Lauf
endete mit **einer Zeile, Exit 137** — ich hatte ihn selbst mit `docker stop`
ueber einen `--filter ancestor=alpine:edge` abgeschossen, der auch sein
Container traf. Eine Suite, in die hineineditiert wird, beweist nichts fuer
einen Stand; ein Lauf mit leerem Protokoll beweist schon fuer gar nichts.

Der Anruf zum Flashen steht weiter aus. v0r (`daf56a12…`) liegt gebaut, das
Orakel laeuft unveraendert (pingbar, Port 23 offen), und es ist kein Write
geschehen.

## Die Freigabe-Frage enthielt zwei falsche Angaben (Check-in #11)

Freigabe-Arbeit ist keine Nebenpfad-Arbeit: wenn die Information falsch ist,
auf der das „ja" steht, ist das „ja" wertlos. Zwei Angaben, beide von Claude
korrigiert und in der Datei nachgesehen, nicht im Kopf:

* **„die Referenz-Version mit zwei Zeilen von mir"** — falsch. v0r ist v0q:
  meine init, mein Ramdisk, meine sechs Module, plus Warteschleife und telnetd.
  Mit der Referenz teilt es den Kernel. Was das Bild also zeigt, ist unser Code
  mit einer wartenden Gadget-Einrichtung — nicht „die Referenz fast unveraendert".
* **„du bekommst die laufende Referenz zurueck, per Kommando"** — teilweise
  falsch. `run-flash-observe.sh` gateierte als Rueckweg gegen
  `factory/sp1a/boot.img` (`5c1ce19e…`, Android-Urzustand), nicht gegen
  `pmos-ref-build/ref/boot.img` (`ed2c225f…`). Stufe 1 ist jetzt die Referenz
  selbst (Pfad und Hash im Code, gemessen 28729344 B, `1951b3e`); Android bleibt
  Stufe 2. Und „per Kommando" gilt nur, wenn v0rs Telnet antwortet — bleibt das
  Bild dunkel, was genau der Fall ist, fuer den man einen Rueckweg braucht, hilft
  nur **Power + Leiser ~10 s** und danach mein Flash.

*Zu den Hash-Verweisen in diesem Eintrag:* die zuerst genannten (`584056e`,
`b8dba73`) waren nach den Textausbesserungen per `--amend` nicht mehr auf dem
Zweig — `git cat-file -e` findet sie weiter (die Objekte leben), `git log` nicht
mehr, und der Dateiraum raeumt sie frueher oder spaeter ein. Ein Protokoll, das
auf ein Objekt ausserhalb der Geschichte verweist, ist nicht nachpruefbar. Regel
dafuer: einen Commit-Hash erst dann ins Protokoll schreiben, wenn der Eintrag
selbst mit diesem Commit landet — Ausbessern nachtraeglicher Verweise macht sie
selbst wieder falsch.

Dabei erwischt, zum zweiten Mal an diesem Abend, dass eine Zahl in einer Meldung
keine Pruefung ist: die Gate-Meldung behauptete 67108864 B, der Code prüfte
>1000000 B und den Hash (`d234cfb`). Und dass eine Sonde die haeufigere
Fehlerquelle ist: `OUT="$o" … "$@" bash …` uebergibt Umgebungsvariablen als
Befehl (Exit 127, kein Protokoll), die Pruefung meldete „keine Meldung" wo das
Gate laengst richtig antwortete.

Nachtrag zur Freigabe-Praxis: zwischen der ersten Frage um 22:26 und dem
Check-in lagen acht Nachfragen, jede an eine Hintergrund-Meldung angehaengt.
Eine Frage, die auf berichtigten Fakten steht, wird einmal gestellt — dann ist
Ruhe, bis der Besitzer antwortet.

## 2026-10-30 04:2x — Die Bilder lagen im Räumordner (Check-in #13)

Check-in von Claude: v0r, `fl-v0q`, `refmod` und `fl-refpacked` lagen unter
`/private/tmp`. macOS räumt das beim Neustart und den Rest periodisch nach
Alter. Das Gate hätte im Ernstfall *ehrlich* abgebrochen — nur eben in dem
Moment, in dem das Telefon dunkel ist und zurückgeflasht werden soll, und
`tests/gadget-modules` wie `tests/bisection` hätten ihre Artefakte verloren.
Ein Rückweg, dessen Datei im Ordner des Betriebssystems liegt, das den Ordner
räumt, ist kein Rückweg.

Gemessen, nicht übernommen:

* 69 Dateien, 0,33 GB nach `~/hermes-workspace/images` (außerhalb des Repos),
  Kopie mit Zeitstempel, danach Quell- und Ziel-Hash jeder Datei verglichen und
  Bytevergleich mit `cmp`: 0 Abweichungen. Gegenprüfung am neuen Ort mit
  `shasum -a 256 -c SHA256SUMS`: 69 Einträge, 0 nicht-OK. Das Manifest
  `images/SHA256SUMS` und `images/HERKUNFT.md` halten die Messwerte fest.
* Die drei tragenden Werte am neuen Ort, identisch zu denen des Hash-Audits:
  v0r `daf56a12…` (21 094 400 B), v0q `2911e6f7…` (21 094 400 B), Bild A
  `346a96da…` (28 729 344 B). Auch die Eingaben der historischen Baurezepte
  (`fl-v0k/kernel-blob`, `fl-v0o/new.cpio`, `new.cpio` von v0l/v0n) und die
  0,1 MB Text-Beweise (`ERGEBNIS.txt`, `kanal.txt`) sind dabei — die wären
  ebenfalls geräumt worden.
* Die Kandidatenlisten wählen wirklich den neuen Ort, nicht den Rückfall:
  `IMG_A`, `IMG_V0R`, `CPIO_V0Q`, `V0Q_IMG`, `IMG` und `STAGED` lösen alle auf
  `~/hermes-workspace/images/...` auf (nachgestellt, weil „der Default zeigt
  jetzt dorthin" ohne Auflösung gemessen werden muss).
* `tests/gadget-modules` und `tests/bisection` nach der Umstellung: Exit 0.
* Kein Write ans Handy: Telefon bei 172.16.42.1 pingbar, Port 23 offen, `boot_a`
  hält weiter die Referenz (`ed2c225f…`).

Umgestellt wurden 22 Stellen in 13 Dateien: die Kandidatenlisten der beiden
Tests (neuer Ort zuerst, `/private/tmp` als Rückfall für Container-Läufe, die
den alten Namen eingehängt bekommen), die Ausgabeorte von `run-flash-observe.sh`
(`flash-observe`), `ref-enumeration-test.sh`, `gate-test.sh`,
`build-refpacked.sh` und `refmodules.py`, die fünf Baurezepte
`build-v0m/v0o/v0p/v0q/v0r.sh` und `tools/ci-arm64.sh` — das braucht jetzt einen
einzigen Mount (`-v ~/hermes-workspace/images:/images:ro`) statt der fünf
Einzelmounts, deren fehlender jeweils ein `not ok` war, das Dunkelheit war.

Zwei eigene Fehler beim Umstellen, beide von den Werkzeugen gefangen: der
Token-Tausch setzte ein öffnendes Anführungszeichen ohne schließendes (`sh -n`
auf jeder berührten Datei), und zweimal fiel die Ersetzung in ein bereits
quotiertes `echo "…"` — gültig, aber liest sich wie ein Fehler. Deshalb prüft
das Umstellungsskript jetzt, dass jedes Muster genau einmal trifft, und meldet
pro Datei: ein stilles Nichtstun sieht sonst aus wie eine fertige Wanderung.

**Die Nachprüfung hat eine echte Lücke gefunden, die ich selbst gerissen habe.**
`build-v0q.sh` verlangt `fl-v0p/new.cpio`; die Datei war nicht mitgezogen —
vorher lag sie unter `/private/tmp` und wurde dort gefunden, nach der Umstellung
hätte der Bau am neuen Ort abgelehnt. Nachgeholt (19 297 676 B, Hash
`36a5d711…`, Quell- und Ziel-Hash gleich, `cmp` ohne Unterschied), Manifest auf
70 Einträge neu erzeugt, Gegenprüfung: 0 nicht-OK.

Drei Fehler der Sonde selbst, jeder einzelne hätte die Lücke unsichtbar
gemacht — und alle drei sind dieselbe Klasse wie der aus dem Kopf gesetzte
Hash:

* Der Kandidaten-Regex ließ die halb quotierte Form nicht zu und meldete
  **null Eingaben** bei Dateien, die sieben enthielten. Eine leere Prüfung und
  eine kaputte Prüfung sehen gleich aus; die Zahl der Prüfsteine wird jetzt aus
  dem Text abgeleitet und gegen die Textstellen gemeldet.
* Eine Schwelle aus dem Kopf (`>= 12` Mounts, `>= 14` Eingaben) als Erwartung —
  durch Zählung aus den Dateien ersetzt.
* Eine Prüfung, die verlangt, dass *sie selbst* etwas geändert hat
  (`n >= 2` geschlossene Anführungszeichen): im zweiten Lauf richtet sie nichts
  mehr und fällt aus, obwohl der Baum in Ordnung ist. Geprüft wird der
  Zustand, nicht die eigene Tat.

`sh -n` allein hätte die offene Anführungszeichen-Kette nicht gefangen: sie
pairt sich mit dem Anführungszeichen des nächsten `echo`, also ist die Datei
parsbar und trotzdem falsch. Sechs solcher Stellen. Der Nachweis läuft die
Prüfzeile deshalb im echten Lauf und vergleicht ihre Antwort mit der Platte.

Mutationstest gegen die Sonde: ein Symlink-Spiegelbaum ohne `fl-v0p/new.cpio`
lässt sie mit Exit 1 und genau diesem Dateinamen umfallen. Eine Sonde, die nur
grün meldet, ist kein Beweis. Stand: 55 Prüfsteine ok, 0 not ok; Manifest
70 Einträge, 0 nicht-OK. Das ist Ad-hoc-Nachweis der Pfade, nicht das
Suite-Ergebnis — der Containerlauf über den neuen Mount wird separat
nachgetragen.

### Der Containerlauf über den neuen Mount: 129 / 0 / 4 skip

`docker run --rm --platform linux/arm64/v8 -v "$PWD":/w:ro
-v ~/hermes-workspace/images:/images:ro -v $WS/pmos-ref-build:/pmos-ref-build:ro
-v $PWD/tools/ci-arm64.sh:/v.sh:ro alpine:edge sh /v.sh` →
**`SUITE: ok=129 (davon skip=4) not-ok=0 exit=0`, `SUITE GRUEN`**. Ein Mount für
alle Bilder statt der fünf alten, und die Zahl ist identisch zu der von vor der
Wanderung — die Umstellung ändert also nichts, was die Suite sieht.

Zur Herkunft, weil die Regeln hier schon einmal gezahlt haben: der Container
kopiert `/w` beim Start nach `/work`, die Zahl gehört also einem Arbeitsbaum
*vor* den beiden folgenden Commits. Nachgesehen, nicht angenommen — der
Unterschied zu `08f00c3` betrifft vier Dateien, und keine Zeile davon liest die
Suite:

* `BRINGUP-M1.md` — Text, liest kein Test.
* `build-v0p/v0q/v0r.sh` — die geänderten Zeilen sind ausschließlich die sechs
  geschlossenen Anführungszeichen. Die zwei Tests, die diese Dateien überhaupt
  lesen, tun es mit `grep` nach `gadget-reference.sh` und `panel-status.sh`
  (beide Treffer sitzen heute noch drin: 2 und 1) bzw. mit einer
  Existenzprüfung. Kein Test führt die Rezepte aus.

Dabei der blinde Fleck, warum `sh -n` die offene Anführungszeichen-Kette nicht
meldete und die Suite sie durchließ: **`tests/all` parst `tests/*` und einige
Werkzeuge, aber nie `device/blueline/firstlight/*.sh`.** Die Baurezepte — die
einzigen Dateien, die Bilder bauen und deren Hashes vergleichen — stehen in
keiner Parse-Schleife. Nachtrag: drei Dateien in diese Schleife, was die
Suite-Zahl ungültig macht und einen Neulauf braucht. Bewusst *nicht* erledigt,
solange die 129 als letztes Ergebnis gelten sollen: eine Suite, die ich im
gleichen Atemzug ändere, über die ich gerade ihre Zahl berichte, beweist
nichts (derselbe Fall wie der Lauf, der während meines Editierens lief).

## 2026-10-30 13:12 — Drei Fäden nach Check-in #16, und einer davon ist das Orakel selbst

Kein Write ist geschehen. Die drei Fäden waren: die Referenz mechanisch zu Ende
lesen, den Beweis-Einsammellauf trockentesten, und das Gerät nachmessen.

**Faden 1, die mechanische Diagnose ist fertig.** Die Referenz-Initramfs liegt
als **zstd** (Magik `28b52ffd`) und ist zwei aneinandergesetzte cpio-Archive;
entpackt mit dem Repo-eigenen Verifizierer, dessen Feldsatz den Kopf erklärt
(`ramdisk_size` bei Offset **16**, nicht 20 — den Wert 0 bei 20 hatte ich aus dem
Kopf gesetzt). In ihrer `init_functions.sh` steht:

* `get_usb_udc()` (Zeile 810): `ls /sys/class/udc | head -1` — **einmal, ohne
  Warteschleife**, exakt wie v0q es tut.
* `setup_usb_network_configfs` (Zeile 840–843): bei leerem UDC
  `No UDC found, skipping gadget setup` und Rückkehr.
* Die "zweite Chance", die ich vermutet hatte (Zeilen 1014–1057), gehört
  `setup_usb_storage_configfs` — dem USB-Speicher, nicht dem Netzwerk.

Die Referenz gewinnt also nicht, weil sie wiederholt, sondern weil
`pmOS_init.sh` die Funktion erst bei 1,708 s aufruft, nachdem dwc3 bei ~1,7 s
probiert hat. v0rs Warteschleife ist deshalb eine **Verbesserung, keine
Kopie** — und die Runden Zahl bleibt die entscheidende Messung: Runde 0 oder 1
heißt, dass dwc3 unter v0r nie throughkommt, und dann ist das Gadget selbst
der Fehler, nicht sein Timing.

**Faden 2, der Trockenlauf hat einen echten Fehler im Runner gefunden.** Der
Einsammelblock hat jede Zeile verworfen, die das **erste Wort** ihres Befehls
enthielt, um das Echo loszuwerden. Sein entscheidender Befehl heißt
`cat /run/steps.log`, und fünf Texte unseres eigenen init enthalten `cat` —
darunter `udc=$(ls /sys/class/udc 2>/dev/null) gebunden=$(cat …)` und
`UDC steht auf: $(cat …)`. Die zwei Zeilen, um die es im ganzen Zyklus geht,
wären **spurlos verschwunden**. Gegenbeweis am lebenden Gerät: ein Befehl,
dessen Ausgabe sein eigenes erstes Wort enthält, verlor genau diese Zeile.
Der neue Filter (Zeichen `# HEBER-ANFANG`/`-ENDE` im Runner) wirft nur noch
die Zeile, die **exakt** dem Befehl gleichkommt, und Prompt-Zeilen; jeder
Einsammelbefehl bleibt unter 60 Zeichen, weil die pmOS-Leitung bei ~80 Spalten
bricht und ein zerrissenes Echo nicht mehr entscheidbar ist.
Der neue Test (Abschnitt 5b in `tests/bisection`) liest die Funktion **aus dem
ausgelieferten Runner heraus und führt sie aus**, und holt sich die zwei
decisiven Zeilen aus dem ausgelieferten **Bild** (Kompression am Magik-Byte
entschieden, nicht im Kopf), statt sie abzutippen; er verlangt außerdem, dass
der **alte** Filter an denselben Zeilen verliert — sonst beweist der neue
nichts. Läuft: `2 decisive Zeilen gerettet (längster Befehl 45 Zeichen), der
alte verlor 2 davon`. Eine leere Datei heißt jetzt `ACHTUNG leer` statt
schweigend Erfolg (dieselbe Fehlerklasse wie ein Prüfstein, der eine fehlende
Datei als "ok" bucht). `tests/bisection`: 9 ok / 0 not ok / Exit 0 (vorher 8,
einer ist der neue). Die Container-Zahl 129 gilt nicht mehr — nach dieser
Änderung wäre ein Neulauf nötig, und den gab es hier nicht.

**Faden 3, das Orakel ist dunkel, das Gerät sitzt im Fastboot-Modus.**
Ping 100 % Verlust, Port 23 und 5555 zu, ARP und adb leer — aber `ioreg` zeigt
"Google / Pixel 3" an USB, und `fastboot devices` meldet `PIXEL3-SERIAL  fastboot`.
Die Zähler unverändert (getvar: retry:a 2, unbootable:a no, successful:a no,
current-slot a, unlocked yes, bootloader b1c1-0.4-7617406). **Ein Grund ist
nicht belegt**, und ich habe keinen gesucht; die letzten Telnet-Aktionen von
mir waren ausschließlich `cat`/`tail`/`ls`/`ps`/`lsmod`. Nichts angefasst: ein
Wiederanlaufen der Referenz über `fastboot reboot` hätte einen der zwei
verbleibenden Fehlstarts gekostet, und das ist Gregors Entscheidung, nicht
mein Aufräumen. Folgen für das Verfahren, beide im Block nachgezogen: Schritt 0
ist jetzt **fallback**, weil das Gerät schon in fastboot steckt — erst
`fastboot devices` lesen —, und die Zahl der verbleibenden Fehlstarts ist eine
Bedingung für das Vorgehen geworden. `fastboot --set-active=a` soll die Zahl
auffüllen und die unbootable-Markierung löschen; **für diesen Bootloader ist
das unbelegt**, es ist ein Meta-Daten-Write, und deshalb liegt es als
Vorschlag da und nicht als ausgeführter Schritt. Belegbar ist es erst nach dem
Zyklus, mit getvar vorher/nachher.
Die Manifestprüfung über alle 70 Bilder danach: 70/70 OK — an den Bildern hat
heute nichts geronnen, die Änderungen betreffen nur Host-Werkzeuge und Text.

## 2026-10-30 13:17 — Der letzte ungefakete Beobachtungskanal: der Einsammelblock selbst

Der Runner sammelt nach dem Flash die Belege über Telnet ein. Dieser Block war
den Tests der einzige Kanal, den nichts fakte — `tests/ref-enumeration` fakte
fastboot, system_profiler und ioreg, `tests/bisection` fakte fastboot, und die
Einschleusung in die Szene geschah über `PHONE=192.0.2.1`, damit das echte
Telefon nie hineintestet. Der Block selbst lief dadurch nur gegen das lebende
Orakel, und das sitzt seit dem Vormittag im Fastboot-Modus: bei `v0r` wäre es
sein erster Lauf am echten Gerät.

Deshalb jetzt Abschnitt 5c in `tests/bisection`: eine vorgebliche Shell auf
127.0.0.1, die das Orakel nachspielt — Banner **vor** dem ersten Echo, Echo
hinter jedem Befehl, Prompt danach, und bei einer fehlenden Datei die
Fehlermeldung statt nichts. Der Block wird aus dem Runner **herausgelöst** und
gegen diese Shell ausgeführt, nicht nachgebaut. Er läuft, seit er Port und
Wartezeit als Argumente nimmt (`${PHONE_PORT:-23}`/`${PHONE_WAIT:-4}`, Vorgabe
unverändert, auch die `nc`-Vorprüfung fragt jetzt denselben Port ab).

Elf Prüfungen, alle bestanden, 26 s für die ganze Datei: die decisive UDC-Zeile
landet in der Datei, ihr Echo nicht, kein Prompt darin, `telnet-identitaet.txt`
trägt die Antwort und **nicht** das Banner (die Greeting-Banner-Falle, hier als
Prüfung statt als Erzählung), und die leer antwortende `lsmod`-Datei bleibt leer
**und** wird als `ACHTUNG leer` gemeldet. Die Zahl der Prüfungen kommt aus einem
Zähler, nicht aus einem Text — die erste Fassung druckte eine ausgedachte `11`
und eine ausgedachte `0`, dieselbe Klasse wie die Fehlermeldung, die eine
Erwartung behauptet, die der Code nicht prüft.

Gegenbeweis geführt: denselben Gegenlauf mit dem **alten** Filter in der
Kratz-Kopie — Exit 1, und die beiden benannten Ausfälle sind genau die decisive
UDC-Zeile und die Bindungszeile. Nach dem Rückbau wieder Exit 0. Der Test
unterscheidet also in beide Richtungen. `tests/bisection`: 10 ok / 0 not ok /
Exit 0 (vorher 9).

## 2026-10-30 13:32 — Der Container stand 13 Minuten in einem ping, und der Buchstabe war schuld

Der Suite-Neulauf nach dem neuen Einsammel-Test wollte nicht enden. `docker exec`
zeigte im laufenden Container:

```
 3813  12:58  bash device/blueline/firstlight/run-flash-observe.sh …/fl-refpacked/firstlight.img 346a96da… 4
 3867  12:58  ping -c1 -W2000 192.0.2.1
```

`-W2000` war auf macOS immer gut: BSD-ping misst die Antwortfrist in
**Millisekunden**. iputils — der Container — misst sie in **Sekunden**, und
192.0.2.1 (TEST-NET-1, bewusst ohne Antwort) war damit ein Blocker von 33
Minuten pro Poll, in der Schleife mit vier Polls.

Gemessen statt Man-Page geglaubt, beide Seiten:

* iputils/alpine, `ping -c1 -W2000 192.0.2.1`: nach 6 s noch nicht beendet (von
  mir abgebrochen; im echten Lauf 13 min), `ping -c1 -W 2 -w 3 …`: **exit 1 nach
  2 s**.
* macOS, vier Polls mit `-W2000` in einem kompletten `tests/bisection` von 26 s:
  dort blockierte kein Poll auch nur ansatzweise sekundenlang.
* Nebenbefund, weil er die Verführung zeigt: `ping -c1 -W 1 8.8.8.8` bekam auf
  macOS eine Antwort trotz gemessenem Hinweg von 9,9–19,7 ms. Die macOS-Zahl ist
  also keine scharfe Antwortfrist, und ich behaupte ihre Einheit auf
  Antwortebene nicht — belegt ist nur, dass 2000 dort nicht blockiert.

Der Runner setzt die Frist jetzt nach `uname -s`: `Darwin → -W 1500`, sonst
`-W 2 -w 3` (Einzelantwort und Gesamtfrist). Neu ist Abschnitt 5d in
`tests/bisection`: ein Fake-`ping` zeichnet die Argumente auf, und die Prüfung
muss dieselbe Zeile je Plattform **verschieden** beurteilen — `-W2000` ist auf
macOS legitim und auf iputils der gemessene Hänger. Ohne diesen Gegenbeweis wäre
die Zahl nur eine Erwartung, die ich mir ausgedacht habe. Der Fake zeichnet auch
auf, **dass** überhaupt gepingelt wurde: eine Prüfung, die ins Leere läuft, ist
dieselbe Fehlerklasse wie ein Prüfstein ohne Datei.

`tests/bisection`: 11 ok / 0 not ok / Exit 0 (33 s, vorher 10 ok/27 s).
Nebenbei die Frage, ob meine Testläufe dem Telefon etwas geschrieben haben, als
es im Fastboot-Modus hing: Nein, und der Beweis ist die Zeichenkette nicht im
Kopf, sondern im Aufrufprotokoll — die Runner-Zeile 22 stellt platform-tools
nur voran, **wenn kein fastboot gefunden wird**, und der Fake gewinnt dadurch;
derselbe Fake meldet `flash boot_a` erhalten (die Prüfung darauf ist grün).

## 2026-10-30 13:39 — Dieselbe Suite ohne Bild-Mount, und warum das kein Skip wurde

Dieselbe Suite, diesmal ohne die Bild-Einhängungen (mein eigener Aufruf hatte
`$HOME` leer übergeben, also drei leere `-v`-Argumente; der Log zeigte
`SUITE: ok=104 (davon skip=3) not-ok=1 exit=1`), meldete zwei Ausfälle: meinen
neuen ping-Abschnitt und einen **älteren**, `Runner bei falschem Hash ohne Grund
im Protokoll`. Die Ursache ist in beiden Fällen dieselbe und sitzt nicht im
Runner: ohne Bild bricht der Runner vorher mit `Bild fehlt` ab, und die Prüfung
verlangt einen Hash-Vergleich, den es dann nie gab.

Beides ist kein Grund zu skippen, weil die geprüfte Eigenschaft — *der Runner
vergleicht den mitgegebenen Hash, bevor er fastboot ruft* — an keinem Byte des
Bildinhalts hängt. Also erzeugen sich diese Abschnitte jetzt selbst ein Bild
(ANDROID-Merkmal, 64 KiB, Hash gemessen statt geraten) und laufen überall. Ein
Skip wäre die halbe Antwort gewesen: auf einer Maschine ohne Artefakt bliebe
genau der Teil des Läufers ungeprüft, der sonst immer mitläuft — dieselbe
Klasse wie ein Prüfstein, der ins Leere läuft und Erfolg meldet.

Belege: mit Bildern 11 ok / 0 not ok / Exit 0; ohne Bilder (Kopie der Datei,
`/private/tmp`-Kandidaten umgelenkt, `WS`/`IMGD` ins Leere) 10 ok / 0 not ok /
3 skip / Exit 0, und die drei Skips sind ausschließlich die Abschnitte, die das
ausgelieferte Bild wirklich lesen (patch-v0r, verify-v0r, Bild-A-Vergleich).
Eine eigene Korrektur in derselben Reihe: die vier Ueberschriften oben trugen jetzt die gemessenen Zeiten ihrer Commits (13:12, 13:17, 13:32, 13:39, aus `git log --date=format:%H:%M`). Vorher stand dort 06:30 bis 08:1x — das war die Uhr aus der Kontext-Zusammenfassung, nicht die des Rechners, und sie lag um sechs Stunden daneben. Ein Protokoll, dessen Zeitstempel aus einer Nacherzählung stammen, ist für spätere Kausalbehauptungen unbrauchbar: `date` und Commit-Zeit sind die einzige Quelle, und die älteren Überschriften (04:2x zu Commit 04:30) zeigen, dass es vorher richtig war.

Nebenbefund zur Ordnung: `fastboot` und `$HOME` sind in der Hintergrund-Shell
dieses Agents nicht gesetzt — Mounts und Telefonabfragen laufen jetzt mit
absoluten Pfaden, weil ein leeres `$HOME` drei `-v`-Argumente still zu leeren
Strings macht.

## Nachtrag 15:34 — RESTART2 ist belegt (Rueckweg gefuenkelt)
- Restart2 noetig, weil busybox 'reboot bootloader' das Kommando verwirft
  (RESTART ohne Argument). Eigener Aufruf: reboot(0xfee1dead,0x28121969,
  LINUX_REBOOT_CMD_RESTART2=0xa1b2c3d4,"bootloader"). Erste Fassung hatte
  0xe1212120 — keine Kommandokonstante, reboot() gab EINVAL, kein Neustart.
- Der laufende Device-Baum (Referenz-DTB + Overlay dtbo_b) enthaelt
  pon@800/mode-bootloader und -mode-recovery; CONFIG_POWER_RESET_QCOM_PON=y.
  Das Referenz-DTB allein hat keinen reboot-mode — das Overlay bringt ihn ein.
- Messung 15:34:09: /tmp/restart2 bootloader (SHA 06e4de89… am Geraet geprueft)
  -> t=7s Product 0x4EE0 (Fastboot), Telnet zu, slot-retry-count:b bleibt 1
  (kein Slot-Boot-Zaehler verbraucht) = direkt in den Bootloader, nicht
  'normaler Neustart, der zufaellig in Fastboot faellt'.
- Upload-Kanal nebenbei geloest: unquotierte Heredocs ($@<<EOM) verfilschen
  die Base64-Bytes; Stueck-fuer-Stueck-printf mit SHA je Stueck (74/74 gleich)
  ist der zuverlaessige Weg. Skript: firstlight/restart2-robust-testen.py.

## Nachtrag 18:15 — Der Lesekanal war die ganze Zeit heil, unser Bild fand seine Partition nicht

Vier dunkle Nachmittage lang war die Frage, was unser Kernel tut, nachdem er
vom USB-Baum verschwindet. Zwei Messungen von heute nachmittag entscheiden sie,
beide maschinell, keine gefolgert.

**1. Das Ende von boot_a ist beschreibbar und Liesbar (18:07).** An der
laufenden Referenz, dieselbe Partition, derselbe Versatz, den unsere `logflush`
benutzt: `blockdev --getsize64` = 67108864, `--getro` = 0,
`dd bs=131072 seek=504 conv=notrunc,fsync` = rc 0, und der Marker steht beim
Lesen bei 66060288 Byte da (`OMAMOBILE-SCHREIBTEST-1101`). Protokoll:
`firstlight/evidence/boot-a-schreibtest-2026-11-01.md`.

**2. Unser Bild hat dort nie geschrieben.** Nach zwei eigenen Laeufen (17:41,
18:03) war der Bereich leer: `grep -c OMAMOBILE-LOG` = 0. Der Grund sitzt in
`find_bootdev`: sie kennt nur `/dev/disk/by-partlabel/boot_a` und
`/dev/disk/by-name/boot_a`. Beide Namen legt ein Uevent-Daemon an — die
Referenz hat ihn (ueber ihren Symlink lief gerade der Schreibtest), unser
first-light laeuft ohne jeden Daemon im Initramfs. `find_bootdev` gab 1,
`logflush` kehrte ohne eine Zeile zurueck, und der Log-Beutel mit steps.log,
UDC-Liste, Haengliste und dmesg lag nie auf der Partition. Der Kanal war seit
seinem ersten Bau unbrauchbar, und keine Anwesenheitspruefung sah es, weil der
Aufruf selbst korrekt aussah.

**3. v0ac (sha256 0c03240a91c2b143122c9c1c1b99089e6dcbc98ad3389f0da8931eb9a94e84e6)
sucht selbst.** Der Kernel haelt denselben Inhalt, aus dem ueventd den Symlink
baut: `/sys/block/<disk>/<part>/uevent` traegt `PARTNAME=boot_a`,
`<part>/dev` traegt major:minor. Die beiden bekannten Pfade bleiben erste
Wahl, danach die eigene Suche, und ein fehlender Knoten wird mit mknod
angelegt. Jede Entscheidung geht als Mark auf das Panel, denn nach einem
eigenen Lauf ist das Panel der einzige Leser.

**4. Der Selbst-Rueckweg ist belegt, und er ist fuer den Mac unsichtbar.**
v0ab kam 17:52:30 bei t=185 s von selbst nach Fastboot zurueck, ohne
Tastenaktion — `restart2 bootloader` wirkt. Die fruehere Erfahrung "nach
unserem Lauf sieht der Mac nichts" erklaerte sich anders als vermutet: ABOOT
hatte jedes Mal das alte Bild in boot_a gestartet, das in `while :; do sleep
60; done` endet und nie zurueckkehrt (Retry a fiel dabei 1 -> 0,
`slot-unbootable:a` stellte sich auf ja). Der Rueckweg ist also noetig, aber
er ist nicht zuverlaessig sichtbar: um 17:52:30 sah der Mac die Rueckkehr als
`0x4EE0`, zwischen 16:55 und 17:20 sah er sie sieben Minuten lang nicht.
Zwei Messungen desselben Vorgangs, zwei Ausgaenge — eine Messung, die den
Sichtbarkeitsfall braucht, taugt nicht als Beweis, und die Tastenaktion bleibt
der Ausgang, wenn das Bild schweigt.

**5. dtbo ist Teil der Bootkette.** Mit leerem `dtbo_a` starb jedes Bild — die
Referenz und die Stock-Factory ebenso — nach ~13 s; mit Factory-dtbo ueberlebt
es (72 s und 76 s Telnet). `dtbo_a` traegt seit 16:31 das Factory-Bild
(`ff7bd6da…`) und wird gehalten. Vor jedem Versuch `--set-active=b` pruefen:
mit `slot-unbootable:a: ja` / `retry a: 0` brachte die Referenz zweimal
hintereinander kein Telnet innerhalb 200 s zustande, einmal nach
`--set-active=b` kam es bei 78 s.

**Regel aus dem Zahlenspur-Fehler von heute:** der v0ac-Umbau forderte zwei
neue Schleifenkoepfe und fand einen — die Zahl stand im Kopf. Jetzt stehen die
gemessenen Differenzen im Umbau (ein Kopf, ein `for`, ein `mknod`, ein
`grep -q`, drei Marks, 20 Zeilen, Klammerbilanz dicht), gemessen mit
`scratch/misse-v0ac-spur.py`, und das eingerueckte `done` wird ueber den
Zeileninhalt gezaehlt, nicht ueber die Spalte.

**Suite-Stand:** 145 ok (davon skip=4), 0 not-ok, Exit 0, frisch nach v0ac und
nach allen Skript-Aenderungen (TAP-Abschrieb `scratch/tap-v0ac.txt`).
Blockwart 12/0/0.


---

## Nachtrag 19 (2026-11-01, 20:45): das eigene Bild gibt eine Shell — und zwei Wurzeln, die alles Frühere erklären

### Meilenstein

Erstes eigenes Bild, das im eigenen Lauf eine erreichbare Shell gibt. v0ae
(sha256 `0d3b7fc6…`) aus dem RAM gestartet, Telnet auf 172.16.42.1:23 offen ab
**t=24 s** (20:13:19 gelesen) und im zweiten Lauf offen von **t=26 s bis t=360 s**
(66 Proben, keine Lücke). Protokolle:
`firstlight/evidence/eigene-shell-2026-11-01.md`,
`firstlight/evidence/v0ae-durchgang-2026-11-01.md`,
`firstlight/evidence/abgriff/` (18 Dateien, 314 951 B, Manifest mit sha256 je Datei).

Aus dem Steps.log desselben Laufs, alles zwischen 5 s und 6 s:

    [5s] gadget-module-dir gefunden
    [6s] modul libcomposite.ko geladen   (und u_ether, usb_f_ncm, u_serial, usb_f_acm)
    [6s] udc nach 0 runden gefunden: a600000.usb, uptime 6.14s
    [6s] UDC steht auf: a600000.usb
    [6s] ifconfig usb0 172.16.42.1
    [6s] boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
    [6s] raw log channel live on /dev/sda11

Aus der Shell desselben Laufs: `/sys/class/udc` = `a600000.usb`, `state`
= `configured`, Funktionen `acm.GS0` und `ncm.usb0`, `usb0` mit 172.16.42.1,
`grep -c nonexistent /run/steps.log` = 0, `/proc/device-tree/compatible` =
`google,blueline`, `qcom,sdm845`, dmesg ohne `ufshcd`- oder `abr`-Fehler.

Damit ist die älteste offene Frage des Projekts beantwortet — der Satz von
2026-10-29, „USB peripheral on this handset + this Mac has never been observed
with ANY mainline image", ist **falsifiziert**: ein bindendes Gadget wurde
gesehen, an genau diesem Mac, über denselben Hub. Alle „TOT"-Zeilen, die auf
einem fehlenden NCM beruhten, haben die Gadget-Bindung gemessen, nicht den
Kernel — wie die Durchsicht damals vermutete.

### Wurzel #9 — der Log-Kanal war seit v0p tot, weil die Partition dem Platten-rw folgt

    gemessen 19:40:50 am laufenden Gerät:
      blockdev --setro /dev/sda; blockdev --setrw /dev/sda11
      -> sda=1 sda11=1   dd: "Operation not permitted", 0 Bytes
      blockdev --setrw /dev/sda
      -> dd rc=0, 24 Bytes, Marker lesbar

Unsere `storage_guard` setzt Platte UND Partitionen auf ro; `logflush` drehte
nur die Partition zurück, und `2>/dev/null` an der dd verschluckte den Fehler.
Seit v0p hat kein Bild je nach boot_a geschrieben — der Beweis: der Schreibtest-
Marker von 18:07 lag um 19:35 unverändert auf 66060288, obwohl v0ac 334 s
gelaufen war. Fix in v0ad: Platte rw vor dem dd, dd-Text eingefangen,
`schreib_rc=` im Protokoll. Beweise: `evidence/ro-kausalitaet-2026-11-01.md`,
`evidence/ro-wurzel-und-sechs-starts-2026-11-01.md`.

### Wurzel #10 — dem Initramfs-Archiv fehlten die Elternordner der Module

Seit v0p lagen sechs `.ko` im Archiv (Byte-identisch zur Quelle, ELF, richtige
Mode, richtiger vermagic, alle Prüfer grün), aber der letzte Verzeichniseintrag
war `usr/lib`; `usr/lib/modules/<version>/…/gadget/function` fehlte als
Eintrag. `unpack_to_rootfs()` legt fehlende Elternordner nicht an, es verwirft
die Datei ohne Meldung. Folge im Lauf: kein Modul, `insmod` Exit 254,
libcomposite fehlt, configfs-Mount schlägt fehl (USB_CONFIGFS=m), und acht
Bind-Runden pro Start laufen auf `can't create …/g1/UDC: nonexistent directory`
— genau der Text, den der Besitzer am Panel las und der einen Tag lang für einen
Log-Flush-Fehler gehalten wurde. Fix in v0ae: sieben Ordnereintraege vor die
erste `.ko`, plus Prüfung, dass für JEDEN Dateieintrag der Elternordner im
Archiv steht — dieselbe Prüfung ein zweites Mal auf das aus der fertigen .img
zurückgelesene Archiv. Beweise: `evidence/erster-eigener-stepslog-2026-11-01.md`,
`evidence/boot-a-beutel-2026-11-01.md`.

### Wurzel #11 (Korrelation gemessen, Mechanik noch nicht belegt) — der aktive Slot entscheidet, ob ein RAM-Start überlebt

    20:33  current-slot:b  unbootable:b:yes  retry b:0  retry a:3
    20:34  fastboot boot v0ae  -> nach ~25 s zurück im Fastboot, en8 nie aktiv
    20:40  fastboot boot ref/boot.img (ed2c225f, den ganzen Tag funktionierend)
           -> derselbe Tod. Es lag also nicht an unserem Bild.
    20:45  fastboot --set-active=a, danach dasselbe v0ae -> Shell offen,voller Abgriff

Zwei Facts dazu: die Todes-Uhr ist unsere eigene. `initramfs/init:70` tut im
Aufgabe-Zweig `echo c > /proc/sysrq-trigger`, ABOOTs Kommandozeile trägt
`panic=60`, also: Crash bei t=181 s (pstore: `Kernel panic - not syncing:
sysrq triggered crash`, `Comm: init`), Neustart 60 s später, ABOOT findet keinen
startfähigen Slot und parkt in Fastboot — zusammen ~240 s, passend zur
Beobachtung. Und: die Startkommandozeile des toten Laufs trägt
`slot_suffix=_a`, `bootreason=watchdog`, die des lebenden `slot_suffix=_b`,
`dtbo_idx=8`, `bootreason=reboot,bootloader`. Welche dtbo-/vbmeta-Menge ABOOT zu
einem RAM-Start dazunimmt, hängt also an_slot; eine der beiden Mengen lässt den
USB-Controller (`a600000.usb`) nicht erscheinen, unsere Init crashed daraufhin
bei 181 s. Belegen lässt das in zwei Zyklen: `--set-active=b` muss den Tod
zurückbringen, `--set-active=a` ihn wieder nehmen.

### M1-Kriterien, abgelesen statt vermutet

| Gate | Stand | Fehlendes |
|---|---|---|
| M1.0 ankommen, entsperren, erfassen | erledigt | — |
| M1.1 first-light bauen (nur Host) | erledigt 2026-10-27 | — |
| M1.2 Start aus dem RAM, keine Writes | **erfüllt bis auf eine Zeile** | `uname` nennt den Distro-Build `#5-postmarketos-qcom-sdm845` (Kernel absichtlich der Referenz-kernel, unser Teil sind Init und Initramfs); `compatible` = `google,blueline` ✓; alle UFS-Ganzen Platten ro ✓; kein `ufshcd`/`abr` in dmesg ✓. Offen: „the simple-framebuffer console is the screen we are reading" — das kann nur ein Mensch ablesen. |
| M1.3 LUN-Karte und Kalibrier-Backups | **erledigt 2026-11-02** | LUN-Karte gemessen (`evidence/abgriff/storage-ro.txt`: sda 63,9 GB Haupt-LUN, sdb 4 MiB, sdc 4 MiB, sdd 8 MiB, sde 32 MiB, sdf 72 MiB). Kalibrier-Abgriff 2026-11-01: 13 Bereiche, 56 266 752 B, **12 mit sha256 beglaubigt** (persist `56204d37…`, dtbo_a/b `ff7bd6da…`, boot_a vor Write `0478f8db…`, boot_b `973ead30…`, modemst1/2, misc, frp, devinfo, vbmeta_a/b, beide GPT-Kopfsätze); das 13. Loch ist der 24-Byte-Endblock der gepackten Datei, kein LUN-Defekt. Zweitkopie auf der NAS, 24/24 sha Rücklese OK. |
| M1.4 GPT vor dem ersten Slot-Flag-Write | **erfüllt 2026-11-02** | GPT-Audit `pruefe-gpt.py`: 47 Prüfpunkte, 0 Fehler, jetzt als `tests/gpt-audit` in der Suite. Sektorabstand 4096 B auf allen sechs LUNs, Kopf- und Sicherungskopf-CRC stimmen, Kopf und Sicherung gehören zusammen (GUID gleich, mein/sicher vertauscht), Geometrie pro Satz deckungsgleich, Referenz-CRCs der belegten Sätze stehen in Nachtrag 21 (LUN a `e9277d82`, b `89f95d74`, c `d6645fd8`, d `1cdb565e`, f `8e2a8772`). ABOOT legt die UEFI-Satz-CRC **nicht** an — der Prüfer rechnet eigene. Offen und notiert: `boot_a`/`boot_b` unterscheiden sich in den Attributbits zwischen Kopf und Sicherung (Nachtrag 21). Dazu aus Flash gestartet: boot_a trägt v0af, Port 23 nach 28 s. |
| M1.5 Slot B beschreiben, Root auf userdata rw | **als nächstes offen** | Rootfs auf userdata `rw`, Rest bleibt ro. Bisher läuft alles als RAM-Bild oder Flash-Bild mit Initramfs-Root; userdata ist von uns nie angefasst. Vor dem ersten Write: Platte rw (Wurzel #9), Sicherung gegen Manifest prüfen, und ein Satz, was geschrieben wird und woran Erfolg erkennbar ist. |
| M1.6 Slot B bootbar markieren | offen, und blockiert | Aktuell `unbootable:b:yes`, `retry b:0`. Seit M1.4 ist a die Startquelle (`retry a` wird in jedem Zyklus auf 3 gesetzt, weil unser Linux nie `successful` meldet) und b nur noch Rettungsquelle für `fastboot boot`; die Inhalte von b sind unangetastet. |
| M1.7 durchstarten bleiben | offen | systemd/Sitzung, dazu die Display-Lücke: dmesg meldet `DSI PLL(0) lock failed` und fehlende `qcom/a630_sqe.fw` — Display und GPU-Firmware sind die nächsten echten Baustellen nach M1.5. |

### Eigenfehler, die dieser Abend gezeigt hat

1. `mark 'text $(befehl)'` in einfachen Anführungszeichen druckt seinen
   Befehl, nicht seinen Wert — zwei Instrumente von v0ad/v0ae waren blind, ohne
   blind auszusehen. In der nächsten Fassung doppelt zitieren und an einem Mark
   mit bekanntem Wert prüfen.
2. `fastboot boot` gegen ein lebendes Telefon wird verschluckt: 20:16 meldete
   der Client „Finished", das Telefon bootete nie. Erst auf Fastboot-Sicht
   warten, dann starten.
3. Ein Abgreifer ohne Rahmenprüfung ist ein Gerücht: `greife-beweise.py` holt
   jetzt jede Datei zwischen `@@ANFANG`/`@@ENDE` mit Bytezahl des Telefons und
   sha256. Die verschachtelte `$( … | wc -c)`-Größenabfrage zerlegt sich bei
   mehrzeiligen Befehlen selbst (sieben Artefakte verrutscht) — zweiter
   Durchgang, Größe separat erfragen.
4. Die Selbst-Rückweg-Uhr (372 s) nimmt die Shell weg, während man noch dran
   sitzt. Vorgesehene Änderung: Rückkehr nur noch nach Funkstille (fünf Minuten
   ohne Verbindung oder ohne `/tmp/halt`), obere Grenze bleibt.

## Nachtrag 20 — 2026-11-02, kurz nach Mitternacht: Sicherung an zweitem Ort, Rückweg neu gestellt, und was als Nächstes geschrieben wird

Claude hat vor dem ersten Write auf `boot_a` vier Punkte verlangt. Alle vier sind
gemessen, nicht versprochen.

**1) Die Sicherungen liegen nicht mehr nur auf dem Mac.** 24 Dateien, 190 MB, nach
`//gregor@DXP4800-ACC4/hermes-sicherungen/blueline-2026-11-01` (UGREEN, 9 TiB,
7,8 TiB frei) kopiert, zusammen mit allen Manifesten und der LUN-Karte. Die
Gegenseite hat nachgezählt: `sha256 -c` auf der NAS liest **24 von 24 Dateien OK**
(`sha256-kontrolle.txt` dort und hier identisch). Erst danach ist geflasht worden.

**2) Der Rückweg ist nicht mehr Slot b.** Seit 20:33 steht `unbootable:b:yes` bei
`retry b:0`, und um 20:45 starb sogar die Referenz im RAM nach 60 s — Slot b ist
als Bootquelle unzuverlässig geworden, auch wenn seine Inhalte unangetastet liegen
(Nachgemessen um 00:20, an der frischen Sicherung von `boot_b`: Die Partition ist 64 MiB, ihr Inhalt ist **nicht** bytegleich mit `pmos-ref-build/ref/boot.img` — die erste Abweichung liegt bei Byte 44, also im Headerfeld, aber die folgenden 28 725 248 B (Kernel, Ramdisk, Anhang) sind **bytegleich**. Die Rettungsinhalte liegen also unveraendert in Slot b, nur die Ganzen-Partition-sha (`973ead30…`) war eine andere Behauptung, als die Datei haelt. `dtbo_b` traegt den Factory-Inhalt `ff7bd6da…`, `vbmeta_a` und `vbmeta_b` sind identisch `227eb064…`. Die volle `boot_b` ist jetzt erstmals gesichert, an beiden Orten.
Verlässlich und mehrfach belegt ist stattdessen: `fastboot boot
images/fl-v0af/firstlight.img` (RAM, schreibt nichts, hält die Leitung offen und
kehrt allein in den Fastboot-Bildschirm zurück) und, wenn gar nichts mehr antwortet,
Power + Leiser für ~20 s. Kein Plan ab hier stützt sich darauf, dass ABOOT von Slot b
bootet; M1.6 (Slot b bootbar machen) ist davon ausdrücklich unberührt und bleibt offen.

**3) Was geschrieben wird, in einem Satz:** Auf `boot_a` — Partition 11 von LUN a,
64 MiB — wird bytegenau `images/fl-v0af/firstlight.img` (sha `f097ef0f…`) geschrieben,
und dieses Bild trägt selbst die Funkstille-Rückkehr: es hält die Shell, solange eine
Verbindung steht, und kehrt nach fünf Minuten Funkstille von allein in den
Fastboot-Bildschirm zurück (Obergrenze 60 Minuten), die alte Endlospark-Falle ist also
nicht wieder eingebaut. Erfolg gilt als erreicht, wenn nach `fastboot reboot` der Port
23 binnen 300 s offen steht und der gelesene Kopf von `boot_a` die sha des Bildes
meldet; als Misserfolg gilt ein zu bleibender Port — dann legt `fastboot boot` der
Referenz das Telefon wieder hin, und `--set-active=a` stellt den Zähler neu.

**4) Das wiederholte Loch ist nicht die Platte, sondern unser eigener Sammler.**
LUN e misst 65 536 Sektoren zu 512 B (32 MiB) — der gelesene Kopf braucht 64 Sektoren
bei 0, das Ende liegt bei 65 472, beide Adressen also weit innerhalb der Platte, und
ein 4K-Sektorbetrieb wäre beim Ende (32 KiB, erfolgreich gelesen) aufgefallen. Was
fehlt, ist der *letzte, winzige* Block: Die gepackte Kopfdatei ist 4 120 B, Block 0
liefert 4 096 B, Block 1 die letzten 24 B — und die einzigen Bereiche, die im Manifest
als Loch stehen, sind genau die mit einem Endblock unter hundert Byte. Zum Vergleich:
`modemst1` endet bei 4 013 B, `persist` bei 727 B, beide dicht. Ein Loch, das sich
lückenlos wiederholt, ist hier kein LUN-Defekt, sondern ein Rahmenproblem bei
Miniaturblöcken; die vorgesehene Änderung legt die Payload zwischen zwei gedruckte
Markierungen, statt auf Zeilenform zu vertrauen.


## Nachtrag 21 (2026-11-02, nach M1.4): die Partitionstabelle in Zahlen, und ein Zähler, der sonst im Stillen läuft

Zwei Aufträge aus dem Check-in, dann M1.4 zu Ende. Alles ohne Telefon gemessen,
das Telefon lag die ganze Zeit im Fastboot und ist unangetastet.

**Der Zähler, der im Stillen läuft.** Unser Linux markiert Slot a nie als
`successful` — diesen Schalter legt bei Android ein System am Ende eines sauberen
Starts um, und keins davon läuft hier. Also zieht jeder Start aus dem Flash
`slot-retry-count:a` um eins ab, und nach drei Starts ist Slot a `unbootable`;
das Telefon landet dann scheinbar grundlos im Fastboot. Genau die Formulierungen,
die vor M1.4 zur slot-b-Falle führten. `starte-abgriff.py` setzt jetzt in
**jedem** Zyklus `--set-active=a` und schreibt vorher und nachher fünf Klemmen ab
(`current-slot`, `slot-retry-count:a`, `slot-retry-count:b`, `slot-successful:a`,
`slot-successful:b`) — vorher passierte das Setzen nur, wenn b aktiv vorgefunden
wurde. Beleg aus M1.4: vor dem Setzen `retry a = 0`, danach `3`.

**Die Leser in der Suite.** `tests/leser-harness` ruft `pruefe-leser.py` (18
Prüfpunkte gegen eine nachgebaute Telefon-Shell: Anker, Payload-Abtrennung,
Rahmen, und seit heute die Cursor-Auskunft) und gibt seinen Zahlensatz als
TAP-Zeile weiter; `tests/gpt-audit` tut dasselbe für das GPT-Audit und rechnet
die Header-CRCs **zweimal** — einmal im Prüfer, einmal hier über die Auszüge auf
der Platte, damit ein Harness sich nicht selbst abnickt. Beide hängen in der
ausdrücklichen Liste von `tests/all` (ein neuer Ordner-Eintrag wird geparst, aber
nicht gerannt, das stand schonmal da). Lokal: 18/0 und 47/0 plus 16 eigene
Kopfprüfungen. Die Ad-hoc-Fußnote fällt damit weg.

### Das GPT-Audit (M1.4-Abschluss, `pruefe-gpt.py`, 47 Prüfpunkte, 0 Fehler)

Grundlage sind die Auszüge vom 2026-11-01 (64 Sektoren Kopf und 64 Sektoren Ende
je UFS-LUN), jetzt unter `evidence/gpt/` im Baum — 352 KiB, keine Bilddatei.
Gemessen, nicht aus dem Handbuch:

* **Sektorabstand 4096 B auf allen sechs LUNs.** Header 92 B, Revision 1.0.
* **Kopf-CRC und Sicherungskopf-CRC stimmen** über alle fünf erreichbaren Köpfe
  und alle sechs Sicherungsköpfe (LUN e: Kopf-Auszug fehlt, 24-Byte-Endblock).
* **Kopf und Sicherungskopf gehören zusammen**: gleiche Disk-GUID, `mein`/`sicher`
  vertauscht. Die Tabelle existiert also zweifach und inhaltlich gleich.
* **Feldabstand am Kopfende weicht von UEFI ab.** An Offset 80 sitzt im Kopf die
  **Zahl der belegten Sätze** (LUN a 21, b 3, c 3, d 32, f 16), im Sicherungskopf
  eine Null; die von UEFI verlangte CRC32 der Eintragssätze steht **an keiner
  Stelle** der Auszüge — ABOOT legt sie nicht an, `gdisk` hätte nichts zu prüfen.
  Deshalb rechnet der Prüfer eine **eigene Referenz-CRC über die belegten Sätze**
  und gibt sie aus. Das ist der Fingerabdruck, mit dem jeder künftige
  Schreibvorgang verglichen wird:

  | LUN | Sätze | Kapazität | Referenz-CRC | erster / letzter Satz |
  |---|---|---|---|---|
  | a | 21 | 128 | `e9277d82` | apdp_a … vendor_b (enthält userdata, misc, frp) |
  | b | 3 | 128 | `89f95d74` | xbl_a, xbl_config_a, last_parti |
  | c | 3 | 128 | `d6645fd8` | xbl_b, xbl_config_b, last_parti |
  | d | 6 | 128 | `1cdb565e` | ALIGN_TO_128K_1 … uefivar |
  | e | — | — | fehlt | Kopf-Auszug unvollständig |
  | f | 15 | 128 | `8e2a8772` | ALIGN_TO_128K_2 … toolsfv |

* **Zwei selbst eingebaute Feldfehler, beide jetzt im Text festgehalten:** Satzweite und
  Satzanzahl sind keine Halbworte (ich las `128` und `2658147757`), und der
  Partitionsname sitzt ab Satz-Offset **56**, nicht 72 (16+16+8+8+8). Wer das
  nächste Mal Namen ins Leere liest, sucht an der richtigen Stelle.
* **Geometrie-Regel:** Kopf- und Sicherungsfeld müssen pro Partitionsname in
  LBA-Bereich und Typ übereinstimmen — für alle 21/3/3/6/15 Sätze gegeben. Der
  rohe 16-KiB-Vergleich taugt nicht als Beweis, weil ABOOT das Sicherungsfeld
  sektorweise mit demselben Muster füllt (bei LUN b erschien der Dreier-Block
  zwölfmal); ein Rohvergleich wäre ein Fehlalarm.

**Der offene Befund.** Genau zwei Sätze unterscheiden Kopf von Sicherung, und
zwar nur in den Hersteller-Attributbits (Satz-Offset 48, keine Geometrie):

| Satz | Kopf | Sicherung |
|---|---|---|
| `boot_a` | `0x0070000000000000` | `0x0570000000000000` |
| `boot_b` | `0x0082000000000000` | `0x0020000000000000` |

Alle übrigen 19 Sätze der LUN a sind bytegleich. Aufgenommen am 2026-11-01, also
**vor** unserem `--set-active=a` — die Abweichung ist nicht von uns gemacht.
Zwei Lesarten: ABOOT schreibt beim Slot-Wechsel nur das Kopffeld, oder die
Sicherung ist seit einem früheren Factory-Write alt. Entscheidbar ist das nur am
Gerät, und zwar billig: im nächsten Fenster beide Felder von `boot_a`/`boot_b`
ablesen, einmal `--set-active=b` und zurück, und schauen, welches Feld sich bewegt.
Bis das entschieden ist, gilt für jedes Schreiben: **die Geometrie ist die
Verpflichtung, die Attributbits sind eine Beobachtung** — und nach jedem
Schreibvorgang werden beide Felder neu abgegriffen und gegen die Referenz-CRCs
oben gehalten.

## Nachtrag 22 (2026-11-02, 16:15–17:2x): M1.5 — die Wurzel will auf userdata, aber die Partition gehört ABOOT

**Beleg vor dem Write (16:15, `evidence/vor-userdata/`, 20 Dateien).** `userdata`
= `/dev/sda21`, 51 GiB, LBA 2068480. Die Superblock-Region bei Offset 1024 ist
null, `mount -o ro` meldet `wrong fs type, bad superblock`, `unlocked: yes`. Auf
der Partition steht kein Dateisystem, also auch keine Nutzerdaten; ein 64-GB-
Backup gibt es nicht und wird nicht gebraucht.

**Bild.** Alpine-arm64-minirootfs in 1 GiB ext4, eigener `/init` mit
switch_root-Beleg und Funkstille-Rückweg. Bau im Container-eigenen Overlay
(`virtiofs` auf der Mac-Freigabe hat keine xattrs — `set_inode_xattr: No such file
or directory`), das fertige Bild auf die Freigabe. sha256 `c4e43c11fa66…`.

**Bild v0ag.** Suche über `/sys/block/sda/sdaN/start` (kein `by-partlabel` in
dieser Ramdisk), Sektor 16547840, Platte erst `--setrw`, dann die anderen
Partitionen einzeln zurück unter ro; die Wache bekommt ihre Ausnahme über
`/tmp/uddev`, weil ihr Hintergrund-Unterlauf die Variablen des Vaters nicht sieht.
Auf dem Telefon belegt: `partition=sda21 sektor=16547840` bei 6 s, Mountversuch
bei 167 s, dort `EXT4-fs (sda21): group descriptors corrupted`.

**Wurzel #15.** Der Kernel meldete den Block `58080576997508677`; little-endian
ist das `45 46 49 20 …` = „EFI ". Der Bytestellenvergleich Telefon gegen Mac-Bild:

| Offset | Telefon | Bild |
|---|---|---|
| 1024 | `00 00 01 00 00 00 04 00 33 33…` | gleich |
| 4096 | `45 46 49 20 50 41 52 54` („EFI PART") | `81 00 00 00 89 00 00 00` |
| 8192 | GUID-Bytes des alten Partitionssatzes | `02 80 00 00 02 80 01 00` |
| 65536 | `10 80 00 00 10 80 01 00` | gleich |

`81 00 00 00 89 00 00 00` ist der erste Gruppenbeschreiber (Block-Bitmap 129,
Inode-Bitmap 137). Bei 4096-Byte-LUN-Sektoren liegen GPT-Kopf (Sektor 1 = Offset
4096) und -sätze (ab 8192) genau in diesem Feld, und **ABOOT legt sie bei jedem
Start wieder hin**. Ein dichtes Sparse-Bild (262 144 DATA-Säcke, zurückgelesen,
sha gleich dem Rohbild) ändert daran nichts.

**Zwei Fehler vorher, beide behoben.** `fastboot flash userdata rootfs.ext4`
rechnet selbst um, meldet `Invalid sparse file format at header magic`, schickt
nur 9588 KB für 1 GiB und lässt Löcher (1024 und 65536 dicht, 4096/8192 nicht).
`-S 0` ändert daran nichts. Ein eigenes Sparse-Bild braucht die Magie `0xED26FF3A`
(auf dem Draht `3A FF 26 ED`) und einen 28-Byte-Kopf, dessen Größenfelder
`file_hdr_sz` und `chunk_hdr_sz` **u16** sind; als u32 gepackt lehnt fastboot ab.

**Folgerung und nächster Schnitt (v0ah).** Das Dateisystem darf nicht dort liegen,
wo das GPT liegt: Bild mit 1 MiB Null-Vorlauf (`rootfs-vorlauf.ext4`, sha
`0de3fd84e0fd…`, Superblock bei 1 MiB + 1024), Mount mit `offset=1024` (Einheit
1024-Byte-Blöcke), zweiter Versuch ohne Versatz als Messung im selben Zweig.

**Nebenbefund.** Ein Markentel aus dem laufenden Linux auf Offset 4096 schlägt mit
EPERM fehl, weil die Wache die Platte im Sekundentakt zurück auf ro legt —
Wurzel #9 bestätigt sich damit von der Gegenseite. Für Schreibversuche am
laufenden System muss die Wache zuerst aus.

## Nachtrag 23 (2026-11-02, 17:1x–17:5x): der Hänger hieß max-download-size

**Was die letzten Minuten wirklich gekostet hat, war nicht das Dateisystem,
sondern die Übertragung.** Der Abbruch des ersten Write-Zyklus ließ den Log
durchkommen:

    Sending sparse 'userdata' 1/5 (262141 KB)   OKAY [11.926s]
    Writing  'userdata'                         OKAY [ 0.443s]
    Sending sparse 'userdata' 2/5 (262141 KB)   …

`fastboot` zerlegt eine 1-GiB-Übertragung in **fünf Sitzungen** zu je
262 141 KB, begrenzt durch `max-download-size: 268435456`, und der client blieb
beim Übergang von Sitzung 1 auf Sitzung 2 stehen: Rechenzeit eingefroren
(5,06 s insgesamt, in 20 s keine Millisekunde dazu), das Telefon danach auf USB
sichtbar („Pixel 3"), aber gegenüber `fastboot devices` stumm.

**Zwischenbehauptung, die ich zurücknehme:** ich hatte die Sack-Für-Sack-Geometrie
(262 400 DATA-Säcke) als Ursache verdächtigt und auf 16-MiB-Brocken umgestellt —
die Umstellung war nie gelaufen. Das gepolsterte Bild (1 MiB + 1 GiB) ist kein
Vielfaches von 16 MiB, der Bauer lehnte es ab, und `python3 … | tail -4 && sh …`
meldete den Exit von `tail`. **Beide Hänger liefen auf demselben alten Bild.**
Lehre: nach jedem Schritt in einer Rohrleitung, die `tail` enthält, Zeitstempel
oder sha der Ausgabedatei prüfen.

**Fix.** `baue-sparse.py` setzt jetzt wie `img2simg` DONT_CARE für Nullserien:
117 441 332 B statt 1 077 939 240 B, 7 DATA-Brocken, 58 Löcher — **eine**
Sitzung. Round-trip gegen das Rohbild bleibt dich; weil ein DONT_CARE das Feld
nicht schreibt, belegt der Round-trip die DATA-Brocken, nicht das Schreiben der
Löcher (steht im Code, damit die Prüfung nicht führt).

**Zwei weitere kleine Fallen, beide behoben.** Der Frist-Wächter im
Write-Zyklus erbte den Standardausgang seines schlafenden Kindes und hielt damit
die Rohrleitung offen — der Prüfer hing 180 s genau daran; Frist jetzt übergebbar
und 900 s, weil 300 s einen 1-GiB-Write nicht tragen. Und die Endbedingung des
Bauers multiplizierte die *Zahl der Säcke* mit 4096, fand einen Widerspruch, wo
keiner war, und meldete Exit 1 bei dichtem Round-trip.

**Stand.** v0ah (sha256 `88706c1c…`, 677 Zeilen Init, Vorlauf-Mount
`offset=1024`) ist gebaut und ad-hoc geprüft: 16 Prüfpunkte, 0 Fehler — Umbau am
echten Archiv, ausgepackte Bild-Ramdisk, beide Begleitdateien, Trockenübung des
Write-Zyklus mit hörendem Fastboot und belegter Reihenfolge. Ausdrücklich nicht
Suite-Grün; die kanonische Suite (148 ok / 4 skip) erreicht diese Dateien nicht.
Telefon ist zurück im Fastboot, der Write läuft.


## Nachtrag 24 (2026-11-02, 22:4x–23:3x): offset= ist in Byte, und die GPT-These kriegt einen Beweis

**Der Check-in von Claude hatte in einem Punkt recht, in einem zweiten war die Arbeit
schon erledigt, und in einem dritten hatte er einen unbelegten Satz erwischt.**

1. *Einheit.* `misst-offset-einheit.sh` legt ein ext4 bei 1 MiB in ein Loop-Blockgerät
   und mountet im arm64-Container — mit **dem** `mount` aus dem ausgelieferten Archiv
   (util-linux 2.41.6), nicht nur mit dem des Containers (2.42.4):

       offset=1048576 -> ERFOLG (lost+found)
       offset=1024    -> FEHLER rc=32 bad superblock
       offset=2048    -> FEHLER rc=32 bad superblock

   `offset=` ist in **Byte**. v0ah hätte damit 1 KiB statt 1 MiB gelesen — ein zweiter,
   von der GPT-Frage unabhängiger Grund für den Fehlschlag. v0ai (`11afeb3b…`) mountet
   1048576, und kein `2>/dev/null` mehr: der Wortlaut geht in `$udfehler` und damit in
   die Marke. Erfolg ist, dass `/ud` in `/proc/mounts` steht, nicht dass der Mount
   schweigt. Nebenbefund: `mount -o offset=` richtet das Loop selbst ein; der Kernel
   hat `CONFIG_BLK_DEV_LOOP=y`, MIN_COUNT=8, kein Modul und kein `losetup` nötig.
   Und die 79-Zeichen-Grenze gilt dem Telnet-Zeileneditor, nicht dem Init: der
   ausgelieferte Init enthält Zeilen bis 389 Zeichen und ist damit gebootet.

2. *Freigabe der Partition.* War schon vor dem Check-in so, jetzt aber mit Zeilenbeleg:
   die Wache liest `/tmp/uddev` und überspringt beim gesetzten Wert die
   userdata-Partition **und** `/dev/sda`, alles andere bleibt einzeln unter ro
   (init 536–552).

3. *„ABOOT legt sein GPT hin" ist eine These.* Belegt ist nur der Fund nach einem
   Write — und der lief mit fastboots eigener Umrechnung, die 4096 und 8192 als
   Löcher ließ. Der Unterscheidungsschritt heißt `marker-4mib.bin` (4 194 304 B,
   sha256 `39cb098d…`, **ein** DATA-Sack ohne jedes Loch, also wird wirklich jedes
   Feld zwischen 0 und 4 MiB geschrieben) mit `MK0000-`, `MK4096-` und `MK8192-`
   Zeilen; `beweise-marker.py` liest die Felder (13 Belege, längster Befehl 71
   Zeichen). Sind sie nach dem nächsten Boot weg, kann das nicht am Write gelegen
   haben: bleiben sie, war die These falsch und der Vorlauf überflüssig.

**Der Write-Zyklus heißt jetzt `schreibe-v0ai.sh`** und prüft vor jedem Partitions-
Write Größe **und** volle sha256 der Sicherung gegen `sha256-lokal.txt`; bei
Abweichung bricht er ab, ohne geschrieben zu haben (Negativprobe: Exit 1, kein
`flash boot_a`). Positive Trockenübung: Marker-Bild, boot_a, `--set-active=a`,
Reboot, Exit 0.

**Ad-hoc-Prüfung: 34 Prüfpunkte, 0 Fehler, Exit 0** (`pruefe-v0ai.py`, ausdrücklich
nicht Suite-Grün; die kanonische Suite mit 148 Punkten lief nicht). Sie prüft die
Umformung gegen den *wirklich* ausgelieferten v0ah-Init, die Negativprobe gegen ein
Archiv ohne Anker, beide Trockenübungen des Zyklus und das fertige Bild von innen
(745 Einträge, sechs Module, Init mit Byte-Versatz, `aus-bild.cpio` bytegleich).
Telefon weiterhin stumm im Fastboot; Kabel direkt ans Mac Studio ist der eine
Handgriff, den nur Gregor tun kann.


## Nachtrag 25 (2026-11-02, 23:0x–23:3x): die GPT-These ist belegt — ABOOT legt bei jedem Start nach

Das Telefon war wieder im Fastboot (Kabel direkt, erzwungener Neustart), und der
erste-Schreibvorgang  nach der Zwangspause ging in **0,664 s** durch: 4096 KB userdata, `Writing
OKAY [0.134 s]`. Damit ist auch die zweite Verdachtsreihe erledigt: es war nie das
Bild, nie die Sitzungsanzahl und nicht der Hub — es war der festgefahrene
Download-Zustand nach dem ersten Abbruch.

**Die Marker-Messung, entscheidend.** `marker-4mib.bin` (4 194 304 B, sha `39cb098d…`)
traegt MK0000-, MK4096- und MK8192-Zeilen und war als **ein einziger DATA-Sack**
unterwegs — kein Loch, also wurde wirklich jedes Feld zwischen 0 und 4 MiB
geschrieben. Nach einem Boot (uptime 71 s, Belege in `evidence/marker-sofort/`):

    feld 0     : 4d 4b 30 30 30 30 2d 32 30 32 36 2d 31 31 30 32   'MK0000-2026-1102'  -> ueberlebt
    feld 4096  : 45 46 49 20 50 41 52 54 00 00 01 00 5c 00 00 00   'EFI PART' rev 1.0, Kopf 92 B  -> weg
    feld 8192  : 28 73 2a c1 1f f8 d2 11 ba 4b 00 a0 c9 3e c9 3b   ESP-SatzGUID, erster Partitionssatz -> weg
    feld 1 MiB : Nullen  (unsere Nullen)                            -> ueberlebt
    feld 64 KiB: Nullen  (unsere Nullen)                            -> ueberlebt

Weil der Write nachweislich kein Loch hatte, kann nur ABOOT die beiden Felder
beschrieben haben: **Wurzel #15 ist belegt**, Claudes Ausweicherklaerung (Locher des
ersten Writes von 17:01) ist widerlegt. ABOOT nimmt Sektor 1 und 2 der Platte
(LUN-Sektor 4096 B), laesst Sektor 0 und alles ab 64 KiB in Ruhe — der Vorlauf von
1 MiB ist damit genau die richtige Stelle, und ext4-Makler bei 4096/8192 waeren bei
jedem Start zertreten worden.

**Nebenbefund, der die Aenderung von Punkt 1 sofort lohnte:** die Mounts melden
jetzt ihren Wortlaut in die Marke. Erste Boot-Runde mit Marker-Inhalt:

    v0ai beide Mounts fehl: mount: /ud: wrong fs type, bad option, bad superblock
                            on /dev/sda21, …   (zuvor: … on /dev/loop0, …)

Der Loop mit `offset=1048576` wird also angelegt (er heisst /dev/loop0) — die
Ablehnung kam von dem Inhalt, der zu dem Zeitpunkt da war: der Marker, kein
Dateisystem. Genau so soll es sein.

**Und eine eigene Falle, ehrlich notiert:** der Write-Zyklus lief im Vordergrund mit
420 s Werkzeugfrist; das Werkzeug ging weg, das Skript nicht. Die naechste
Telnet-Probe meldete Port 23 zu, dann stand das Telefon wieder in Fastboot — der
Selbst-Rueckweg des Init hatte nach Funkstille zurueckgegeben, was das Design von
v0aa/v0ab ist. Laengere Zyklen laufen von jetzt an als Hintergrundprozess mit
Meldung, nicht als foreground-Kette, die das Werkzeug abreisst.


## Nachtrag 26 (2026-11-02, 23:2x  - 2026-11-03, 00:5x): Wurzel #17, und die Wurzel auf userdata

**Zuerst der Erfolg.** Nach dem erzwungenen Neustart laeuft der Write-Zyklus in
**50 Sekunden** durch: userdata 114 688 KB in `Sending OKAY [2.970 s]` /
`Writing OKAY [0.135 s]`, boot_a 20 648 KB, `--set-active=a`, Reboot, Exit 0.
Hub, Sackgeometrie und Sitzungsanzahl sind damit endgueltig draussen.

**Erste Partitions-Marke (Wurzel #16).** Der Mount scheiterte weiterhin, jetzt aber
mit Wortlaut (seit v0ai ohne `2>/dev/null`):

    EXT4-fs (loop0): I/O error while writing superblock
    mount: /ud: can't read superblock on /dev/loop0

Von Hand am laufenden Telefon gemessen:

    losetup -f --show -o 1048576 /dev/sda21  -> /dev/loop0
    losetup -l /dev/loop0                     -> /dev/loop0 0 1048576 0 0 /dev/sda21 0 512
    dd if=/dev/loop0 bs=1 skip=1080 count=2  -> 53 ef            (Superblock steht da)
    blockdev --getro /dev/sda21               -> 1               (Partition ist zu)

Der Byte-Versatz war von Anfang an richtig. **pass 1 der Wache legt jede Partition
einzeln unter ro**, und die Ausnahme in der Halteschleife verhindert nur das
*erneute* Setzen  - sie hebt ein vorhandenes ro nicht auf. Der Init gab je nur die
*Platte* frei. Von Hand freigegeben montierte derselbe Loop sofort:

    mount -o rw /dev/loop0 /ud            -> /dev/loop0 /ud ext4 rw,relatime 0 0
    ls /ud                                -> bin dev etc home init lib
    cat /ud/etc/alpine-release            -> 3.24.3

**v0aj** (sha `0206cb16...`) gibt deshalb Platte *und* Partition frei und haelt die
Partition aktiv rw. Boot damit, Marke bei 172 s:

    v0aj userdata rw: /dev/sda21 on /ud type ext4 (rw,relatime)
    v0aj wache: platte_ro=0 ud_ro=0 schreibtest=probe

**Zweite Partitions-Marke (Wurzel #17).** Sechs Sekunden spaeter trotzdem:

    [  174.114810] Buffer I/O error on dev loop0, logical block 131072, lost sync page write

und danach `touch /ud/.probe-zwei` → `Read-only file system`. Der Grund sitzt in
derselben Schleife, Zeile 537 des Init: sie laeuft ueber **`/sys/class/block/sd*`**  -
das Muster erfasst auch **`/dev/sda` selbst**. Freigegeben war nur `$ud`, also legte
die Halteschleife die Platte jede Sekunde erneut unter ro, und die Partition folgt
dem Plattenschalter (Wurzel #9, jetzt von der anderen Seite: nicht das Setzen auf
der Partition, sondern das Setzen auf der Platte). **v0ak** (sha `f5ac4efd...`)
verschont deshalb die Platte der Userdata-Partition und haelt Platte wie Partition
aktiv rw.

**Haltbarkeit ist belegt.** UEber einen echten Neustart hinweg blieben auf dem
Dateisystem:

    /ud/.probe-leben     -> ueberlebt-v0ai      (vor dem Neustart geschrieben)
    /ud/.v0aj-besuch     -> die init-Marke selbst
    /ud/.v0aj-schreib    -> der Schreibtest der Wache

Damit ist M1.5 Kriterium "eine geschriebene Datei ueberlebt einen Neustart" erfuellt.

**Uebergabe blieb zweimal aus  - aus zwei verschiedenen Gruenden.** Zuerst
`uebergabe bleibt aus: init_da=66 schalter=/sbin/switch_root`: das Bild liefert
`/ud/init` mit 0644 aus, der Test heisst aber `[ -x /ud/init ]`. Von Hand auf 0755
gesetzt, **und der chmod war nach dem Neustart wieder weg**  - weil die Platte
bereits wieder unter ro lag (Wurzel #17) und ext4 mit `errors=remount-ro` geantwortet
hatte. Zweitens: `chmod 755` steht jetzt auch im Image-Bauer
(`baue-userdata-image.sh`, mit Abbruch, wenn die Bit nicht gesetzt wird) und
vorsichtshalber im Init vor der Uebergabe (`v0ak init scharf gemacht:`).

**Stand um 00:5x:** v0ak bootet, und das Telefon meldet sich **nicht** mehr auf
Telnet (172.16.42.1 und 192.168.5.1, Port 23, kein Ping)  - waehrend es am USB-Baum
als "Pixel 3 (blueline)" haengt, also in Linux ist. Genau das erwartet dieses Bild:
die Userdata-Wurzel bringt kein Gadget und kein telnetd mit, ihr `/init` haelt nur
eine Shell am Panel offen und fuehrt nach fuenf Minuten Funkstille `restart2` in den
Bootloader. Die Uebergabe ist damit stark belegt, aber **nicht abgelesen**  - dafuer
muss die neue Wurzel selbst sichtbar werden (Gadget + telnetd + Stempel-Datei), und
das Panel kann nur ein Mensch lesen (M1.2).


## Nachtrag 27 (2026-11-03, 01:1x): die Uebergabe ist passiert — gelesen auf einer Leitung, die wir nie benutzt haben

Der Wartelaufer hat 40 Minuten kein Fastboot-Geraet gesehen und **nichts
geschrieben** (Exit 1, die Negativprobe gilt also auch am echten Geraet). Dafuer
hat die Suche nach dem Zustand etwas Neues zutage gefoerdert.

**Das Telefon haengt am Bus, und zwar als unser Bild:**

    ioreg: Pixel 3 (blueline)@10330000  ->  idVendor 0x18d1, idProduct 0xd002
           USB Product Name "Pixel 3 (blueline)", USB Vendor Name "Omarchy Mobile",
           USB Serial Number "omamobile-blueline"

Diese Produktkennung traegt nur unser Gadget. Kein Fastboot (`getvar` laeuft in der
Frist auf), keine IP auf 172.16.42.1, kein Port 23 — aber am selben USB-Platz
existiert ein serielles Knoten: **/dev/cu.usbmodem103303**. Da antwortet eine Shell.

**Was diese Shell ist, entscheidet mehr als jede Mount-Marke.** Sie antwortet auf
jede Zeile, ist eine busybox-ash, aber:

    echo PFAD=$PATH                       -> /usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    cat /proc/uptime                      -> /bin/sh: cat: not found
    while read l; do ...; done < /proc/mounts   -> can't open /proc/mounts: no such file
    for f in /*; do echo $f; done         -> /*            (das Glob expandiert auf nichts)
    echo cat_da=$(if [ -e /bin/cat ] ...) -> weg          pwd -> /

Wurzel da, aber **leer**: kein /bin, kein /proc, keine einzige Datei unter `/`. Das
ist die Signatur von `switch_root`: es schiebt die neue Wurzel vor und **loescht die
alte Wurzel**; ein Prozess, der aus dem Initramfs schon lief (hier die
serielle Konsole), behaelt diese ausgeloeschte alte Wurzel als seine. Eine leere `/`
in einer lebenden Shell ist damit der Beleg, dass die Uebergabe gelaufen ist —
unabhaengig davon, dass die neue Wurzel sich gegenueber dem Mac immer noch nicht
meldet, weil das alte Userdata-Init weder Gadget noch telnetd mitbringt.

**Neues Werkzeug:** `sende-acm-befehl.py` — ein Befehl nach dem anderen ueber
/dev/cu.<knoten>, 115200 8N1, Fluchtsequenzen (die Cursor-Auskunft) werden vor der
Ausgabe entfernt. In einer ausgeloeschten Wurzel sind nur noch die eingebauten
Kommandos der Shell brauchbar (`echo`, `pwd`, `[`, `while read … < Datei` ueber
Glob- und Test-Builtins); jeder externe Applet fehlt. Deshalb stehen die Lesungen
oben in dieser Form.

**Was daraus folgt:** es fehlt nur noch das neue Userdata-Bild mit eigenem Gadget,
telnetd und `/omamobile/LEBEN` (sparse sha `7d9f2179…`, eine Sitzung). Um es zu
schreiben, muss das Telefon zurueck ins Fastboot — die Uebergabe-Shell kann nicht
einmal `reboot`, weil keinProgramm mehr da ist. Ein Handgriff: Power+Leiser halten.
