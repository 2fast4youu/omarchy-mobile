# Omarchy Mobile auf dem Pixel 3 (blueline) — Stand 2026-11-05

## Flashen
1. Telefon in den Fastboot: **Power + Leiser ~10–15 s**.
2. `fastboot flash boot_a boot.img` (v0ba) und
   `fastboot flash userdata userdata.img` (8 GiB, sparse),
   `fastboot --set-active=a`, `fastboot reboot`.
   Gebuendelt: `device/blueline/arch/flash-buendel.sh`.
3. Nach dem Boot (ca. 40 s) startet die Sitzung automatisch:
   Hyprland, Quickshell (Telefon-Shell) und Squeekboard.

## Bedienung
- **Oben auf die Leiste tippen** → Quick Settings; dort die
  **Keyboard-Kachel** schaltet die Bildschirmtastatur.
- Der **App-Drawer** (Suchleiste unten) ruft die Tastatur beim Aufziehen
  (Launcher-Patch, Image fbab627b; im Paket noch 50a11a59 ohne Patch).
- Terminal: **Foot** (Dock) oder `fingerterm` (eigene Tastatur).
- SSH: `ssh -i ~/.ssh/omamobile_blueline root@172.16.42.1` (usb0).

## Zeit
Keine RTC. Die Init setzt zuerst die Bauzeit
(`/etc/omamobile-buildtime`), dann holt `omamobile-time-sync` die echte
Zeit aus dem HTTP-Date-Header über den Mac-Proxy (usb0, Port 3128).

## Bekannte Luecken
- **WLAN:** kein `CONFIG_BRCMFMAC` im Kernel, keine BCM4375-Firmware →
  kein `wlan0`. Netz nur ueber usb0/Proxy.
- **Slot-Erfolgsmarke:** fehlt (GPT-Attribut); nach drei Starts ohne
  Marke faellt ABOOT auf Fastboot. Fastboot-Laeufe buendeln.
- **Tastatur** erscheint nicht automatisch bei jedem Textfeld
  (Hyprland aktiviert das Input-Method-Protokoll nicht selbst); Kachel
  oder Launcher rufen sie.

## Was am Geraet belegt ist
- Display: DSI-1 connected/enabled, 1080x2160, msmdrmfb (Refgen-Fix).
- GPU: a630-Firmware im Initramfs, adreno initialisiert.
- Touch: ST FTS5 (`stmfts`) mit gpi.ko + udev-uevents.
- Shell: omamobile-Profil (home/back/bar), Quickshell.
- OSK: Squeekboard 1.43, 110 Layouts, SetVisible ueber den Session-Bus.
- Zeit: HTTP-Sync (21:22 UTC belegt).
