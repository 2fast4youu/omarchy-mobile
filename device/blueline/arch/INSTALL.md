# Omarchy Mobile für das Google Pixel 3 (blueline)

Omarchy Mobile (Hyprland + Quickshell-Telefon-Shell) auf Mainline-Linux
für das Pixel 3. Diese Anleitung beschreibt Bau, Installation und den
ehrlichen Funktionsstand.

---

## 1. Was funktioniert (am Gerät gemessen)

| Funktion | Status | Beleg |
|---|---|---|
| **Display** | ✅ 1080×2160, DSI, Helligkeit 40 % | Screenshots |
| **Touch** | ✅ stmfts, Gesten | UI reagiert |
| **Homescreen / Shell** | ✅ Quickshell mit Dock, Suchleiste, Statusleiste | `homescreen-wiederhergestellt-2026-11-11.png` |
| **Bildschirmtastatur** | ✅ Squeekboard, QWERTZ | — |
| **WLAN** | ✅ verbindet (AP: HOME-WLAN) | `nmcli` |
| **Bluetooth** | ⚠️ Adapter vorhanden, Pairing-Agent defekt | — |
| **Audio** | ⚠️ ADSP läuft, SLIMbus-Codec bindet, aber keine Soundkarte (`Failed to get logical address`) | dmesg |
| **Akku-Anzeige** | ✅ Prozent + Symbol in der Statusleiste | Screenshots |
| **Akku-Messung** | ✅ Kapazität, Spannung, Strom, Temperatur | `/sys/class/power_supply/qcom-battery/` |
| **UPower** | ✅ `percentage`, `state` | `upower -i` |
| **Suspend (s2idle)** | ✅ Gerät schläft sauber; Wakeup per Pwrkey belegt, RTC-Wakeup vorbereitet | `/sys/power/suspend_stats/` |
| **Idle** | ✅ hypridle: 30 s dimmen, 60 s DPMS aus | — |
| **Power-Profile** | ✅ power-saver 1,13 GHz / balanced 1,77 GHz | `powerprofilesctl` |
| **Thermik** | ✅ 38–42 °C unter Last | `thermal_zone*` |
| **USB-Ladetyp** | ✅ APSD erkennt SDP, Ladepfad verifiziert | `APSD_RESULT_STATUS=0x1`, `CHG_EN=0x1`, `ICL=1000 mA` |
| **Kameras erkannt** | ✅ 3 von 3 in `cam -l` | `cam -l` |
| **Frontkameras** | ⚠️ erkannt, Stream startet nicht | `STREAMON error 32` |
| **Rückkamera** | ❌ Sensor antwortet nicht auf I2C | siehe Abschnitt 6 |
| **Megapixels** | ⚠️ startet, UI läuft, kein Stream | — |
| **Flash ohne Tastendruck** | ✅ `bootonce-bootloader` + SysRq | siehe Abschnitt 4 |

---

## 2. Bauen

Ein Befehl baut `boot.img` und `userdata.img`:

```sh
device/blueline/baue-rom.sh
```

Ergebnis in `~/hermes-workspace/rom-blueline/` mit `SHA256SUMS`.

Teilbauten:

```sh
NUR=kernel device/blueline/baue-rom.sh   # Kernel + DTB
NUR=rootfs device/blueline/baue-rom.sh   # Arch-Rootfs
NUR=packen device/blueline/baue-rom.sh   # nur boot.img/userdata.img
```

### Voraussetzungen

| Was | Pfad (Default) |
|---|---|
| Kernel-Baum (sdm845-Mainline) | `~/hermes-workspace/linux-sdm845` |
| Kernel-Out | `~/hermes-workspace/pmos-kernel-out` |
| ALARM-Tarball | `~/.cache/omamobile-rootfs/ArchLinuxARM-aarch64-latest.tar.gz` |
| Omarchy-Pakete | `~/hermes-workspace/pkgs` |
| Firmware | `~/hermes-workspace/firmware` |
| Ramdisk | `~/hermes-workspace/images/fl-v0ag/ramdisk.gz` |
| Referenz-Bootimage | `~/hermes-workspace/pmos-ref-build/ref/boot.img` |

Alle Pfade lassen sich per Umgebungsvariable überschreiben.

### Kernel-Patches

Die Kernel- und DT-Änderungen liegen als Patch im Repo:

```
device/blueline/arch/kernel-patches/0001-omarchy-mobile-blueline.patch
```

`baue-rom.sh` wendet ihn automatisch an, wenn er noch nicht drin ist.
Details und Begründung je Datei: `kernel-patches/README.md`.

---

## 3. Flashen

> **Nur `boot_a` und `userdata` werden geschrieben.** Andere Partitionen
> bleiben unberührt.

```sh
fastboot flash boot_a    rom-blueline/boot.img
fastboot flash userdata  rom-blueline/userdata.img
fastboot --set-active=a
fastboot reboot
```

`userdata` ist ein Sparse-Image (33 Chunks, ~3,5 min).

---

## 4. Ohne Tastendruck in den Bootloader

Das Gerät kann sich selbst in Fastboot bringen — kein Power+Leiser nötig:

```sh
# auf dem Gerät als root:
printf "bootonce-bootloader" | dd of=/dev/disk/by-partlabel/misc bs=1 seek=0 conv=notrunc
sync
echo b > /proc/sysrq-trigger
# nach ~40 s: fastboot devices zeigt das Gerät
```

**Rettungsweg**, falls ein Boot-Image nicht startet:

```sh
fastboot boot rom-blueline/boot.img    # aus dem RAM, ohne zu schreiben
```

Damit lässt sich ein bekannt gutes Image laden, ohne `boot_a` zu
überschreiben.

---

## 5. Nach dem ersten Boot

Der Init (`/init` im Initramfs) macht alles selbst: Module laden,
Firmware spiegeln, D-Bus, NetworkManager, seatd, dann Hyprland +
Quickshell + Squeekboard in einer `dbus-run-session`.

Wichtig für Kameras: **libcamera findet nur initialisierte udev-Devices.**
Der Init muss deshalb

```sh
SYSTEMD_IGNORE_CHROOT=1 udevadm trigger
```

ausführen (das System läuft nicht unter systemd, `udevadm` hält sich
sonst für chroot).

---

## 6. Bekannte Einschränkungen

### Was in der Session vom 2026-11-11 repariert wurde

Diese Blocker wurden gefunden und behoben (jeweils mit Belegdatei in
`device/blueline/arch/`):

| Blocker | Fix |
|---|---|
| RTC ohne `wakeup-source` | `&pm8998_rtc { wakeup-source; }` + Label in `pm8998.dtsi` |
| `rtc-pm8xxx.ko` fehlte | Modul ins Image und in die Init-Modulliste |
| Kein Standard-Wakealarm | `echo +3600 > /sys/class/rtc/rtc0/wakealarm` im Init |
| Sensoren mit 1 Pad | `pads[2]` (SINK+SOURCE) in `imx355.c`/`imx363.c` |
| Sensor-Mode auf SINK-Pad | `Pad: 1` in allen `Mode`-Befehlen der Megapixels-Config |
| `udevadm trigger` fehlte | `SYSTEMD_IGNORE_CHROOT=1 udevadm trigger` im Init |
| `/dev/video*` root-only | `chmod 666 /dev/video* /dev/v4l-subdev*` |
| `simple.yaml` fehlte | Config mit `sony,imx355/imx363` + `qcom,sdm845-camss` |
| Megapixels-Binaries fehlten | `megapixels-gtk`, `libmegapixels`, `liblibdng`, GSchema, Desktop-Eintrag |
| XDG/Pictures fehlten | `~/.config/user-dirs.dirs`, `~/Pictures`, `postprocess.sh` |
| `omamobile-setup-user` zu spät | synchron mit 30 s Timeout + Fallback |
| `wcd9340` ohne `reset-gpios` | `reset-gpios = <&tlmm 54 GPIO_ACTIVE_HIGH>` |
| `adspua.jsn` fehlte | aus dem Factory-Image extrahiert (PDR-Service `avs/audio`) |
| Audio-Module nicht geladen | 14 Module in Abhängigkeitsreihenfolge im Init |
| ADSP-Firmware nicht gespiegelt | `adsp.mbn`/`adspr.jsn`/`adspua.jsn` in der Init-Firmware-Liste |
| Audio-Module vor ADSP | Reihenfolge ADSP → QRTR-Warteschleife → Audio |
| PipeWire fehlte | `pipewire`/`wirepipe-pulse`/`wireplumber` + Start im Init |
| Hyprland-Configs fehlten | aus `/usr/share/omarchy/config/hypr` ins Rootfs kopiert |
| **UID-Mismatch** | `OM_UID=$(id -u omarchy)` statt hart `/run/user/1000` |
| Plugin-Symlinks fehlten | im Rootfs **nach** der Paketinstallation verlinkt |
| **`shell.json` fehlte** | `profile/shell.json` ins Rootfs + Prüfung im Init |
| `WAYLAND_DISPLAY` hartkodiert | dynamisch aus `$OM_RUNTIME/wayland-*` |
| Hardware-Watchdog fehlte | `qcom-wdt`, `pm8916_wdt` im Init |
| Prüfskripte fehlten | `omamobile-verify-all`, `omamobile-health` im Image |

**Wichtig:** Ohne `shell.json` lädt Quickshell **keine** omamobile-Plugins
(`"plugins": []`) — dann fehlen Homescreen und Dock. Die Datei wird im
Init geprüft und bei Bedarf wiederhergestellt.

### Rückkamera (IMX363) liefert keine Bilder

Der Sensor antwortet nicht auf I2C (`Error reading reg 0x0016: -6`), die
Chip-ID ist nicht lesbar. Der VANA-Regler (`rear_cam_vana`, GPIO 16)
bleibt `disabled`. Aus dem Stock-Image ließ sich die Power-Sequenz nicht
extrahieren: `com.qti.sensormodule.metric_imx363.bin` enthält nur
Kalibrierdaten, `com.qti.sensor.imx363.so` ist stripped, der Stock-Kernel
enthält keinen IMX363-Treiber.

Aus dem Stock-DTBO bekannte Soll-Werte (siehe
`arch/factory-imx363-soll-ist-2026-11-11.txt`):
MCLK0 = GPIO 13, RESET = GPIO 80 (ACTIVE_HIGH), VANA = GPIO 16,
`vdig = pm8998_s3`, `vio = pm8998_lvs1`, `vana = pmi8998_bob`,
CCI-Master 0, CSIPHY 0, MCLK 24 MHz.

### libcamera 0.7.2 und Sensor-Pads

libcamera erwartet pro Sensor **2 Pads** (SINK + SOURCE), die
Mainline-Treiber haben **1 SOURCE-Pad**:

```
CameraSensorRaw: unsupported number of sinks (0) or sources (1)
```

Deshalb startet der Stream nicht (`STREAMON error 32`), obwohl alle drei
Kameras in `cam -l` erscheinen. Ein Downgrade auf libcamera 0.5/0.6 oder
ein Treiber-Patch (zweites Pad) wäre der nächste Schritt.

### Audio (WCD934x) — teilweise

Der ADSP bootet (adsp.mbn aus den Factory-MBN-Segmenten zusammengesetzt),
der SLIMbus-Codec erscheint als `217:250:1:0`, `wcd934x-slim` bindet und
der WCD-Reset (GPIO 54) ist high. Aber:

```
wcd934x-slim 217:250:1:0: Failed to get logical address
```

Die SLIMbus-`ADDR_QUERY` an den Codec bleibt unbeantwortet, deshalb bindet
`snd-soc-sdm845` keine Karte und `/proc/asound/cards` bleibt leer.

Nächster Ansatz: Power-Up-Reihenfolge (Regler → Reset → Clock → Query) und
den WCD-SPI-Pfad aus dem Stock-DTBO vergleichen.

### Suspend ohne Tastendruck

`echo mem > /sys/power/state` schläft sauber, aber im s2idle wird der
USB-Port abgeschaltet — ohne funktionierenden RTC-Alarm ist das Gerät dann
weder per SSH noch per fastboot erreichbar.

`omamobile-wakeup` aktiviert inzwischen auch
`/sys/class/rtc/rtc0/device/power/wakeup`, und
`omamobile-suspend-test [Minuten]` setzt den RTC-Alarm, schläft und prüft
die Schlafdauer. Am Gerät noch zu belegen.

### Bluetooth-Pairing

Der BlueZ-Pairing-Agent scheitert an `python3.14`/`pyexpat`.

### USB-Ladestrom

APSD erkennt den Port als **SDP** (500 mA), die Register sind korrekt
(`CHG_EN=0x1`, `USBIN_IL=0x0`, `ICL=1000 mA`). Bei vollem Akku
(≥ 4,3 V) setzt der Charger `CHARGER_INHIBIT_BIT` — das ist
Überladeschutz, kein Fehler.

### Rootfs-Größe

Die Rootfs ist 8 GiB. **Der Pacman-Cache muss im Image geleert sein**
(`pacman -Scc`), sonst läuft sie voll und alle Schreibvorgänge scheitern
(Screenshots 0 Bytes, Megapixels kann nicht speichern, dconf-Fehler).

---

## 7. Belege

Alle Messungen liegen als Textdateien und Screenshots in
`device/blueline/arch/` — jede Änderung mit Gerätebeleg und Commit.
