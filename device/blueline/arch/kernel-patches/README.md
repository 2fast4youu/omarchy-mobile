# Kernel-/DT-Patches für Omarchy Mobile auf dem Pixel 3 (blueline)

Basis: `linux-sdm845` (7.1.0-rc1-sdm845), Zweig mit sdm845-Mainline-Support.

Anwenden im Kernel-Baum:

```sh
cd linux-sdm845
git apply /pfad/zu/0001-omarchy-mobile-blueline.patch
make ARCH=arm64 LLVM=1 O=/out -j$(nproc) Image.gz dtbs modules
```

## Inhalt (9 Dateien, +258/−19)

| Datei | Änderung | Grund |
|---|---|---|
| `arch/arm64/boot/dts/qcom/sdm845-google-common.dtsi` | Kamera-Knoten: `camss`-Ports, `cci_i2c0/1`-Sensoren (imx363/imx355), VANA-Regler, Bluetooth-`local-bd-address`, `ramoops`, `mss_pil`-Firmware | Kamera + BT + Pstore |
| `drivers/media/i2c/imx363.c` | `xclk` optional, Regler optional, Chip-ID-Fehler toleriert (Notifier bindet trotzdem), Regler-Fehlerbehandlung | Rückkamera soll probe-en statt zu blockieren |
| `drivers/media/i2c/imx355.c` | `cur_mode` = kleinster Mode (820×616), `get_selection` implementiert | libcamera braucht Crop-Rechtecke; sdm845-CAMSS kann keine 3280×2464-Frames |
| `drivers/power/supply/pmi8998_fg.c` | `CHARGE_FULL`/`CHARGE_NOW`/`CHARGE_FULL_DESIGN` | UPower braucht `energy-full` für die Prozentanzeige |
| `drivers/power/supply/qcom_smbx.c` | SMB2: `APSD_START_ON_CC_BIT` in der Init-Sequenz | Ohne das Bit bleibt `usb_type` „Unknown" |
| `drivers/regulator/fixed.c` | `gpiod_direction_output()` nach dem GPIO-Request | Fixed-Regulator trieb seinen Enable-Pin nicht |
| `fs/file.c` | `get_unused_fd_flags`: `O_CLOEXEC \| O_ACCMODE` erlaubt | libcamera öffnet dma-bufs mit `O_RDWR` |
| `fs/notify/group.c` | `fsnotify_wait_marks_destroyed()` deaktiviert | SRCU-Deadlock blockierte Suspend (quickshell in D-State) |
| `drivers/gpu/drm/msm/dsi/phy/dsi_phy_10nm.c` | Debug-Ausgabe reduziert | Rauschen im Log |

## Bekannte Einschränkungen

- **Rückkamera (IMX363)**: Chip-ID wird nicht gelesen (Sensor antwortet nicht auf I2C),
  VANA-Regler bleibt `disabled`. Siehe `../rueckkamera-*.txt`.
- **libcamera 0.7.2** erwartet 2 Pads pro Sensor (SINK+SOURCE), die mainline-Treiber
  haben 1 SOURCE-Pad → `CameraSensorRaw: unsupported number of sinks (0) or sources (1)`.
