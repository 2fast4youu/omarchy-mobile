# Foto-Lesetabelle v0q (2026-10-29, 06:4x)

Vorab festgelegt, damit das Display-Foto in einer Minute ausgewertet ist. Der
Statusblock des v0q-Init schreibt in dieser Reihenfolge — die **erste Zeile,
die fehlt oder einen Fehler zeigt**, ist der Fund. Alles darunter ist dann
nur noch Kontext.

## Der Statusblock (Panel, 5 Zeilen pro Schritt)

    P1 v0q <marke> u=<uptime-s> init=<pid>          <- lebt Init ueberhaupt
    P2 mod libcomposite=<rc> u_ether=<rc> ncm=<rc>  <- Module geladen?
    P3 cfgfs=<rc> udc=<erster UDC>                  <- configfs gemountet, UDC da?
    P4 bind=<rc> udcline=<UDC-Datei> ip=<ncm-addr>   <- Gadget gebunden?
    P5 host=ping<rc> mac=<mac>                       <- Host am anderen Ende?

## Lesetabelle

| Beobachtung | These | widerlegt / gestuetzt | naechster Schritt |
|---|---|---|---|
| **P1 fehlt ganz** (Panel dunkel oder nur ABOOT) | Init laeuft nicht | Ramdisk/Init-Pfad oder Kernel-Abort | pstore lesen (`/sys/fs/pstore`), dann Packing pruefen — **nicht** neu flashen |
| P1 zeigt `init=` ohne 1 | Init ist nicht PID 1 | `rdinit=/init` ignoriert | cmdline aus dem Bild auslesen (`unpack-v0.py`) |
| **P2 rc ungleich 0** (z.B. `libcomposite=1`) | Modul passt nicht zum Kernel | vermagic oder Abhaengigkeit | `insmod` einzeln mit Meldung; vermagic vergleichen: `modinfo` der .ko gegen `uname -r` im initramfs; Reihenfolge libcomposite → u_ether → u_serial → usb_f_ncm |
| P2 meldet `File exists` | Modul schon im Kernel (=y) | ungefaehrlich | ignorieren, weiter lesen |
| **P3 `cfgfs=` ungleich 0** | configfs nicht verfuegbar | `CONFIG_USB_CONFIGFS` fehlt oder mount-Pfad falsch | Pfad im Init pruefen (`/sys/kernel/config`, nicht `/config`); libcomposite-RC von P2 nachsehen |
| **P3 `udc=` leer** | kein UDC-Provider = dwc3 nicht gebunden | USB-Controller/PHY/Typec | Typec- + dwc3-Module pruefen (`typec_qcom_pmic`, `dwc3`); DT-Knoten `usb@a6f8800` status; Rolle in `/sys/class/typec` |
| **P4 `bind=` ungleich 0** | Gadget-Seqenz fehlerhaft | UDC schon belegt / functions fehlen | Inhalt von `/sys/kernel/config/usb_gadget/g1/UDC` und `functions/` auflisten; UDC vor bind auf leeren String setzen (Referenz tut das) |
| P4 `udcline=` zeigt g1, P5 `host=` Fehler | Gadget gebunden, Host sieht nichts | Kabel, Host-Seite, oder NCM-Interface nicht sichtbar | anderes Kabel/Port; am Mac `ifconfig -a` und `system_profiler SPUSBDataType`; Interface-Name im Panel nachtragen |
| **P4 ok, P5 ping ok** | NCM steht | — | M1 erfuellt: `ssh root@172.16.42.1` vom Mac (Host 172.16.42.5) |
| Panel zeigt nur `P1`, keine Folge | Panelblock bricht ab | dmesg-Ausgabe ueberlagert tty0 | Ausgabe auf die 5 Zeilen begrenzen (`clear`/`printf`), Bild mit dem Handy-Foto halten |
| Panel zeigt die **dmesg**-Zeilen, keinen Statusblock | Panelblock lief zu frueh/spaet | Zeitfenster | Statusblock vor `exec init` verankern, Wiederholen ohne dmesg |

## Was das Foto NICHT entscheidet

* Ob ABOOT `RESTART2` ehrt — dafuer braucht es UART oder einen Test, bei dem
  das Telefon danach in Fastboot zurueckkommt.
* Ob der Host (Mac) das Interface richtig benennt — dafuer `ifconfig -a`.

## Der Handgriff, der v0q startet (eindeutig, 2026-10-29 11:0x)

Das Telefon steht im Fastboot-Menü, und dort steht **„Start" schon
ausgewaehlt**. Ein **kurzer Druck auf Power** startet den Boot — das ist die
Aktion, die gemeint ist, wenn ich „starten" schreibe.

* **Kurzer Druck auf Power** = ausgewaehlten Menüpunkt ausführen → v0q bootet.
* **Power ~10 s halten** = Hard-Reset. Geht auch, ist aber eine andere Aktion
  (ohne Menü, erzwingt einen Neustart aus jedem Zustand).
* **Power + Leiser ~10 s halten** = ins Fastboot-Menü (damit sind wir dort
  hingekommen); aus dem Menü heraus ist das kein Start.
* `fastboot --set-active=a` ist hier **nicht** nötig: Slot a ist der aktive und
  war in jeder Lesung nicht als unbootable gemeldet (siehe BRINGUP-M1.md 09:31).
  Ein Neustart ist kein Partitionsschreibvorgang.

## Fixe Reihenfolge nach dem Foto

1. Erste fehlerhafte Zeile bestimmen (Tabelle oben).
2. Am Mac parallel: `ifconfig -a | grep -i -E "ncm|usb0|172.16"`,
   `ls /dev/cu.usb*`, `fastboot devices` — damit "kein NCM" und "kein Bus"
   getrennt sind.
3. Bei Modul- oder UDC-Fehler: UART (`fastboot oem uart enable`, SBU-Adapter,
   1.8 V) statt naechstem Blindbau.
