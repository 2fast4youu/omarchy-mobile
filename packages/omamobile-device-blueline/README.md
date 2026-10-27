<!-- SPDX-License-Identifier: MIT -->
# omamobile-device-blueline

Omarchy Mobile support for the Google Pixel 3 (`blueline`, SDM845): the
policy that keeps the phone's storage safe after the initramfs hands over,
the address of the USB link back to the laptop, and the power-key policy.

Nothing in this package is enabled that has not passed on a Pixel 3. The
first-light gates and their evidence are in
[`device/blueline/BRINGUP-M1.md`](../../device/blueline/BRINGUP-M1.md);
until they record a pass, no service in here claims anything about the
phone's radios, display or modem.

What it installs (all shared policy, identical to the other device
packages, none of it device-specific beyond the descriptor copy):

- `reboot-to` — `LINUX_REBOOT_CMD_RESTART2` reboot reasons; busybox
  `reboot` hangs on these bootloaders.
- The storage guard's continuation in Arch: the main LUN's whole-disk
  node is made inaccessible and desktop tooling ignores every partition
  but `userdata`.
- `20-usb-gadget.network` — keeps `usb0` at 172.16.42.1 for
  systemd-networkd (the initramfs's address), and `10-omamobile-usb.conf`
  keeps NetworkManager off it.
- `10-omamobile-power-key.conf` — a short power press opens Omarchy's
  system menu; the long press still resets in hardware.
- The `[omamobile]` repository: pacman's keyring dependency, the
  mirrorlist, and an install script that adds the repository once and
  never removes it.
- A copy of `device/blueline/device.conf`, so a phone can read its own
  descriptor from `/usr/share/omamobile/device.conf`.
