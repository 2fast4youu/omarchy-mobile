# Foto-Lesetabelle v0q (Stand 2026-10-29, 12:5x)

**Erste Fassung (11:0x) war eine erfundene Skala.** Sie schrieb Zeilen `P1`–`P5`
mit `insmod`-Rückgabewerten aufs Panel; nachgelesen im fertigen Bild (Init,
370 Zeilen, 737 cpio-Einträge): die Modul-Meldungen stehen dort in `mark()` =
nur `/dev/kmsg` (Zeile 19–22), **nicht** auf dem Panel. Das ist genau die Klasse
Fehler, die zwei Abschnitte weiter unten als „never invent the instrument"
steht — deshalb hier die Panel-Ausgabe, die der Init tatsächlich schreibt.

## Was auf dem Panel wirklich steht (wörtlich aus dem Bild)

    Omarchy Mobile first-light v0h - RAM only, Watchdog-Fuetterer + Pstore    (Zeile 82, immer zuerst)
    ===== pstore: <datei> =====  …tail -40…                                   (Zeile 71-73, nur wenn vorheriger Crash)
    --- <uptime>s ---                                                          (Zeile 53-59, alle 20 s neu)
    wdt bootstatus=… timeout=…
    udc=<ls /sys/class/udc> gebunden=<cat /sys/kernel/config/usb_gadget/*/UDC>
    dwc3 rolle=<typec data_role> typec=<ls /sys/class/typec>
    pid1=<comm> state=<stat-Feld 3> kinder=<…>
    letzter Schritt: <tail -1 /run/steps.log>
    omamobile-blueline: SSH ready: root@172.16.42.1; all storage read-only     (Zeile 295, Gadget-Ende)
    omamobile-blueline: storage guard: <n> device(s) could not be write-protected (Zeile 327)

## Lesetabelle (die erste Zeile, die fehlt oder abweicht, ist der Fund)

| Beobachtung auf dem Panel | These | gestützt / widerlegt | nächster Schritt |
|---|---|---|---|
| Panel ganz dunkel | Init nie gelaufen **oder** Panelblock schreibt ins Leere | beides möglich, trennen: `dmesg`/pstore brauchen den Runner nicht | pstore am nächsten Fastboot lesen; kein Blindbau |
| Banner (Zeile 82) da, danach nichts | PID 1 hängt zwischen Mounts und Messblock | Mount- oder Panelblock-Problem | Inhalt von `/run/steps.log` auf dem Panel fehlt hier — nächster Build schreibt ihn |
| Statusblock alle 20 s, **`udc=` leer** | UDC-Provider fehlt: dwc3/PHY/Typec | Modul-/DT-Lücke | `typec`, `dwc3`-Module und DT-Knoten `usb@a6f8800`; UART statt weiterem Bild |
| `udc=a6f8800.dwc3` o.ä., **`gebunden=` leer** | Gadget gebaut, nie an UDC gebunden | Bind-Schritt (Zeile 182/183) nicht erreicht | `letzter Schritt:` lesen — er sagt, wo PID 1 stand |
| `gebunden=g1` und Mac sieht kein NCM | Gadget bindet, Host sieht nichts | Kabel/Host-Seite oder Interface unsichtbar | anderes Kabel/Port, `ifconfig -a`, `system_profiler SPUSBDataType` |
| `SSH ready: root@172.16.42.1` auf dem Panel | Kette ist durchgelaufen | — | M1: vom Mac `ssh root@172.16.42.1` |
| `pstore:`-Block mit Call Trace | vorheriger Boot ist abgestürzt | Grund steht im Text | den Crashtext lesen, nicht neu flashen |
| `pid1=` zeigt etwas anderes als `init` | nicht unser Init als PID 1 | `rdinit` verfehlt | cmdline aus dem Bild auslesen |
| `letzter Schritt: KEINER`/leer | `/run/steps.log` nie beschrieben | `mark()` lief nie | Mounts prüfen (Zeile 28–34 melden `mount … FAILED` in kmsg) |
| `wdt bootstatus=` mit Reset-Bit | Reset kam vom Watchdog | ABOOT-Zähler erklärt | mit `retry-count`-Lesung abgleichen |

## Der unabhaengige Kanal: UART ueber SBU (kein Partitionsschreib)

Aus der Geraeteseite `Google_Pixel_3_(google-blueline)` (Nura-Wiki, am 29.10.
abgerufen), Abschnitt „UART", bestaetigt durch AOSP „Build Pixel kernels" und
`Peter-Easton/android-debug-cable-howto` — woertlich uebernommen:

* Pinbelegung: `A1 (GND) → GND`, `A8 (SBU1) → RXD`, `B8 (SBU2) → TXD`.
* Pegel: „Voltage is 3.3V, although 1.8V seems to work as well." Baud 115200
  = genau unsere Kernelzeile `console=ttyMSM0,115200n8`.
* Einschalten: Telefon in Fastboot, dann `fastboot oem uart enable`, dann
  starten lassen. Der Befehl schreibt keine Partition; rueckgaengig mit
  `fastboot oem uart disable`.
* Richtung: „it won't work if the plug is reversed on one side" — USB-3/TB3-
  taugliches Kabel, „A"-Seite der Breakout auf der Seite des Displays.

Was dieser Kanal trennt, was Panel und Host nicht trennen koennen:

| Beobachtung am UART | Bedeutung |
|---|---|
| Kernel-Log, aber kein `init:` | Init laeuft nicht → Archiv/Initramfs |
| `init:` bis `modul ….rc=0` | Module geladen; die Gadget-Schritte lesen sich dann selbst |
| Fehler bei `mkdir …/functions/ncm.usb0` | ROOT CAUSE #4 doch noch offen |
| UDC gesetzt, am Mac aber kein `en*` | Gadget bindet, Host-/Kabelseite versagt → NCM als Plan verwerfen |
| gar kein Log | SBU-Richtung/Pegel/Kabel — Handgriff, keine Software |

Der Beobachter zaehlt fuer `seriell` nur `/dev/cu.usb*`; ein UART-Adapter
taucht dort auf, sobald er steckt — die Spalte ist ohne Skriptaenderung
dafuer brauchbar.

## Was das Foto NICHT entscheidet

* Ob ABOOT `RESTART2` ehrt — in v0q ist der `restart2`-Block toter Code (Datei
  `/etc/omamobile-panic-probe` fehlt im Bild), also läuft er gar nicht erst.
* Ob der Mac das Interface richtig benennt — dafür `ifconfig -a`.
* Die Modul-Einzelmeldungen: die stehen nur in kmsg. **Nachtrag für den nächsten
  Build:** `say "moduli: $(ls /proc/modules | wc -l)"` in den 20-s-Block, dann
  ist `usb_f_ncm` geladen/nicht geladen auf dem Foto sichtbar.

## Der Handgriff, der v0q startet

Im Fastboot-Menü ist **„Start" bereits ausgewählt** → **kurzer Druck auf Power**.

* **kurzer Druck Power** = Menüpunkt ausführen → bootet v0q
* **Power ~10 s halten** = Hard-Reset (geht auch, andere Aktion)
* **Power + Leiser ~10 s halten** = zurück ins Fastboot-Menü
* `--set-active=a` ist nicht nötig: Slot a ist aktiv und war in jeder Lesung
  nicht unbootable (BRINGUP-M1.md 09:31). Ein Neustart ist kein Partitionsschreibvorgang.

## Feste Reihenfolge nach dem Foto

1. Erste fehlerhafte oder fehlende Zeile bestimmen (Tabelle oben).
2. Am Mac parallel: `ifconfig -a | grep -i -E "ncm|usb0|172.16"`,
   `ls /dev/cu.usb*`, `fastboot devices`, `ioreg -p IOUSB` — damit „kein NCM"
   und „kein Gerät am Bus" getrennt sind.
3. Bei leerem `udc=` oder Modul-Verdacht: UART (`fastboot oem uart enable`,
   USB-C SBU1/SBU2, **1.8 V**) statt nächstem Blindbau.
