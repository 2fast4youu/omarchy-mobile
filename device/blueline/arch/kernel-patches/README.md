# Kernel-/DT-Patches für Omarchy Mobile auf dem Pixel 3 (blueline)

Basis ist `linux-sdm845` (7.1.0-rc1-sdm845) bei `85f1df2a4ec71d7a91dd95a7a49f889d1595ffa8`.

Anwenden im Kernel-Baum:

```sh
cd linux-sdm845
git apply /pfad/zu/0001-omarchy-mobile-blueline.patch
make ARCH=arm64 LLVM=1 O=/out -j$(nproc) Image.gz dtbs modules
```

Die ROM-Kernelkonfiguration aktiviert `CONFIG_NFC_NXP_NCI=m` und
`CONFIG_NFC_NXP_NCI_I2C=m` für den NXP-Controller. Die Standalone-Init lädt
die passenden NFC-Module in Abhängigkeitsreihenfolge.

`CONFIG_QCOM_MODEMSMEM=m` liefert die Plattformdaten in SMEM-Eintrag 134.
Die Standalone-Init lädt `modemsmem` und `ipa`, bevor sie das Modem startet.
Der GPL-Treiber stammt aus der Patchserie von Richard Acayan und David Heidelberg. [Linux-Kernel-Patch](https://lists.openwall.net/linux-kernel/2026/09/06/26)

## Änderungen

| Datei | Änderung | Grund |
|---|---|---|
| `arch/arm64/boot/dts/qcom/sdm845-google-common.dtsi` | Touchscreen auf I²C2, Kameras, Bluetooth, Ramoops und Modem-Firmware. Lautsprecher über CS35L36 und QUAT_TDM, Mikrofone über WCD9340 und SLIMbus. | Der WCD9340-Reset liegt auf GPIO 64, der Interrupt auf GPIO 54. Der Codec nutzt RPMH LN_BB_CLK3. |
| `arch/arm64/boot/dts/qcom/sdm845-google-common.dtsi` | IMX363 auf CCI0 an `0x1a`, GPIO 80 als aktiv-low und MCLK0 auf GPIO 13. | Die Pixel-3-Werkskonfiguration speichert die 8-Bit-Adresse `0x34`. Mit allen drei Korrekturen lieferte die Rückkamera auf dem Testgerät Frames in 1920 × 1080 und 4032 × 3024. |
| `arch/arm64/boot/dts/qcom/pm8998.dtsi` | Label für die RTC. | Der Geräteknoten markiert die RTC als Wakeup-Quelle. |
| `drivers/media/i2c/imx363.c` | `xclk` optional, Regler optional, Chip-ID-Fehler toleriert (Notifier bindet trotzdem), Regler-Fehlerbehandlung | Rückkamera soll probe-en statt zu blockieren |
| `drivers/media/i2c/imx355.c` | `cur_mode` = kleinster Mode (820×616), `get_selection` implementiert | libcamera braucht Crop-Rechtecke; sdm845-CAMSS kann keine 3280×2464-Frames |
| `drivers/power/supply/pmi8998_fg.c` | `CHARGE_FULL`/`CHARGE_NOW`/`CHARGE_FULL_DESIGN` | UPower braucht `energy-full` für die Prozentanzeige |
| `drivers/power/supply/qcom_smbx.c` | SMB2: `APSD_START_ON_CC_BIT` in der Init-Sequenz | Ohne das Bit bleibt `usb_type` „Unknown" |
| `drivers/regulator/fixed.c` | `gpiod_direction_output()` nach dem GPIO-Request | Fixed-Regulator trieb seinen Enable-Pin nicht |
| `fs/file.c` | `get_unused_fd_flags`: `O_CLOEXEC \| O_ACCMODE` erlaubt | libcamera öffnet dma-bufs mit `O_RDWR` |
| `fs/notify/group.c` | `fsnotify_wait_marks_destroyed()` deaktiviert | SRCU-Deadlock blockierte Suspend (quickshell in D-State) |
| `drivers/gpu/drm/msm/dsi/phy/dsi_phy_10nm.c` | Debug-Ausgabe reduziert | Rauschen im Log |

Die Mikrofonbeschaltung basiert auf [David Heidelbergs Pixel-3-Audioserie v7](https://lore.kernel.org/linux-sound/20261111-pixel3-audio-v7-0-ecf28efc5c33@ixit.cz/).

## Bekannte Einschränkungen

- **Rückkamera (IMX363)**: Megapixels verwendet 1920 × 1080. Autofokus,
  Stabilisierung und Videoaufnahme stehen zur Abnahme aus.
- **libcamera 0.7.2** erwartet SINK- und SOURCE-Pads. Die Sensor-Patches stellen beide bereit.
