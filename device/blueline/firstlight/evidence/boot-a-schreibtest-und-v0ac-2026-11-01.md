# boot_a-Schreibtest und v0ac (2026-11-01, ab 18:05)

## Was gemessen wurde, in der Kuerze

Der Lesekanal ist heil — **unser Bild hat nie in ihn hineingeschrieben.**
Grund: `find_bootdev` kennt nur die Symlinks eines Uevent-Daemons, und den hat
unser Initramfs nicht. v0ac sucht die Partition selbst.

## Messung 1: die Referenz schreibt und liest dieselbe Stelle (18:07)

Protokoll: `boot-a-schreibtest-2026-11-01.md`. An der laufenden Referenz
(Kernel 7.1.0-rc1-sdm845, geparkter Debug-Shell) ueber Telnet:

    D=$(readlink -f /dev/disk/by-partlabel/boot_a)   -> /dev/sda11
    blockdev --getsize64 $D                          -> 67108864      (64 MiB)
    blockdev --getro $D                              -> 0   (vorher schon schreibbar)
    printf 'OMAMOBILE-SCHREIBTEST-1101\n'            -> 27 Bytes
    dd of=$D bs=131072 seek=504 conv=notrunc,fsync    -> schreib_rc=0, 27 B copied
    dd if=$D bs=1 skip=66060288 count=48 | od -c      -> OMAMOBILE-SCHREIBTEST-1101\n, dann \0
    blockdev --setro $D                              -> ro_wieder=1

504 * 131072 = 66060288 B = 63 MiB, und genau dort steht der Marker. Der
Versatz in unserer `logflush`-Zeile (`seek=504`) ist also richtig, die
Partition ist beschreibbar, ein Schreiben braucht kein `--setrw` (ro stand auf
0).

## Messung 2: unser Bild hat die Stelle nie erreicht

Zwei Lesungen nach zwei eigenen Laeufen (17:41 nach v0ab-Durchgang 1, 18:03
nach v0ab-Durchgang 2): `dd if=$D bs=131072 skip=504 count=8 | grep -c
OMAMOBILE-LOG` -> **0**. Kein Fall von "schwer zu lesen", sondern: nie
geschrieben.

## Die Ursache im Bild, nicht geraten

Zeile 276ff des ausgelieferten v0ab-Init:

    find_bootdev() {
        for l in /dev/disk/by-partlabel/boot_a /dev/disk/by-name/boot_a; do ...
        return 1
    }

`/dev/disk/by-partlabel/` legt ein Uevent-Daemon an (Android `ueventd`,
postmarketOS `mdev -s`). Die Referenz hat ihn — von dort stammt auch der
Symlink, den der Schreibtest benutzt hat. **Unser first-light laeuft im
Initramfs ohne jeden Daemon**, also existiert dort kein `by-partlabel`,
`find_bootdev` gibt 1, `logflush` kehrt ohne jede Zeile zurueck, und es bleibt
keine Beweislast auf der Partition. Das erklaert, warum der Schwanz in jedem
Lauf leer war — seit er existiert.

## v0ac: die eigene Suche

`find_bootdev` behaelt die beiden bekannten Pfade als erste Wahl und sucht
danach selbst, denn der Kernel haelt denselben Inhalt, den ueventd benutzt:

    for u in /sys/block/*/sd*/uevent /sys/block/vd*/uevent; do
        grep -q '^PARTNAME=boot_a$' "$u" || continue
        ...  bootdev=${p##*/}; mknod falls /dev-Knoten fehlt ...
        mark "boot_a selbst gefunden: $name (aus $u)"

Drei neue Marks auf dem Panel: `boot_a selbst gefunden: sdaNN`,
`knoten /dev/sdaNN angelegt major=.. minor=.. rc=..`, und — wenn gar nichts
geht — `boot_a nirgends gefunden: kein by-partlabel, kein PARTNAME in /sys/block`.
Angelegt wird nur, wenn der Knoten fehlt; devtmpfs liefert ihn normalerweise.

Die Ablesung am Ende des Laufs meldet ausserdem `logflush rc=`, `geraet=` und
`rueckgelesen=<zahl>` — die Rueckleseprobe liest den Marker direkt aus der
Partition zurueck, bevor das Bild sich per `restart2 bootloader` selbst
zurueckholt.

Zahlenspur des Umbaus, **gemessen** (`scratch/misse-v0ac-spur.py`), nachdem der
erste Baudurchlauf eine Differenz von 2 Schleifenkoepfen forderte und 1 fand:
ein `; do`, ein `for` in Spalte 5, ein `mknod`, ein `grep -q`, drei `mark `,
20 Zeilen (558 -> 578), Klammerbilanz 197/197, rein ASCII. Das neue `done`
steht eingerueckt, Zaehlen in Spalte 0 haette es uebersehen — die Pruefung
zaehlt jetzt Zeilen, deren Inhalt genau `done` ist.

## Stand der Geraetebilder

| Bild | SHA-256 boot.img | Inhalt |
|---|---|---|
| v0aa | `7f0397f5…` | Ziel boot_a, letztes logflush + restart2, 8-Runden-Fenster |
| v0ab | `198795c6…` | Panel-Ablesung 60 x 3 s, `rueckgelesen=`, restart2 im Archiv |
| v0ac | `0c03240a…` | eigene Partitionssuche ueber `PARTNAME=` |

Rückweg unveraendert: `boot_b` = Referenz (`ed2c225f…`), `dtbo_b` = Factory
(`ff7bd6da…`), `dtbo_a` = Factory. boot_b wurde heute kein einziges Mal
geschrieben.

## Was v0ac beantworten muss

1. `boot_a selbst gefunden: sdaNN` — findet die eigene Suche die Partition?
2. `rueckgelesen=1` (oder mehr) — liegt der Log-Beutel tatsaechlich auf der
   Partition? Wenn ja, koennen wir zum ersten Mal **den vollstaendigen
   steps.log eines eigenen Kernels maschinell lesen**: Modul-Ladung,
   UDC-Auffinden, Binden, Haengeliste. Das ist der Leseweg, den die drei
   dunklen Nachmittage gebraucht haetten.
3. Wenn `boot_a nirgends gefunden` — dann kennt dieser Kernel keine
   `PARTNAME=`-Eigenschaft und der Kanal braucht einen anderen Pfad (dann:
   direkt `blockdev --getsize64` ueber `/dev/sda11`-Numerik, die die
   Partitionstabelle des geladenen Slot liefert).
