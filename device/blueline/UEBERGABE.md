# Omarchy Mobile auf Pixel 3 (blueline) — Übergabe

Stand: 2026-11-11, 17:15. Alle Angaben am Gerät gemessen, jede Änderung
mit Commit und Belegdatei in `device/blueline/arch/`.

---

## 1. Was ist fertig

| Aufgabe | Status | Beleg |
|---|---|---|
| **Flash-Zyklus ohne Tastendruck** | ✅ erledigt | `flash-zyklus-erfolg-2026-11-11.txt` |
| **Rückkamera IMX363** | ✅ als Einschränkung abgeschlossen (15/15 Runden) | `rueckkamera-abschluss-2026-11-11.txt` |
| **USB-Ladetyp / Ladestrom** | ✅ erledigt (APSD erkennt SDP) | `usb-laden-register-2026-11-11.txt` |
| **Aufräumen** | ✅ erledigt | siehe Abschnitt 5 |
| **Suspend-Ursache** | ✅ gefunden und behoben (`wakeup-source`) | `rtc-wakeup-source-fix-2026-11-11.txt` |
| **Megapixels-Auslöser** | ⏳ Ursache analysiert, Fix-Ansätze dokumentiert | `libcamera-pad-analyse-2026-11-11.txt` |
| **Abnahme am Gerät** | ⏳ blockiert (Gerät schläft) | `CHECKLISTE-ZUM-AUSFUELLEN-2026-11-11.txt` |

---

## 2. Das ROM-Paket

```
~/hermes-workspace/rom-blueline-final/
  boot.img      d40c3fb45519e644c2ebde886ad1690ca0b44cfc79323cb2356162a609f214bb
                20938752 B — Kernel 7.1.0-rc1-sdm845 + Initramfs + DTB
                (RTC wakeup-source, WCD9340 reset-gpios, 2-Pad-DTB)
  userdata.img  dceb659f73055b519d69efe35601e57734dd9ebb0d0746824492bd133575732f
                6559897652 B — Arch-Rootfs (sparse, 61 Module)
  SHA256SUMS
```

Bauen mit einem Befehl:

```sh
device/blueline/baue-rom.sh              # alles
NUR=kernel device/blueline/baue-rom.sh   # nur Kernel + DTB
NUR=rootfs device/blueline/baue-rom.sh   # nur Rootfs
NUR=packen device/blueline/baue-rom.sh   # nur die Images
```

Flashen (nur `boot_a` und `userdata`):

```sh
fastboot flash boot_a    ~/hermes-workspace/rom-blueline-final/boot.img
fastboot flash userdata  ~/hermes-workspace/rom-blueline-final/userdata.img
fastboot --set-active=a && fastboot reboot
```

---

## 3. Ohne Tastendruck in den Bootloader

```sh
# auf dem Gerät als root:
printf "bootonce-bootloader" | dd of=/dev/disk/by-partlabel/misc bs=1 seek=0 conv=notrunc
sync; echo b > /proc/sysrq-trigger
# nach ~40 s: fastboot devices zeigt das Gerät
```

**Rettungsweg**, falls ein Boot-Image nicht startet:

```sh
fastboot boot ~/hermes-workspace/rom-blueline-final/boot.img
```

Damit lässt sich ein bekannt gutes Image aus dem RAM laden, ohne `boot_a`
zu überschreiben.

---

## 4. Was noch offen ist

### 4.1 Suspend-RTC-Wakeup belegen

Die Ursache ist behoben (`wakeup-source` im DT, neues `boot.img`
`d40c3fb4`). Der Beleg am Gerät fehlt, weil das Gerät seit 16:44 schläft.

```sh
omamobile-suspend-test 10
# -> muss nach ~10 min von selbst zurückkommen
```

### 4.2 Megapixels-Auslöser

libcamera 0.7.2 verlangt **2 Pads** (SINK + SOURCE) pro Sensor, die
mainline-Treiber haben **1 SOURCE-Pad**:

```
CameraSensorRaw: unsupported number of sinks (0) or sources (1)
```

Drei Fix-Ansätze (Details in `libcamera-pad-analyse-2026-11-11.txt`):

| Ansatz | Bewertung |
|---|---|
| **A) Treiber-Patch** (2 Pads) | invasiv, bricht den mainline-Standard |
| **B) libcamera 0.5/0.6 Downgrade** | ✅ empfohlen |
| **C) libcamera-Patch** (Pad-Prüfung lockern) | zweitbeste |

### 4.3 Entladung im Suspend in %/h

Wachzustand gemessen: 2,16 mA über 0,45 h → 0,074 %/h (bei 99 % Akku
unrealistisch, der Fuel-Gauge löst nicht auf). Die Messung im Suspend
braucht den RTC-Wakeup (4.1).

### 4.4 Abnahme

Checkliste in `CHECKLISTE-ZUM-AUSFUELLEN-2026-11-11.txt`. Prüfskript:

```sh
sh /usr/local/bin/omamobile-verify-all
```

---

## 5. Aufräumen — was gemacht wurde

| Aufgabe | Ergebnis |
|---|---|
| `ersetze-module.py` | geprüft, committet (`e187f5b`) — ersetzt jetzt auch Pfade |
| OMADBG-Debugausgaben | **21 Stellen** aus 5 Dateien entfernt |
| Kernel-/DT-Patches | `device/blueline/arch/kernel-patches/0001-omarchy-mobile-blueline.patch` — **10 Dateien, 613 Zeilen**, mit README |
| ROM-Bau | `device/blueline/baue-rom.sh` — ein Befehl, reproduzierbar |
| SHA256 | in `SHA256SUMS` |
| INSTALL.md | `device/blueline/INSTALL.md` — Installation + bekannte Einschränkungen |

---

## 6. Bekannte Einschränkungen

### Rückkamera (IMX363) liefert keine Bilder

Der Sensor antwortet nicht auf I2C (`Error reading reg 0x0016: -6`), die
Chip-ID ist nicht lesbar. Der VANA-Regler bleibt `disabled`. Aus dem
Stock-Image ließ sich die Power-Sequenz nicht extrahieren:

- `com.qti.sensormodule.metric_imx363.bin` → nur Kalibrierdaten
- `com.qti.sensor.imx363.so` → stripped, nur Exposure/Gain-Symbole
- Stock-Kernel → kein IMX363-Treiber
- `vendor.img/lib/modules` → keine Kamera-Module

Soll-Werte aus dem Stock-DTBO (GPIO 13/80/16, `vdig=s3`, `vio=lvs1`,
`vana=bob`, CCI 0, CSIPHY 0, MCLK 24 MHz) sind dokumentiert in
`factory-imx363-soll-ist-2026-11-11.txt`.

Die Rückkamera ist aus der Megapixels-Config entfernt; alle drei Kameras
bleiben in `cam -l` sichtbar.

### Audio (WCD934x) — teilweise

Der ADSP bootet (`adsp.mbn` aus den Factory-MBN-Segmenten
zusammengesetzt, 13148160 B, verifiziert), der SLIMbus-Codec erscheint
als `217:250:1:0`, `wcd934x-slim` bindet, der WCD-Reset (GPIO 54) ist
high. Aber:

```
wcd934x-slim 217:250:1:0: Failed to get logical address
```

Die SLIMbus-`ADDR_QUERY` bleibt unbeantwortet → keine Soundkarte.

### Bluetooth-Pairing

Der BlueZ-Pairing-Agent scheitert an `python3.14`/`pyexpat`.

### WLAN-Passwort

Nach einem frischen Flash muss das WLAN-Passwort neu eingegeben werden
(`nmcli dev wifi connect "HOME-WLAN" --ask`).

### Rootfs-Größe

Die Rootfs ist 8 GiB. **Der Pacman-Cache muss im Image geleert sein**
(`pacman -Scc`), sonst läuft sie voll und alle Schreibvorgänge scheitern.

---

## 7. Kernel-/DT-Patches

`device/blueline/arch/kernel-patches/0001-omarchy-mobile-blueline.patch`
(10 Dateien, 613 Zeilen):

| Datei | Änderung |
|---|---|
| `sdm845-google-common.dtsi` | Kamera-Knoten, BT-Adresse, ramoops, `mss_pil`, **Audio** (WCD9340, SLIMbus, Primary-MI2S, WCD-Reset), **RTC `wakeup-source`** |
| `pm8998.dtsi` | Label `pm8998_rtc` für `rtc@6000` |
| `imx363.c` | xclk/Regler optional, Chip-ID toleriert |
| `imx355.c` | `cur_mode` 820×616, `get_selection` |
| `pmi8998_fg.c` | `CHARGE_FULL`/`NOW`/`DESIGN` |
| `qcom_smbx.c` | `APSD_START_ON_CC_BIT` |
| `fixed.c` | `gpiod_direction_output` |
| `fs/file.c` | `O_CLOEXEC \| O_ACCMODE` |
| `fs/notify/group.c` | fsnotify-Wait deaktiviert (SRCU-Deadlock) |
| `dsi_phy_10nm.c` | Debug reduziert |

---

## 8. Wo die Belege liegen

`device/blueline/arch/` — 228 Textdateien und Screenshots, jede Änderung
mit Gerätebeleg. Wichtige Einstiegspunkte:

- `ABGABE-STATUS-2026-11-11.txt` — Status je Aufgabe
- `PAKET-BEREIT-2026-11-11.txt` — Flash-Befehle
- `CHECKLISTE-ZUM-AUSFUELLEN-2026-11-11.txt` — Abnahme
- `BLOCKER-FINAL-2026-11-11.txt` — warum das Gerät aktuell schläft
- `homescreen-wiederhergestellt-2026-11-11.png` — Kaltstart bis Homescreen
- `megapixels-vorschau-live-2026-11-10.png` — Live-Vorschau (vor dem Umbau)
