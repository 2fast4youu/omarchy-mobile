# Warum kein Bild je auf boot_a schrieb (2026-11-01, 19:33–19:45)

## Kurz

Unsere eigene Storage-Guard blockierte den Log-Kanal. Sie setzt beim Boot die
ganze Platte **und** jede Partition auf read-only. `logflush` drehte nur die
Partition zurueck — und das wirkt nachweislich nicht: die Partition folgt dem
Schalter der Platte. Der Fehlertext von dd lag hinter `2>/dev/null`, deshalb
stand nirgends etwas davon.

## Die Kausalkette, gemessen am laufenden Geraet

Referenz lief (Kernel 7.1.0-rc1-sdm845, Debug-Shell), Telnet offen. Protokoll
roh in `ro-kausalitaet-2026-11-01.md`.

| Uhrzeit | Handlung | Antwort |
|---|---|---|
| 19:40:44 | Ist-Zustand | `sda=0 sda11=0` (beide schreibbar) |
| 19:40:50 | `blockdev --setro /dev/sda; blockdev --setrw /dev/sda11` | `sda=1 sda11=1` |
| 19:40:56 | dd, Marker, `bs=131072 seek=504 conv=notrunc,fsync` | `dd: error writing '/dev/sda11': Operation not permitted`, `0 bytes copied`, `dd_rc=1` |
| 19:41:02 | Rueckleseprobe | alter Marker von 18:07 noch da |
| 19:41:08 | `blockdev --setrw /dev/sda` dann derselbe dd | `platte_rw=0`, `24 bytes copied`, `dd_rc=0` |
| 19:41:14 | Rueckleseprobe | `OMAMOBILE-RO-BLOCK-1101` bei 66060288 |

Zeile 2 ist der entscheidende Satz: **`--setrw` auf der Partition aendert
nichts, solange die Platte read-only ist.** Zeile 5 zeigt, dass dieselbe
Partition mit freier Platte sofort schreibt.

## Warum das genau unser Bild trifft

`storage_guard()` in der Init (Zeile ~486) geht ueber `/sys/class/block/sd*`
und ruft fuer jede Platte und jede Partition `blockdev --setro` auf — das ist
gewollt, first light soll nichts schreiben koennen, was es nicht darf.
`logflush()` tat danach nur `blockdev --setrw "$d"` mit `$d=/dev/sda11`. Nach
dem Befund oben blieb der Schreibzugriff verwehrt, dd ging mit rc=1 und
null Bytes ab, und die Zeile endete auf `2>/dev/null`. Kein Mark, kein
Ruecklesewert, kein Panel-Hinweis: **seit dem ersten Bau der Guard hat kein
einziges Bild auf boot_a geschrieben.**

Der Gegenbeweis sitzt in der Partition selbst: um 19:35 und 19:41 lag bei
66060288 unveraendert der Marker meines Schreibtests von 18:07
(`od -c`: `O M A M O B I L E - S C H R E I B T E S T - 1 1 0 1 \n`), obwohl
v0ac von 18:16 bis 18:21 lief, `logflush` mehrfach aufrief und sich erst nach
334 s zurueckmeldete.

Die fruehere Erklaerung „`find_bootdev` kennt nur die Ueventd-Symlinks" ist
damit **nicht** die Todesursache: die Symlinks fehlen im Initramfs zwar
wirklich (dagegen hilft v0acs PARTNAME-Suche, gemessen traegt
`/sys/block/sda/sda11/uevent` die Zeile `PARTNAME=boot_a`, und
`/sys/block/sda/sda11/dev` liefert `8:11`), aber selbst mit gefundenem
Geraet haette der Schreibvorgang nicht durchgekonnt.

## v0ad (sha256 878558a8da04a6b6…, Init 587 Zeilen)

* `logflush` bestimmt die Platte aus dem Partitionsnamen
  (`sed 's/[0-9]*$//'`), setzt **Platte und Partition** rw, schreibt, setzt
  beide wieder ro.
* Der dd-Text laeuft in eine Variable und geht als Mark aufs Panel:
  `schreib_rc=… <dd-text> platte=/dev/sda ro_achter=1`. Damit ist ein
  Schreibfehler sichtbar, statt zu schweigen.
* Zwei neue Marks an der Gadget-Stelle, auf Clauses Frage hin, vor und nach
  dem configfs-Mount: `vor mkdir: configfs=<zahl> libcomposite=<zahl>
  module=<zahl>` und `nach mount: configfs=<zahl> ordner=ja|nein udc=<liste>`.
  Ohne diese Zahlen bleibt „kein Gadget am Baum" eine Beobachtung.
* Nichts entfernt: PARTNAME-Suche, Ablesung, Prozessnummer-Wartung,
  Selbst-Rueckweg bleiben. Pruefer: 28 Punkte 0 Fehler, `sh -n`, `bash -n`,
  Round-trip des Archivs, restart2-Inhalt dicht.

## Nebenbefund: meine erste Messung der Kernel-Identitaet war falsch, richtig gemessen stimmt die Dokumentation

Zeile 135 der Init behauptet, der Kernel dieses Bildes sei im gzip-Anteil
byte-identisch zur Referenz. Mein erster Vergleich (19:44) verglich das ganze
Kernel-Feld des Boot-Bildes: v0ad 16154423 B (sha `24e8b99a…`) gegen Referenz
16154252 B (sha `e494d677…`) — ungleich, und ich schrieb "falsifiziert". Die
Frage war nur, ob der Kernel gleich ist. Gemessen 19:52, entpackt:

| Stück | v0ad | Referenz | gleich? |
|---|---|---|---|
| entpackter Kernel | 44498944 B, sha `4f41f138…` | 44498944 B, sha `4f41f138…` | **ja** |
| gzip-Strom allein | 16042611 B, sha `7112decb…` | 16042611 B, sha `7112decb…` | **ja** |
| Anhang hinter dem gzip-Strom (DTB) | 111812 B, sha `01be7510…` | 111641 B, sha `24962c90…` | nein, 171 B Unterschied |

Der in `patch-v0q.py` genannte Hash `7112decbddcbe235…` ist exakt der gemessene
Hash des gzip-Stroms. **Die Dokumentation stimmt; meine erste Messung hatte das
falsche Objekt.** Der Unterschied liegt allein im angehaengten Device-Tree, den
unser Pack-Skript selbst ansetzt. Lehraetz: ein Grössenvergleich des Boot-Feldes
beantwortet nicht die Frage nach dem Kernel — entpacken und beide Haelften
getrennt hashen.

## Die sechs Referenz-Starts von heute, tabelliert (Clauses Punkt 2)

Alle sechs: `fastboot boot pmos-ref-build/ref/boot.img` = Start aus dem RAM,
kein Flash. „Telnet" = ob 172.16.42.1:23 innerhalb 200 s offen ging.

| # | Start | Slot vorher | Retry vorher | vorher aufgefuellt | Telnet | Bemerkung |
|---|---|---|---|---|---|---|
| 1 | 17:25:31 | a | a:0, unbootable a ja | nein | **zu** | Slot a war als unbootable markiert |
| 2 | 17:31:12 | a | wie oben | nein | **zu** | |
| 3 | 17:35:38 | a | wie oben | nein | **zu** | |
| 4 | 17:39:38 | a → b | b:3 | `--set-active=b` | **offen bei 78 s** | erster Erfolg |
| 5 | 18:02:03 | b | b:0 | `--set-active=b` → b:3 | **offen bei 72 s** | |
| 6 | 18:22:10 | b | b:1 | `--set-active=b` → b:3 | **zu** | aber: 19:33:51 Telnet offen mit `up=807s` — das ist ein Start um 19:20, dessen Anfang wir nicht gesehen haben |

Zwei von sechs sichtbar, und der siebte meldete sich versaetet. Was die
Tabelle **nicht** enthaelt, weil ich es nicht weiss: ob das Kabel an jedem
dieser Starts direkt am Mac Studio oder am Hub steckte. Gregor hat das am
Nachmittag zugesagt, aber nicht bestaetigt. Bei zwei von sechs ist der
Lesekanal als Beweisgrundlage zu wenig — jede Messung, die auf „der Mac sieht
das Geraet" aufbaut, braucht entweder die Tastenaktion als Ausgang oder einen
zweiten Kanal (der jetzt eingebaute boot_a-Schreibpfad).
