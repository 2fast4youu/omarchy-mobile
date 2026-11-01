# Erster vollständiger Protokoll-Lauf eines eigenen Kernels (2026-11-01, 19:58)

Der Kanal funktioniert jetzt, und er hat die Ursache des schweigenden Gadgets
selbst genannt. Kein Panel, kein Tastendruck, kein Raten.

## Wie der Beutel zustande kam

v0ad (sha256 `878558a8…`) um 19:50:49 aus dem RAM gestartet, Selbst-Rückweg um
**19:56:20 bei t=330 s** (schneller als v0acs 334 s, gleiche Struktur).
19:58:13 liest die Referenz den Schwanz von boot_a:

    A=$(readlink -f /dev/disk/by-partlabel/boot_a)
    dd if=$A bs=131072 skip=504 count=8 | tr -d '\0' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | uniq -c
          1 OMAMOBILE-LOG

Der eine Treffer ist unser Log-Beutel — der Schreibtest-Marker von 18:07 ist
weg, weil der Beutel ihn ueberdeckt hat. Im Beutel steht die eigene
Schreibmeldung:

    [7s] step: schreib_rc=0 8+0 records in 8+0 records out 1048576 bytes (1.0MB)
         copied, 0.010877  platte=/dev/sda ro_achter=1

Das ist der Fix aus `ro-und-sechs-starts`: Platte und Partition rw, dann
geschrieben, beide zurueck ro. Vor dem Fix schrieb seit v0p kein Bild ein
einziges Byte auf diese Partition.

## Was der Lauf sagt, in seiner eigenen Reihenfolge

| Zeit | Meldung | Bedeutung |
|---|---|---|
| 5s | `kernel 7.1.0-rc1-sdm845 aarch64` | derselbe Kernel wie die Referenz |
| 6s | **`KEIN /usr/lib/modules/7.1.0-rc1-sdm845 - Gadget-Module fehlen`** | der Ordner ist im laufenden System nicht da |
| 6s | `modul libcomposite.ko FEHLER 254` (und vier weitere, `usb_f_rndis` still) | 254 = -ENOENT: die Datei existiert nicht |
| 6s | `moduli: 1 geladen, usb_f_ncm 0` | ohne Module kein NCM |
| 6s | `usb_gadget not found in configfs, skipping gadget setup` | configfs-Mount fehlgeschlagen, weil USB_CONFIGFS=m ist |
| 21s…127s | acht Bind-Runden, jede: `can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory` | **das ist der Text, den Gregor am Panel las** |
| 6s | `boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)` | die PARTNAME-Suche aus v0ac arbeitet |
| 131s | `udc=a600000.usb module=0` | der Controller IST da, es fehlt nur das Gadget-Oberbau |
| 131s | `dunkel=888000.i2c geni_i2c: Failed to get tx DMA ch` | einzige zurueckgestellte Sonde, nicht USB |
| 131s | `--- pstore --- console-ramoops-0  dmesg-ramoops-0` | **pstore ist in unserem Bild gefüllt** |

## Die Ursache, gemessen am ausgelieferten Bild

`fl-v0ad/firstlight.img`, Ramdisk entpackt, 738 Eintraege. Die sechs `.ko` sind
da (149865 / 65065 / 66241 / 58993 / 38585 / 93009 B, ELF, Eintragsnummern
730–735). Aber die Ordnereintraege darunter:

    usr        VORHANDEN (mode 40755)      usr/lib   VORHANDEN (mode 40755)
    usr/lib/modules                                   FEHLT
    usr/lib/modules/7.1.0-rc1-sdm845                  FEHLT
    …/kernel, …/drivers, …/usb, …/gadget, …/function  FEHLT

Der Initramfs-Entpacker des Kernels legt einen fehlenden Elternordner nicht an:
die Datei wird ohne Meldung verworfen. Genau das erklärt den Unterschied
zwischen zwei Aussagen, die beide wahr waren — der Modulpruefer fand die Dateien
im Archiv (28 Punkte, 0 Fehler, `Modul bytegleich mit der Quelle, ELF`), und im
laufenden System waren sie nicht da. **Keine bisherige Pruefung hatte gefragt, ob
jeder Dateieintrag seinen Elternordner im Archiv hat.**

Dasselbe gilt für `usr/bin/restart2`: dort existierte `usr/bin` als Eintrag,
deshalb funktionierte der Selbst-Rueckweg, obwohl die Module fehlten.

## v0ae (sha256 0d3b7fc6af599ecb…, Ramdisk 745 Eintraege)

Sieben Ordnereintraege (mode 040755, eigene Inodes) **vor** der ersten
Moduldatei — der Elternordner muss im Archiv vor seinem Kind stehen. Und eine
neue Pruefung, die es vorher nicht gab: fuer **jeden** Dateieintrag wird
verlangt, dass sein Elternordner im Archiv steht, ausgeführt auf der Liste im
Umbau **und** ein zweites Mal auf dem Archiv, das wirklich im Bild steckt
(`Bild-Ramdisk: 745 Eintraege, 6 Module, Dateien ohne Elternordner: 0`).
Ein Modul, das im Archiv liegt und im Wurzelsystem fehlt, ist jetzt ein
Baiausfall statt eines dunklen Bootes.

## Nebenbefund, der einen zweiten Kanal eroeffnet

Unser eigenes Bild meldet gefuellte pstore-Knoten
(`console-ramoops-0`, `dmesg-ramoops-0`). Die fruehere Entscheidung
„pstore/Ramoops ist nicht nutzbar, kein Knoten" gilt fuer unser Bild nicht. Der
Vorher-Nachher-Vergleich ist damit moeglich: der Kernel-Text des *vorherigen*
Laufs liegt beim naechsten Start schon im System, unabhaengig davon, ob das
Gadget hochkommt.

## Offen

Ob v0ae wirklich ein Gadget bindet, misst der RAM-Lauf ab 19:58 Uhr
(`v0ae-durchgang-2026-11-01.md`). Erwartung, vorher festgelegt: `moduli:` meldet
6 geladene Module, `usb_f_ncm 1`, und der Mac sieht 172.16.42.1. Wenn die
Bind-Runde trotzdem gegen `nonexistent directory` laeuft, ist configfs das
Problem und nicht die Module — dann meldet das der Beutel in 5 Minuten, nicht
erst ein Panel-Text.
