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
| **Audio** | ⚠️ PipeWire läuft, Ausgabe ungetestet | — |
| **Akku-Anzeige** | ✅ Prozent + Symbol in der Statusleiste | Screenshots |
| **Akku-Messung** | ✅ Kapazität, Spannung, Strom, Temperatur | `/sys/class/power_supply/qcom-battery/` |
| **UPower** | ✅ `percentage`, `state` | `upower -i` |
| **Suspend (s2idle)** | ✅ `success=3`, `fail=0`, Wakeup über Pwrkey | `/sys/power/suspend_stats/` |
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
