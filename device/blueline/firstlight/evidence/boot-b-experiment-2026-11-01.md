#/boot_b-Experiment und Widerspruch (2026-11-01, 14:13–14:17)

## Was geflasht wurde
- Uhrzeit 14:13:49: `fastboot flash boot_b pmos-ref-build/ref/boot.img`
  - Quelle: ref/boot.img, 28729344 B, sha256 ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82
  - Sicherung Rueckflash boot_b: images/factory-spiegel/sp1a/boot.img,
    sha256 5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e
- boot_a wurde NICHT beschrieben.

## Zustand VOR dem Flash (14:13:31, getvar)
current-slot: a
slot-retry-count:a: 0   slot-unbootable:a: yes  (NEU gegenueber 31.10.: war "no")
slot-retry-count:b: 2   slot-unbootable:b: no   slot-successful:b: no

## Zustand NACH dem Flash (14:13:51)
wie vorher, nur slot-retry-count:b: 3 (Write auf boot_b hat Zaehler gesetzt)

## Boot-Versuch aus Slot b (14:13:59 `fastboot reboot`)
- 150 s gepollt (Telnet 172.16.42.1:23): kein Telnet.
- 14:16:55: Geraet haengt in FASTBOOT (18d1:4ee0). retry b ist IMMER NOCH 3,
  retry a ist 0. current-slot immer noch a.
- Deutung: ABOOT hat Slot a NICHT uebersprungen. Bei unbootable:a + reboot
  (ohne Argument) faellt der Bootloader direkt in den Fastboot-Bildschirm
  zurueck, statt Slot b zu starten. Slot b wurde also nie probiert.
  Der Retry-Zaehler b wurde nicht verbraucht — bestaetigt: kein Boot-Versuch.

## Widerspruch, den Claude angemahnt hat (BELEGT, nicht geloest)
- 31.10. ~20:21: `fastboot boot ref/boot.img` -> Referenz lief, Telnet offen,
  en11 172.16.42.2. Slot a damals: retry 2..3, unbootable:no.
- 01.11. 14:06, 14:09, 14:11 (dreimal, je OKAY/Booting OKAY ~10 s):
  Geraet nach ~13 s wieder in Fastboot (idProduct 0x4EE0), Telnet nie offen,
  ACM-Port nie da, iface 172.16.42.* nie vorhanden.
  Mautprotokoll: scratch/maut-141055.log (t=7s "kein Pixel", t=13s Fastboot an).
- Unveraendert zwischen beiden Daten: ref/boot.img sha256 (ed2c225f…),
  Cmdline im Bild gleich. 'dtbo/vbmeta nie angefasst' war falsch und ist
  berichtigt: dtbo_b/vbmeta_b tragen seit 15:01 Factory-Inhalt, dtbo_a war
  an diesem Nachmittag leer (erster eigener Schreib 16:31) — das ist der
  einzige Zustandsunterschied, der die vier 13-s-Tode von 14:06–14:18 von den
  ueberlebenden Laeufen ab 15:06 trennt (belegt durch den Fuell-Test 16:34).
- Einzige bekannte Aenderung: Slot a jetzt unbootable:yes (retry 0).
  Das kann den Bootloader-Fallback erklaeren, NACHDEM das geladene Bild
  abstuerzte — aber nicht, warum es heute abstuerzt und gestern nicht.

## Offene Pruefpunkte
1. Bootet die Referenz ueberhaupt noch? (Panel-Foto waehrend fastboot boot)
2. dtbo: ABOOT legt dtbo_a/b als Overlay auf den DTB im boot.img an,
   auch bei `fastboot boot` (ABOOT-Standard bei Pixel). Pruefen: pmOS-Wiki
   google-blueline nennt dtbo/vbmeta NICHT (extrahiert 14:14, Wiki-Stand:
   nur flash_rootfs/flash_kernel, kein erase dtbo, kein vbmeta).
   Gegenprobe moeglich: fastboot flash dtbo_b <leer/erase>, dann RAM-Boot.
3. vbmeta: Wiki nennt es fuer blueline nicht; unlocked = advisory only.

## Nachtrag 14:18 — Widerspruch reproduzierbar
- 14:18:20 viertes `fastboot boot ref/boot.img` (sha ed2c225f, gleiches Kabel/Hub):
  t=0..8s kein Google-USB am Baum, ab t=12s wieder 0x4EE0 (Fastboot), Telnet zu.
  Ergebnis identisch zu 14:06/14:09/14:11. Referenz bootet HEUTE nicht mehr,
  gestern (31.10. ~20:21) bootete sie mit denselben Bytes.
- Akku als Ursache ausgeschossen: battery-voltage 4243 mV, battery-soc-ok yes
  (identisch zum getvar-all vom 31.10.).
- Slot-b-Boot von 14:13:59 war KEIN Boot-Versuch: retry b blieb 3, retry a blieb 0,
  current-slot blieb a. ABOOT faellt bei unbootable:a mit reboot(ohne Argument)
  direkt auf den Fastboot-Schirm; ein automatischer Wechsel nach b findet nicht statt.
  -> `fastboot reboot` ist kein testbarer Rueckweg, solange a unbootable ist.
- dtbo/vbmeta: pmOS-Wiki google-blueline (extrahiert 14:14) nennt weder
  `erase dtbo` noch vbmeta-Flags; nur flash_rootfs + flash_kernel. Andere
  SDM845-Geraete (Xiaomi) brauchen `fastboot erase dtbo`, weil die
  Android-Overlays den Mainline-DTB verf&auml;lschen. Auf dem Pixel legt ABOOT
  dtbo_a als Overlay an den vom `fastboot boot`-Bild geladenen DTB — das ist
  die einzige heute noch offene Erklaerung, aber dtbo wurde zwischen gestern
  und heute NICHT veraendert, also erklaert es den Tag-Wechsel nicht allein.
- Lokale Sicherung dtbo/vbmeta: fehlt. images/factory-spiegel/sp1a enthaelt
  nur boot.img (64 MiB). dtbo_a/b = je 8 MiB, vbmeta_a/b = je 64 KiB.
  Vor jedem dtbo-Write muesste das Google-factory-paket (sp1a) als Quelle
  dienen oder ein Backup-Read (fastboot fetch geht hier nicht).

## Panel-Fenster 14:2x — ausgefuehrt, Ergebnis
- Drei RAM-Boots: 14:20:41, 14:22:12, 14:23:43 (je `fastboot boot ref/boot.img`,
  Booting OKAY ~10 s), danach 80 s Beobachtung. 14:25:18: Telefon wieder in
  Fastboot, current-slot a, retry a 0, unbootable a yes — unveraendert.
- Kein Telnet, kein ACM, kein 172.16.42.* in allen drei Fenstern (Polling
  14:18-Lauf mass dasselbe Bild: ab t=12s nur 0x4EE0).
- Foto waehrend der Fenster lag vor Gregor; Rueckmeldung, was der Schirm
  zeigte (Fastboot-Schirm oder dunkel), steht noch aus.
2026-11-01 14:37:51 — Kabelprobe nach Gregors Meldung
Gregor: "google logo kurz aufgeschienen" — ABOOT uebergibt also an das geladene Bild, es stirbt frueh.
Kabel umgedreht (direkt?), danach:
PIXEL3-SERIAL	 fastboot
current-slot: a
slot-retry-count:a: 0
slot-unbootable:a: yes
slot-retry-count:b: 3
RAM-Boot 14:35:44 mit umgedrehtem Kabel: Telnet bei t=0/15/31 zu, kein ACM. Gleiches Bild.
2026-11-01 14:39:07 — Plan nach Kabel- und Panel-Meldung
Gregor meldet: Google-Logo kurz, dann Fastboot. Kabelumdrehen (14:35:44) aendert nichts.
Konsequenz: ABOOT uebergibt an das geladene Bild; das Bild stirbt nach Sekunden.
Bootloader b1c1-0.4-7617406 + Baseband g845-00194-210812-B-7635520 passen zu
blueline-sp1a.210812.016.c2. Offizielles Factory-Paket geladen von
  https://dl.google.com/dl/android/aosp/blueline-sp1a.210812.016.c2-factory-fa981d87.zip
  (2023854136 Bytes, aria2c, factory-download/; Entpacken von boot/dtbo/vbmeta/vbmeta_system).
Erster Test damit: RAM-Boot des Android-factory boot.img (dtbo_a unberuehrt, kein Write).
  Ueberlebt Android -> Hardware/ABOOT in Ordnung, Fehler sitzt im Referenzbild oder
  an der dtbo-Overlay-Kopplung; stirbt auch Android -> hardwarenah (Spannung/WDT).
Nebenbefund: reboot(ohne Argument) bei unbootable:a startet Slot b NICHT automatisch
  (retry b blieb 3); noetig waere set_active b — bewusst zurueckgestellt.
2026-11-01 14:43:27 — RAM-Boot des ANDROID-factory boot.img
SHA entpackt/pruefsummen (factory-download/entpackt/):
  boot.img 5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e (67108864 B, = factory-spiegel)
  dtbo.img ff7bd6daa08351a3c72992ded9a45d6f50f349d30dc68b1d0cd2eb426f8ab42d (8388608 B)
  vbmeta.img 007c923026a3d152c978b1e1643424e8e06b504f392639c6fc3aa9a4cb16a876 (8192 B)
  android-info.txt: require version-bootloader=b1c1-0.4-7617406, baseband g845-00194-210812-B-7635520 (beide = Telefon)
  zip-sha fa981d87b6b28a1996161accbb147f46fe29663bb2ce6cc13dc9e500cbc59c93 = oeffentlich genannter SHA.
RAM-Boot 14:41:54: Sending OKAY, Booting OKAY 3.5s. USB: t=0 4EE0, t=5..10 kein Geraet
(Kernel uebernimmt), t=16 zurueck als 4EE0 = Neustart zurueck in Fastboot, vor adbd/MTP.
AndroidFactory-Bild stirbt also INNERHALB ~12 s ebenso wie die pmOS-Referenz.
Hypothese verschaerft: geraeteseitig (Spannungseinbruch/Brownout oder ABOOT-Uebergabe-
defekt), nicht bildseitig — zwei vellige Bilder sterben heute identisch, gestern ueberlebte die Referenz.
2026-11-01 15:01:54 — Slot-b-Wiederherstellung auf Factory SP1A.210812.016.c2 (Freigabe: Gregor 14:4x)
slot-retry-count:b: 3
slot-unbootable:b: no
2026-11-01 15:02:47 — Slot-Boot von b (Stock-Android SP1A.c2: boot/dtbo/vbmeta geflasht, set_active b)
15:02:09 reboot. USB: t=0 4EE0, t=9 kein Geraet (Kernel laeuft), t=19 zurueck als 4EE0.
Also: Slot b wurde gestartet (Zaehlerpruefung folgt) und starb nach ~15 s. Stock-Android ebenfalls tot.
current-slot: b
slot-retry-count:b: 2
slot-unbootable:b: no
battery-voltage: 4243
slot-retry-count:a: 0
slot-unbootable:a: yes
OEM-Versuch oem uart enable:
OKAY [  0.089s]
Finished. Total time: 0.089s
2026-11-01 15:03:59 — ABOOT-OEM-Bestand
oem help: ungueltig. gueltig: oem uart enable (OKAY 15:02), oem ramdump enable/disable (OKAY).
oem uart enable war 15:02 OKAY, uart status 15:0x OKAY (enabled), ramdump danach enable.
Reboot-Zaehler vor naechstem Versuch: current-slot b, retry b 2, unbootable b no.
slot-retry-count:b: 2
2026-11-01 15:06:01 — Bootloop aus b beendet, Zustand
current-slot: b
slot-retry-count:b: 0
slot-unbootable:b: yes
slot-retry-count:a: 0
slot-unbootable:a: yes
2026-11-01 15:06:12 — Referenz zurueck nach boot_b, Slot-Boot-Test (RAM-Boot heutetoedlich?)
SHA boot_b-Inhalt vor dem Flash war Factory 5c1ce19e; neuer Inhalt ref ed2c225f (geprüft oben).
2026-11-01 15:10:23 — PSTORE-Befund + dtbo-Hypothese
config.gz: PSTORE=y PSTORE_RAM=y PSTORE_CONSOLE=y CRASH_DUMP=y MAGIC_SYSRQ=y; DT ohne ramoops-Knoten;
splash@9d400000..9f7fffff nomap belegt; pstore mountet leer. Ramoops-Modulweg rettet nichts ueber Neustart.
Ram-Boot 14:06 lief mit current-slot a => Overlay dtbo_a (unbekannt, nie gesichert). Slot-Boot 15:06
mit current-slot b => Overlay dtbo_b (Factory ff7bd6da) und UEBERLEBT (Telnet 73s, Gadget D001 bei 11s).
Test: Ram-Boot JETZT mit current-slot b.
2026-11-01 15:37:08 — RAM-Boot-Auflsung
RAM-Boot der Referenz mit current-slot b (dtbo_b gueltig, Factory ff7bd6da):
  15:35:26 boot OKAY; Gadget 0xD001 ab t=23s; Telnet offen bei t=72s; ueberlebt.
RAM-Boot mit current-slot a (dtbo_a leer, seit 28.10. dokumentiert): viermal
  um 14:06/14:09/14:11/14:18 auf den ~13-s-Tod gefallen. Erklarung: ABOOT
  haengt die leere dtbo-Partition als Overlay an (cmdline zeigt dtbo_idx=8),
  der Hauptkernel-Baum wird unbrauchbar. Der Sonderfall vom 31.10. 20:21
  (Leben mit leerem dtbo_a) bleibt ungeklaert; vermutlich dasselbe 13s-
  Neustart-Muster, das damals erst spaeter im Fastboot landete (Boot-into-
  Bootloader-Schalter von busybox reboot bootloader). Fuer den Bringup-
  Ablauf ist das gleichgueltig: Slot b + dtbo_b ist der verlaessliche Pfad.
Konsequenz v0z-Umbau: boot_b als Ziel, restart2 (0xa1b2c3d4, bootloader) am
  Init-Ende, dtbo_b unangetastet, Auslese ueber Referenz-Telnet.
2026-11-01 16:19:19 — Vorbereiten: dtbo_a mit Factory-dtbo fuellen (Claude-Plan, Gregor-Freigabe)
16:27:15 --- Rueckweg-Umbau nach Claude-Check-in 16:1x (Gregor-Freigabe) ---
16:27:15 Fehler berichtigt: 'dtbo nie angefasst' um 14:20 war falsch; dtbo_b wurde um 15:01
16:27:15 mit Factory dtbo.img (ff7bd6da…) geflasht, dtbo_a blieb leer. Jetzt: dtbo_a fuellen.
16:27:15 Schritt 0: Rueckweg-Zaehler — vor allem Retry b (stand 1) wieder auf 3.
16:27:20 Fastboot bereit nach 5s
16:27:20 vorher current-slot         current-slot: b
16:27:20 vorher slot-retry-count:a   slot-retry-count:a: 0
16:27:20 vorher slot-retry-count:b   slot-retry-count:b: 0
16:27:21 vorher slot-unbootable:a    slot-unbootable:a: yes
16:27:21 vorher slot-unbootable:b    slot-unbootable:b: yes
2026-11-01 16:31:51 — Ueberraschung: slot-unbootable:b war um 16:27 ja (retry b 0)
15:34:18 zeigte noch retry b 1 / unbootable b no. Zwischen 15:35 und 16:27 muss
ein richtiger Slot-b-Start stattgefunden und nicht durchgelebt haben. Moeglich:
der restart2-Rueckweg um 15:34 fuehrte zwar sofort nach Fastboot, aber ABOOT
zaehlte einen Slot-Start; spaeter (Tastendruck oder Automatik) lief Slot b an
und wurde bei 0 auf unbootable gestellt. boot_b-Inhalt ist unveraendert Referenz
(ed2c225f), dtbo_b/vbmeta_b Factory. Auffuellen mit --set-active ist daher sicher.
current-slot: b
slot-retry-count:b: 3
slot-unbootable:b: no
SHA dtbo-Quelle OK (ff7bd6daa08351a3c72992ded9a45d6f50f349d30dc68b1d0cd2eb426f8ab42d)
Finished. Total time: 0.855s
current-slot: a
16:34:15 TEST der dtbo-These: RAM-Boot der Referenz mit current-slot a und JETZT gefuelter dtbo_a (Factory ff7bd6da). Erwartung: ueberlebt (Gadget D001, Telnet). Vier Todesfaelle heute 14:06-14:18 hatten leere dtbo_a.
16:34:26 boot rc=0               OKAY [  9.963s] Finished. Total time: 10.752s 
16:34:28 t=  0s usb=0x4EE0 telnet=zu
16:34:58 t= 31s usb=0xD001 telnet=zu
16:35:14 t= 47s usb=0xD001 telnet=zu
16:35:43 UEBERLEBT: Telnet offen bei t=76s (Gadget war ab dem ersten Guck da)
16:35:44 Nachweis laufend: cat /proc/cmdline | tr ' ' '\n' | grep -E 'slot_suffix|dtbo_idx' | postmarketOS debug shell | https://postmarketos.org/debug-shell |  |   Device: Google Pixel 3
16:38:42 Referenz: sync; reboot gesendet (Boot-to-bootloader -> Fastboot)
16:40:25 Fastboot bereit: False nach 103s
2026-11-01 16:42:31 — GERAET schweigt: 'sync; reboot' aus der Referenz-Shell (16:38:42)
liess es vollstaendig vom Baum verschwinden (0 Google-Geraete, kein ACM, kein Telnet,
kein Fastboot, 4+ Minuten). Naechster naher Grund: die Referenz-PID-1-Kette traegt
Traps (pmos_getty/init_2.sh), nacktes reboot ist dort ein Münzwurf — Regel: nur
'sync; reboot -f' oder /tmp/restart2. Wächter läuft; bis dahin Tastenaktion noetig.
16:45:32 GERÄT WIEDER DA usb-produkt=50475
16:45:32 Wächter aus
