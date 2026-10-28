<!-- SPDX-License-Identifier: MIT -->
# Pixel 3 (blueline): first light

Status (2026-10-27): descriptor, plan and device package written; no Pixel 3
hardware in hand yet. Nothing in this file has been run on a blueline.
M1.1, the host-only first-light build, is done and evidenced below; no
fastboot or adb command has been run for it.
Upstream's board device tree is already built by our kernel: `sdm845-google-
blueline.dts` sits in the `omamobile` branch of linux-omarchy-mobile (tree
contents checked 2026-10-27), which is why this phone starts where the
Tensor ports did not: with a mainline board description whose drivers run
upstream on many other SDM845 boards.

**In one paragraph:** the Pixel 3 is the older-sibling Qualcomm phone of the
Pixel 4 family this repository already brings up. Its bootloader is ABOOT,
not Tensor ABL: it boots header-v2 images, matches appended device trees by
`qcom,msm-id`/`qcom,board-id`, keeps its slot flags in GPT partition
attributes, and has no `vendor_boot`, `init_boot` or `vendor_kernel_boot`.
The first light is therefore built from the recipe this generation's field
reports prove: an mkbootimg image at the postmarketOS deviceinfo's offsets
with the board DTB appended, our initramfs (dropbear, CDC NCM gadget, every
UFS block read-only), booted **from RAM with zero writes** before anything
touches slot B. The plan's gates then take calibration backups, write slot
B and `userdata`, and mark slot B bootable as CONTRIBUTING 3.1's named GPT
exception, captured sector by sector before and after.

## Development handset state (2026-10-27)

The way back is held off-device. **Correction 2026-10-27 (owner review):**
the first factory image pulled here, **Android 11 (RQ3A.211001.001,
Oct 2021)**, `blueline-rq3a.211001.001-factory-2cca4239.zip` (sha256
verified equal to the hash in its file name, `2cca42397f29cc3b032dbd2b627e65049ffd894be4801a39c292e663d01cbc71`),
ships bootloader **b1c1-0.3-7241706** (verified inside the unpacked zip at
`rq3a/blueline-rq3a.211001.001/bootloader-blueline-b1c1-0.3-7241706.img`)
while this handset runs **b1c1-0.4-7617406** — flashing RQ3A's flash-all
would *downgrade* the bootloader. The way back is therefore the last
official blueline factory image, **Android 12 (SP1A.210812.016.C2,
Jun 2022)**, `blueline-sp1a.210812.016.c2-factory-fa981d87.zip` —
downloaded 2026-10-27, sha256
`fa981d87b6b28a1996161accbb147f46fe29663bb2ce6cc13dc9e500cbc59c93`
verified equal to both the hash in its file name and Google's published
checksum; its payload `bootloader-blueline-b1c1-0.4-7617406.img`
(8,726,312 bytes, unpacked under `factory/sp1a/`) matches this handset's
`version-bootloader` bit for bit, so flashing it does NOT downgrade the
bootloader (the same build LineageOS documents for the b1c1-0.4 era:
`review.lineageos.org` vars/blueline, build_number 8618562).
`android-mainline/factory/` holds both zips; neither is ever flashed
without re-checking its bootloader version against `fastboot getvar
version-bootloader` first.

**Honest state of `boot_a`:** the Ubuntu Touch / postmarketOS `boot_a`
that ran this handset was overwritten by first-light flashes and the
intended `fastboot fetch` backup landed as a **0-byte file**
(`android-mainline/factory/boot_a-ut-backup.img`, verified size 0). It is
NOT bit-restorable; the way back to Android is the SP1A factory image
above, which **wipes user data** (owner accepted this on 2026-10-27).
Standing rule from this incident: **before any partition write, the
backup file for that partition must exist with nonzero size and a
recorded sha256 — verified, not assumed — or the write is logged as
destructive and re-consented.**

The port's handset arrived running **Ubuntu Touch on a postmarketOS base**
(the USB composite self-describes with serial `postmarketOS`,
`18d1:d001`, connected over a hub; `adb` on the host saw no adbd, so its
USB gadget exposes no adb function to the Mac). Stock Android therefore no
longer sits on a boot slot as-is: before any gate writes slot B, the owner
must have the matching **stock factory image saved off-device** as the way
back (BRINGUP-M1 M0/M1.5), and M1.0's getvars will show which slot the
Ubuntu Touch boot lives in. That the phone boots a postmarketOS-family
stack at all is useful evidence for M1.2 — a mainline-derived SDM845
kernel already drives this board's storage and display in that setup;
`uname -r` from it belongs in this note once a shell is reachable.

## Sources and facts

- [V, source, 2026-10-27] Upstream board DTS:
  [arch/arm64/boot/dts/qcom/sdm845-google-blueline.dts](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom/sdm845-google-blueline.dts)
  with `sdm845-google-common.dtsi` beside it: root `compatible =
  "google,blueline", "qcom,sdm845"`; `qcom,msm-id = <SDM845 0x20001>` and
  `qcom,board-id = <0x00021505 0>` for ABOOT's matching; `chosen`
  `stdout-path = "serial0:115200n8"` with `serial0 = &uart9`; a
  `simple-framebuffer` (`a8r8g8b8`) on the bootloader's splash region
  (`cont_splash_mem`, `0x9d400000` + 36 MiB) sized 1080x2160 by the board
  file; the panel node (`lg,sw43408`, reset GPIO 6, TE GPIO 12); `i2c2`
  enabled with a `ST,FTS @ 49` comment but no touch node yet; and the
  Wi-Fi node asking calibration variant `Google_blueline`. The same DTS is
  in [linux-omarchy-mobile](https://github.com/derekross/linux-omarchy-mobile)
  `omamobile` (directory listing checked 2026-10-27), so our kernel already
  builds the DTB; nothing has run it on a Pixel 3.
- [V, source] Boot image recipe proven on this phone by field reports
  (postmarketOS deviceinfo for `google-blueline`): fastboot flashing,
  `console=ttyMSM0,115200`, kernel offset `0x8000`, ramdisk offset
  `0x1000000`, tags offset `0x100`, base `0x0`, page size 4096, no
  Qualcomm QCDT, the board DTB **appended** to the image, and UFS sector
  size 4096. Its firmware packages (`firmware-google-blueline`,
  `firmware-google-blueline-dtbo`) are an inventory of which stock blobs
  exist, not a license to ship them: our rule stands, they come from the
  owner's own factory image.
- [V, this repo] The Pixel 4 notes
  ([BRINGUP-M1.md](../flame/BRINGUP-M1.md)) verified with `fastboot` on a
  real SM8150 phone of the same boot generation: `boot_a/b`, `dtbo_a/b`
  and `userdata` exist, there is no `vendor_boot`, `init_boot` or
  `vendor_kernel_boot`, and slot selection is GPT partition attributes
  (CONTRIBUTING 3.1, which still names no device). Blueline is expected to
  match; gate M1.0 checks the claim on this phone before anything is
  written.
- [V, reports, not ours] Published field notes for a mainline-kernel Pixel
  3 running as a daily phone
  ([device records](https://forge.caseytunturi.com/Fimeg/SouveraineOS/src/branch/public/saf/device/README.md),
  2026-07/08) report calls, SMS and LTE data working on it, and three
  operational notes for SDM845 mainline setups we adopt as risks to
  verify, not as facts: warm reboots can leave TrustZone/remoteproc state
  poisoned so they boot cold only; the WCN3990 ships no Bluetooth BD
  address and needs a persisted generated one; and the X20 modem answers
  QMI only once the `modemsmem` SMEM item is populated, else the probe
  waits with `DeviceNotReady`. None of it is claimed for our kernel here.

## The phone after first light

Slot A is stock Android and the way back, never written. Slot B holds our
`boot_b` (kernel + appended DTB + our initramfs) and, if gate M1.5 proves
the stock overlay interferes, our `dtbo_b`. `userdata` becomes the Arch
root. Every other block stays read-only behind the initramfs guard; the
allowlist the guard will carry is `boot_b dtbo_b userdata`. USB is the
only link during bring-up: CDC NCM at 172.16.42.1, like every other device
here.

## Gates

One change per boot, read-only first, human approves every write and every
reboot (AGENTS 1). No gate may run its write before the gate before it
passed on this phone, with the date and `uname -r` recorded beside it.

### M1.0 — arrive, unlock, capture (no writes beyond the unlock)

- Stock boot, `adb` on; record `ro.product.device`, `ro.boot.slot_suffix`,
  `ro.boot.flash.locked`, the bootloader version and active slot into
  `~/android/reference` (never committed). From fastboot, `getvar all`
  (scrub the serial) and `getvar partition-size:*`: this confirms or
  refutes the boot_a/b, dtbo_a/b, no-vendor_boot layout from the Pixel 4
  notes, and sizes `boot_b` for the image gate.
- Unlock is the owner's call and wipes `userdata` (Android's data, not
  the calibration partitions): `fastboot flashing unlock`, with written
  acceptance that until M1.6 the phone has only its stock slot. If the
  phone arrives locked with a stale Android, take the getvars first.
- Pass: partition table, sizes and slot state recorded. Risk: none beyond
  the unlock itself.

### M1.1 — build the first-light image (host only) — DONE 2026-10-27, no phone

**Kernel.** `omamobile` branch of [linux-omarchy-mobile](https://github.com/derekross/linux-omarchy-mobile) shallow-cloned to `~/hermes-workspace/android-mainline/kernel` (outside the repo); release `7.3.0-rc6-omamobile-push1-g33267e524f97-dirty` (`include/config/kernel.release`; `-dirty` is an artifact of the shallow clone's `git describe`, no source was edited). The board DT is upstream, no blueline-specific patch. The repo's `docker/Dockerfile` does not install on arm64 (`g++-multilib`, `gcc-multilib`, `lib32readline-dev`, `lib32z1-dev` have no aarch64 candidates — the image was built for x86_64 hosts), so the build ran in a trim of it for arm64 (`android-mainline/buildenv-Dockerfile.arm64`, same Ubuntu 24.04 minus the multilib packages): gcc 13.3.0, GNU Make 4.3, binutils 2.42, native `--platform linux/arm64` on this Apple-silicon machine, no `LLVM=1`.

Config: arm64 `defconfig` + `kernel/configs/omamobile.config` with `scripts/kconfig/merge_config.sh -m` exactly as `bin/omamobile kernel` does. **The fragment builds clean for sdm845** — arm64 is multi-platform, so the Tensor options are additive; no fallback config was needed. `scripts/config -e` pinned three symbols the defconfig leaves `=m` and the initramfs needs built-in (it loads no modules): `SCSI_UFS_QCOM`, `USB_CONFIGFS`, `QCOM_WDT` (ABOOT-generation watchdog; flame takes it over with a module, first light cannot). `EXT4_FS`, `USB_DWC3_QCOM`, `USB_CONFIGFS_NCM/ACM`, `DEVTMPFS_MOUNT`, `BLK_DEV_INITRD`, `DRM_SIMPLEDRM`, geni serial and the RPMH/ICC/IOMMU sdm845 stack were already `=y` from defconfig or the fragment (`olddefconfig` kept every pin). `modules` was not built (first light loads nothing); the target DTB needed its own `make` invocation — combining `Image.gz arch/arm64/boot/dts/qcom/….dtb` in one call trips kbuild's target-prefix duplication (`No rule to make target 'arch/arm64/boot/dts/arch/arm64/boot/dts/…'`).

```
make ARCH=arm64 O=out-blueline-kernel defconfig
scripts/kconfig/merge_config.sh -m -O out-blueline-kernel \
    out-blueline-kernel/.config kernel/configs/omamobile.config
scripts/config --file out-blueline-kernel/.config -e SCSI_UFS_QCOM -e USB_CONFIGFS -e QCOM_WDT
make ARCH=arm64 O=out-blueline-kernel olddefconfig
make ARCH=arm64 O=out-blueline-kernel -j18 Image.gz
make ARCH=arm64 O=out-blueline-kernel dtbs
```

**Image builder.** `device/blueline/firstlight/build` (host CLI, `build-flame-probe` style) runs `device/blueline/firstlight/initramfs/build` in a disposable aarch64 Alpine container and assembles with AOSP `mkbootimg.py` (AOSP `system/tools/mkbootimg`, shallow clone beside the kernel). The initramfs is Alpine `alpine-baselayout busybox dropbear iproute2 util-linux busybox-extras` (729 cpio entries) with `device/blueline/firstlight/initramfs/init`: banner, tmpfs/devtmpfs root, **every** UFS block `blockdev --setro` before anything mounts (per-device failures logged, re-asserted by a 1 s loop), an **empty** `/etc/omamobile-ufs-rw` with fail-closed init (missing or non-empty file also means all-read-only), no module loads, no userdata mount, CDC NCM `usb0` 172.16.42.1/24 + CDC ACM, product string from the descriptor's `NAME` (`/etc/omamobile-usb-product`; busybox `tr` has no `[:print:]` class — the printable-ASCII octal range is used), dropbear key-only on 172.16.42.1, shells on `ttyMSM0` and `ttyGS0`. Assembly:

```
device/blueline/firstlight/build --kernel …/Image.gz \
  --dtb …/sdm845-google-blueline.dtb --ssh-key ~/.ssh/id_ed25519.pub \
  --mkbootimg …/mkbootimg/mkbootimg.py --out out-blueline
# in the container:
mkbootimg.py --header_version 2 --base 0x0 --kernel_offset 0x00008000 \
  --ramdisk_offset 0x01000000 --tags_offset 0x100 --pagesize 4096 \
  --kernel Image.gz --ramdisk initramfs.cpio.gz --dtb sdm845-google-blueline.dtb \
  --cmdline 'console=ttyMSM0,115200n8 panic=10 androidboot.hardware=qcom androidboot.board=blueline' \
  -o out-blueline/firstlight.img
```

The DTB goes through `--dtb` (appended, header-v2 dtb fields), not the second stage — the field-proven recipe for this phone appends the board DTB (`append_dtb`, no QCDT). Output is `firstlight.img`, never `boot.img`, and the builder refuses an existing file.

**Validation, no phone (all logged to `logs-blueline/`, gitignored):**

(a) header parse (`python3` + `struct`; script in scratch, output verbatim):

```
magic           : ANDROID!
header_version  : 2 (header 1660 bytes in a 4096-byte page)
page_size       : 4096
kernel          : 16216010 bytes @ 0x8000
ramdisk         : 4757262 bytes @ 0x1000000
second          : 0 bytes
tags_addr       : 0x100
recovery_dtbo   : 0 bytes @ 0x0
dtb             : 105798 bytes @ 0x1f00000
cmdline         : console=ttyMSM0,115200n8 panic=10 androidboot.hardware=qcom androidboot.board=blueline
size            : 21086208 bytes (sections end at 21086208)
OK: header v2 layout, all sections present and page-aligned
```

`mkbootimg.py` wrote `header_version 2` (the v2 layout with the dtb size/addr fields; "header v2" on this generation means this layout, which ABOOT accepts — postmarketOS builds exactly this). `os_version/patch` is 0: the header fields are informational for ABOOT and no deviceinfo value for them was cited, so none was invented. `dtb @ 0x1f00000` is mkbootimg's default `--dtb_offset` load address; ABOOT relocates the appended DTB itself. 21.1 MiB fits a Pixel-3-size boot partition with room to spare; the builder enforces 64 MiB until M1.0's `getvar partition-size:boot_b` replaces the budget.

(b) appended DTB split out of the image and decompiled:

```
$ dtc -I dtb -O dts /chk/dtb (root node)
	qcom,board-id = <0x21505 0x00>;
	qcom,msm-id = <0x141 0x20001>;
	model = "Google Pixel 3";
	compatible = "google,blueline", "qcom,sdm845";
```

(c) ramdisk extracted and listed: 729 entries incl. `init`, `usr/sbin/dropbear`, `usr/bin/dropbearkey`, `sbin/blockdev`, `sbin/getty`, `usr/sbin/udhcpd`, `bin/ip*`, `root/.ssh/authorized_keys` (the one supplied public key), `/etc/omamobile-usb-product = [Google Pixel 3]`, `/etc/omamobile-ufs-rw: 0 bytes` (empty allowlist).

(d) `sha256 out-blueline/firstlight.img`:
`dcbd1bcdd935cd4dba50b969d006be64c71c6ad28e67e219b219e01d2a9fab53`

- Pass: image builds and parses as header v2 with the board DTB appended and
  a dropbear-bearing initramfs; re-running the builder refuses the existing
  `firstlight.img`. `avbtool info_image` is not expected to find a footer;
  ABOOT on an unlocked phone does not require one. **Nothing touched a
  phone: no fastboot or adb was ever invoked for this gate.**

### M1.2 — boot from RAM, zero writes

- Announce to whoever holds the phone: the screen will show our boot text.
- `fastboot boot <firstlight.img>` — ABOOT runs it without flashing
  (field reports show this path works on this generation; if the phone's
  ABOOT refuses, that is a stop, not a license to flash: re-check with
  `fastboot --help`-visible options and the getvars, then ask).
- Expect: the splash console hands over to kernel boot text; within 90 s
  the host has `usb0` and `ssh root@172.16.42.1`.
- Pass: `uname -a` names our build and
  `cat /proc/device-tree/compatible` starts with `google,blueline`;
  `lsblk -o NAME,RO,RM,SIZE` shows every UFS disk and partition
  read-only; the modem, Wi-Fi and ADSP remoteprocs are untouched
  (`/sys/class/remoteproc` untouched); no `ufshcd` or `abr` errors in
  `dmesg`; the `simple-framebuffer` console is the screen we are reading.
- Stop: no USB link after 90 s → hold Power ~30 s, then Power (stock
  slot A was never written; this is always survivable here). Record
  pstore after the restart.
- Risk: none — no block is written in this gate.

#### Attempt 2026-10-27: ABOOT refuses the RAM boot — gate pivots to a temporary flash

`fastboot boot` with the built image failed as
`Booting FAILED (remote: 'Error verifying the received boot.img: Invalid
Parameter')` — every time, after ABOOT had already accepted the transfer.
Controls run on the handset, in order:

1. Stock RQ3A `boot.img` from the verified factory zip via the identical
   `fastboot boot`: **OKAY**. The port, cable, and fastboot work; the
   verdict is about our image.
2. AVB hash footer (test key, `SHA256_RSA2048`, boot partition size from
   the factory image's 64 MiB budget) added around our image: refused.
3. `os_version` header field set byte-identical to stock
   (`0x1600015a`): refused.
4. The arm64 Image inside our build carries `text_offset = 0x0`
   (mainline default since the 5.8 era) while the header said
   `kernel_addr = 0x8000`. A UART log in pmaports !3932 shows this exact
   mismatch as `KernelDecompress failed: Invalid Parameter / Kernel
   TextOffset does not match`, and mobile-nixos !361 patches for it; the
   builder was rebuilt with `--kernel_offset 0x0` (header now matches the
   Image's own text_offset). Refused again — the mismatch was real but
   not the only gate.

The community record is consistent that this ABOOT generation (Android
10+ bootloader, Pixel 3/3a/3XL family) refuses *temporary* booting of any
image not built against its exact vbmeta era — TWRP never regained
`fastboot boot` there (TeamWin/android_device_google_crosshatch#5,
twrpme#109, several unresolved reports through Android 12) — while
`fastboot flash` of the same images works. Per this gate's own rule the
refusal is a stop: no further RAM-boot permutations.

**Plan deviation, decided 2026-10-27 (not a reversible shortcut):** M1.2
was written as zero-write and later gates were to touch only slot B.
This handset's ABOOT refuses RAM boot outright and there is no second
bootable mainline slot (slot A holds the only working stack, slot B is
not Ubuntu Touch's boot source here), so bring-up flashes **`boot_a`
directly**. That is destructive by design: the Ubuntu Touch `boot_a` was
overwritten without a valid backup (see the 0-byte-file correction
above), the way back is the SP1A factory image at the cost of user data,
and the owner consented to exactly this trade. Every later partition
write follows the verify-backup-first rule stated at the top of this
document.

#### Attempt 2026-10-27 (second): concatenated-DTB boots alive but mute — the PHYs were modules

Flashed to `boot_a` and rebooted (`fastboot flash` + `fastboot reboot`):
with the DTB concatenated onto the kernel blob the phone stopped dying —
no return to ABOOT for minutes, while every header-section-DTB boot was
back in ~4 s. But it booted **mute**: no NCM link, no ACM port, black
panel. Two causes, both readable from the built `.config` without the
phone:

1. First light loads **no kernel modules**, yet `arm64 defconfig` leaves
   the two PHYs the DWC3 controller needs as `=m`:
   `CONFIG_PHY_QCOM_QUSB2` (USB2 PHY, `qcom,qusb2-v2-phy`) and
   `CONFIG_PHY_QCOM_QMP_USB` (USB3 QMP PHY). The controller's probe is
   deferred forever, no UDC ever appears under `/sys/class/udc`, init's
   gadget bind has nothing to bind, and there is no instrument left.
   Fixed by `scripts/config -e PHY_QCOM_QUSB2 -e PHY_QCOM_QMP_USB
   -e PHY_QCOM_QMP` + `olddefconfig` + Image rebuild, same pin mechanism
   as M1.1's three pins. (`qcom,dwc3` glue itself was already `=y` via
   `USB_DWC3_QCOM`; the Google common DTS carries no Type-C/TPM nodes, so
   peripheral mode needs no TCPM stack.)
2. The panel console (`console=tty1` + `simple-framebuffer` over the
   splash region) stays dark on this reboot path: ABOOT kills the
   bootloader splash on handoff from fastboot mode, and first light
   ships no DSI driver. The panel is therefore **not** an instrument on
   this gate; the heartbeat/pstore loop keeps writing to kmsg anyway
   (harmless) and to ttyGS0 once the PHY fix lets the gadget bind.

#### Attempt 2026-10-27 (third): every instrument silent — the USB glue never probed

Three fixes landed in this round, all found from the host side:

1. **configfs never mounted.** The init mounted `configfs` on
   `/sys/kernel/config`, but that directory is created by *userspace*,
   not by the kernel — nothing in `init/` or `fs/sysfs` makes it — so the
   mount failed against a hidden `/dev/null` file and the gadget was
   never built. Fixed by `mkdir -p /config` + `mount -t configfs configfs
   /config` (postmarketOS' initfs path; flame's initramfs has the same
   latent bug and escapes only because its boot chain pre-creates the
   directory).
2. **The real blocker: the DWC3 glue had no matching driver.** Since the
   flatten series (v7.0/7.1) `drivers/usb/dwc3/dwc3-qcom.c` matches only
   `"qcom,snps-dwc3"` (`dwc3_qcom_of_match` in 7.3.0-rc6-omamobile, one
   entry), and `dwc3-of-simple.c` carries no Qualcomm entry at all — but
   this Android-based tree's `sdm845.dtsi` still labels both wrapper
   nodes `"qcom,sdm845-dwc3", "qcom,dwc3"`. No driver claimed `usb_1`:
   no DWC3 core, no `/sys/class/udc`, no probe error, nothing on any
   instrument. The community Pixel 3 ports run the *old* driver with the
   old compatible (pmOS' fork pins `sdm845-6.11`/`sdm845-7.1-rc1-r0`), so
   the binding rename simply never surfaced there. Fixed by
   `compatible = "qcom,snps-dwc3", "qcom,sdm845-dwc3", "qcom,dwc3"` on
   `usb_1`/`usb_2` (old strings kept as fallback). The `vdda-phy`/
   `vdda-pll` swap suspicion from an early diff of the two forks was
   checked against the 7.1 reference and dropped: mainline order and
   pmOS order are identical (phy=l26a_1p2, pll=l1a_0p875).
3. **Instruments added where the plan was mute-by-design:** heartbeat
   echo onto ttyGS0, pstore ramoops node in the blueline DTS (1 MiB at
   0x9ff00000, `console-ramoops` readable after the next boot), and a
   `console=tty0` fbcon line — ABOOT's fastboot splash teardown kills
   `keep_bootcon`, so `console=tty0` is the only way kernel text can
   reach the panel at first light.

Side experiment worth recording: a self-built pmOS 6.11 kernel
(`kernel/sdm845-6.11` tag, their defconfig, our initramfs, same
concat-DTB v2 pack) booted alive but mute — with `CONFIG_EFI_ZBOOT=y`
the packaged `Image.gz` is an EFI-stub binary, so that build is *not*
proof for the reference stack, only for our packaging path. The pmOS
packaging detail they rely on (initfs, bootimg v2 with DTB appended per
their `initfs` + `deviceinfo` bootargs) is now reproduced stepwise.

#### Attempt 2026-10-27 (fourth): 7-second ABOOT return localizes the death to the QSCRATCH map — flatten's offset is wrong for SDM845

The timed panic probe worked as designed: flashing the probe image (panic
45 s after init) and the plain listener (no probe) both returned the
handset to FASTBOOT MODE **7 s** after the reboot command — while the
stock SP1A `boot.img` under the identical `fastboot reboot` booted on to
its logo (the owner saw it) and never returned. So the death is ours,
it happens well before 45 s, and with `panic=10` it is a *panic or abort*
in the first seconds of driver probe.

Reading the flatten driver closed the loop. `dwc3_qcom_probe()` in
7.3.0-rc6-omamobile computes the QSCRATCH window as
`res.start + SDM845_QSCRATCH_BASE_OFFSET` (0xf8800) — written for SoCs
whose wrapper node sits 0xf8800 below its QSCRATCH block. On SDM845 the
wrapper node's `reg` **is** the QSCRATCH region itself: every
working 6.11-era driver (ours in `kernel-pmos`, vanilla mainline's)
ioremaps `reg[0]` unshifted, and the two trees' QSCRATCH register
offsets are byte-identical — only the base computation changed. With
the shift, `qscratch_base` lands at `0xa7f1000`, inside the 0xa600000
wrapper range but in no man's land: `devm_ioremap()` checks no conflict,
so the first `GENERAL_CFG`/`vbus_override` write hits a block its GDSC
does not own, and the SoC aborts. Every symptom lines up:

- PHY-pin builds (glue unbound, no QSCRATCH write) lived minutes;
- the snps-dwc3-compatible build (glue bound, write at probe —
  `vbus_override` runs from probe in peripheral mode) dies in seconds;
- the pmOS 6.11 reference build (old driver, unshifted map) survived
  and just stayed mute for its own packaging reasons;
- stock boots the Google logo under the same reboot command.

**Fix (driver, not device tree):** the qscratch offset becomes match
data — `qcom,sdm845-dwc3` maps `reg[0]` at offset 0, `qcom,snps-dwc3`
keeps the 0xf8800 shift. The third round's DTS prepend of
`qcom,snps-dwc3` is reverted: it papered over the driver bug and pointed
the wrong (shifted) map at exactly the hardware that does not want it.
The probe stays armed on the test images: gadget first, panic at 45 s
second — the fastboot return is the boot's period at the end of sentence.

#### Attempt 2026-10-27 (fifth): the QSCRATCH map was half the bug — flatten anchors the *core* window at the wrapper reg too

The per-SoC QSCRATCH offset (fourth entry) changed nothing: probe and
listener images died at 5–6 s exactly like before. The flatten rework
does not only read QSCRATCH relative to the wrapper `reg` start — it
passes `probe_data.res` straight into `dwc3_core_probe()`, which maps
the DWC3 core globals at `res.start + 0xc100` and xHCI at `res.start`,
and then `dwc3_core_is_valid()` issues the first readl. The flattened
binding's SoCs anchor their wrapper node at the **core base** (eliza:
`usb@a600000`, reg `0xfc100`, QSCRATCH at `+0xf8800`); SDM845 anchors it
at **QSCRATCH** (`usb@a6f8800`, reg `0x400`). So on SDM845 the core read
hit `0xa709800` — the QSCRATCH-only fix had moved `qscratch_base` to the
right block while the first fatal access was never QSCRATCH but the core
probe's own validity readl. `devm_ioremap()` checks no conflict, so
nothing failed until the access; the abort needs no QSCRATCH write at
all, which is why every PHY-only diagnosis from the outside looked
alive-but-mute until the glue bound.

**Fix:** derive both windows from the QSCRATCH address — `ioremap`
QSCRATCH directly (match data: 0 for `qcom,sdm845-dwc3`, `0xf8800` for
`qcom,snps-dwc3`) and pass the core resource anchored at
`QSCRATCH − SDM845_QSCRATCH_BASE_OFFSET`. For the flattened SoCs both
computations are the identity; for SDM845 they reproduce exactly the
layout the 6.11-era driver used via the child node (`dwc3@…` reg) —
which is the tree every working Pixel 3 USB gadget boots on. Kernel
commits `16897c828` (driver), `7c0318228` (QMP PHY rails), `b5278c8ef`
(ramoops).

**The instrument now works unattended:** with `panic=10` a dead boot
warm-reboots into FASTBOOT MODE within seconds by itself, so the
flash → reboot → observe cycle needs no button holds anymore; a boot
that survives the probe's 45 s proves driver-probe aliveness, and a
surviving gadget must show ACM/NCM/SSH from then on.

#### Attempt 2026-10-27 (sixth): the driver is innocent — the whole 7.3 kernel line dies at 4-6 s, 6.11 survives

Three instruments ran back to back, all automatic (panic=10 turns every
death into a fastboot reappearance within seconds):

| build | boot args | outcome |
|---|---|---|
| fixA2 (dual-window fix + clocks-before-reset reorder) | bind active, probe 45 s | dead, ABOOT back at 4 s |
| same kernel | `--no-gadget` (UDC never written) | dead at 4 s — the bind never ran, so the death is not the gadget start |
| fl-phy (yesterday's "mute but alive" build, same bytes) | — | now dead at 4 s |
| fl-pmos (postmarketOS 6.11 kernel, same first-light initramfs) | — | alive through the whole 240 s window |

**Interpolation bug found mid-evening:** the `--cmdline` in
`initramfs/build` was single-quoted, so every `omadwc3q=` (and any
`${OMAMOBILE_EXTRA_CMDLINE}`) run above actually booted the literal text
`${OMAMOBILE_EXTRA_CMDLINE:-}` — the kernel ignored it and the driver ran
at full power. The scratch-only/off falsifications from the first
pass of this table are therefore VOID, not evidence; the fixed
interpolation (expand in shell, byte-assert the knob in the shipped
header) re-runs as off12. The two rows that never used the knob stand:
the 7.3 line dies at 4 s even with the gadget bind skipped, and the
6.11 kernel survives 240 s. The dwc3 window fixes stay (correct against
the binding either way, checkpatch clean); whether the driver is also a
trigger is exactly what off12's now-real `omadwc3q=off` decides.  Note:
the dtbo-restoration flash cycles both timed out waiting for the
handset — `dtbo_a` is still erased, which the 6.11 survival proves is
survivable and keeps as the one known state difference the 7.3 deaths
and the 6.11 survival share.

#### Attempt 2026-10-28: off12 measures — with the dwc3-qcom driver fully off the 7.3 kernel still dies at 5 s

The fixed interpolation put a real `omadwc3q=off` into the header
(byte-checked in the shipped image), the driver binded nothing, no
register of the USB block was touched — and the ABOOT came back at 5 s,
before the 10 s userspace probe could fire.  The 6.11 kernel with the
same first-light initramfs lived through the whole 240 s window.  The
dwc3-qcom probe is therefore exonerated as the killer of the 7.3 line
(the window-anchoring fixes remain correct upstream hygiene), and what
remains is kernel-wide: 7.3.0-rc6-omamobile-push1 vs postmarketOS 6.11,
with the config the only cheap axis.  Next measurement: 7.3-rc6 built
from the pmOS 6.11 reference config (`out-blueline-pmoscfg`, pins kept,
panic probe 120 s) — survives: config, bisect symbols; dies: code,
bisect commits.

**pmoscfg measured (2026-10-28, image a9cd3b0f…):** the 7.3-rc6 kernel
built from the full 3501-symbol 6.11 reference config (olddefconfig
clean, all bring-up pins verified =y afterwards) died at 5 s, twice,
independently flashed.  Config is exonerated.  Note arm64 has no
`OF_APPENDED_DTB` — the concatenated-DTB layout is config-free, the
head.S probe always runs.  Next axis, one flash each: 6.11 kernel with
the 7.3-built DTB (`pmosdtb`); dies => the device tree (prime suspect:
the ramoops reservation), survives => a 6.12..7.3 code regression and
a commit bisect with the panic-probe loop as the test harness.

**pmosdtb was NOT a measurement (2026-10-28).** The image lived silently
for 400 s — but its probe sat at the END of init, behind the 30 s UDC
wait and `dropbear -R` keygen, so "probe never fired" and "kernel dead"
were indistinguishable.  The probe is now armed as a background timer
immediately after the pseudo-fs mounts (commit 8e9d8ae): a fired probe
proves kernel + PID 1 aliveness even when the main flow hangs.  The
`dr_mode` theory died on inspection: the 7.3 tree's
sdm845-google-common.dtsi carries `dr_mode = "peripheral"` exactly like
pmOS — the device trees agree on the role.

**pmosdtb was NOT a measurement (2026-10-28).** The image lived silently
for 400 s — but its probe sat at the END of init, behind the 30 s UDC
wait and `dropbear -R` keygen, so "probe never fired" and "kernel dead"
were indistinguishable.  The probe is now armed as a background timer
immediately after the pseudo-fs mounts (commit 8e9d8ae): a fired probe
proves kernel + PID 1 aliveness even when the main flow hangs.  The
`dr_mode` theory died on inspection: the 7.3 tree's
sdm845-google-common.dtsi carries `dr_mode = "peripheral"` exactly like
pmOS — the device trees agree on the role.

**The tree is upstream v7.3.0-rc6, squashed, plus only our four commits
(2026-10-28).** `git tag` is empty and the root commit 33267e524 is a
96114-file squash of the whole 7.3.0-rc6 tree; on top sit 16897c828
(dual-window), 349f27b (ramoops dts), beaeaf73e (`omadwc3q=` knob),
eddee2db (pointer cast).  There is no upstream 6.12..7.3 history in this
clone, so a code bisect cannot run inside it — the suspect set inside the
tree is exactly those four commits, and the "kernel code" axis otherwise
means an upstream 6.11 -> 7.3-rc6 regression that would need the real
upstream history fetched.

**dtb73 result corrected (2026-10-28).** The probe was armed for 25 s and
ABOOT returned at 5 s — that is a DEATH before the probe, not a fired
probe; the watcher's `<= 90 s` label was wrong and is now `<= 25 s`.  So
the 7.3 kernel on the pmOS 6.11 blueline device tree (no ramoops) also
dies at 5 s: the device tree does not rescue it.  Config (pmoscfg, two
independent flashes at 4-5 s), the dwc3 driver state (off12, 5 s), and
now the device tree (dtb73, 5 s) are all exonerated; every surviving
first-light boot we have measured was a 6.11 kernel, and every death was
a 7.3 kernel.

**Config delta, informational (2026-10-28).** Comparing the surviving
6.11 self-build `.config` to the 7.3 `pmoscfg` `.config`: 160 symbols set
in 6.11 are absent in 7.3, 672 new in 7.3.  Most are auto-selected
crypto/CPU-feature symbols, but the absent set includes arm64 base
symbols — ARM64_PAN, ARM64_LSE_ATOMICS, ARM64_USE_LSE_ATOMICS,
ARM64_WORKAROUND_REPEAT_TLBI — whose behaviour differs at boot; the bare
build prints these explicitly to see whether olddefconfig keeps or drops
them on the 7.3 tree.

**Decisive single-variable test armed (2026-10-28): `rc6-bare`.** A
`git worktree` at the squashed root 33267e524 (bare upstream 7.3.0-rc6,
none of our four commits, ramoops-free dts confirmed) built from the same
pmOS 6.11 config + 21 pins, packed with the early 25 s probe.  This is
the maximal-innocence 7.3 image.  Dies at 5 s => our four commits are
innocent and the regression is upstream 6.11 -> 7.3-rc6 (fetch upstream
history to bisect).  Survives => one of our four commits is the killer
(ramoops dts being the prime suspect; bisect those five).

**rc6-bare — our four commits are exonerated (2026-10-28, image
1ca8177a…).** A `git worktree` at the squashed root 33267e524 — bare
upstream v7.3.0-rc6, none of 16897c828/349f27b/beaeaf73e/eddee2db, the
dts carrying no ramoops node — built from the same pmOS 6.11 config + 21
pins, flashed, died at 4 s (before its 25 s probe).  So the death is not
anything we wrote: it is an upstream regression in the range 6.11 (every
survivor) -> 7.3.0-rc6 (every death), reproducible at 4-5 s regardless of
config, device tree, or dwc3 driver state.  The clone is a tarball squash
(`git rev-list --count HEAD` = 6, no tags, root touches 96114 files), so
it carries no v6.12..v7.2 history; a mainline bisect means fetching the
real upstream history and bisecting there, building each suspect with our
config + first-light initramfs, oracle = the early panic-probe's ABOOT
return window (survives the probe window = good, dies before it = bad;
the probe->panic=10->fastboot path needs no USB, so the oracle works even
with USB compiled out).

**Next cheap single-variable step before that multi-hour bisect: rc6-nousb
(armed).** v7.3.0-rc6, pmOS config with the whole USB stack disabled
(CONFIG_USB + DWC3/xHCI/configfs off; PHYs, clocks, interconnect, pstore
left on), early probe.  Survives => the regression is inside the 7.3 USB
core/xHCI/dwc3 stack (narrow within it next).  Dies => it is 7.3 core
(arm64 head, clocks, cpuidle/PSCI, mm, scheduler), a much wider search,
and the bisect should start on core subsystems, not USB.

**Next two measurements, both built and byte-verified (2026-10-28):**
`pmosh` (fl-pmosh, 81941839…): self-built 6.11 kernel + our 7.3 DTB,
early probe 25 s — is the self-built reference kernel alive at all, and
does its UDC finally bind (NCM watch added: 172.16.42.1 ends the cycle
early and SSH collects the boot log)?  `dtb73` (fl-dtb73, 3816a149…):
7.3 Image.gz (dual-window fix + knob) + the pmOS 6.11 blueline DTB,
early probe 25 s, verified byte-level to carry both blobs — if it dies
at 5 s like pmoscfg did, device tree AND config are exonerated and the
7.3 kernel code is the sole remaining axis: commit bisect with the
probe loop as harness.  This also tests how far the self-built 6.11
diverges from pmOS's shipped boot.img; if the shipped image survives
where the self-build dies, suspect the build/packaging, not the code.

### M1.3 — the LUN map and the calibration backups (read-only)

- Record which UFS LUN carries the partition table, `userdata` and each
  calibration partition (`persist`, the modem's `efs`/`modemst*` as their
  PARTNAMEs appear in `/sys/class/block/*/uevent`): this phone's answer
  is the `MAIN_LUN` key's value (docs/RELEASES.md 3.2) and the GPT
  exception entry's LUN. The Pixel 4 XL notes in review
  ([#52](https://github.com/derekross/omarchy-mobile/pull/52)) name seven
  UFS LUNs on its SM8150 phone; expect a similar map here.
- Back the calibration partitions up over SSH with `dd iflag=direct`
  (checksummed, to the laptop, off-repo; sha256 recorded). Before the
  first slot-flag write, no gate may run without these.
- Pass: backups complete and checksummed twice. Risk: reads only.

### M1.4 — capture the GPT before any slot-flag write

- For every LUN found in M1.3: save sectors around the primary and backup
  GPT (LBA 1, 2, last-1, last and the header regions), record the slot
  priority, successful and trial bits of every partition's attributes,
  and have `gdisk v` report both headers' CRCs. The Pixel 3 generation
  has field reports of slot-flag writes leaving the backup GPT header
  inconsistent, which bricks boot selection — the before/after capture is
  what lets this plan see it and put it back.
- This gate also fills CONTRIBUTING 3.1's exception entry for blueline:
  LUN, the four LBAs, the attribute bits, the CRCs it rewrites, the
  rollback (dd the saved sectors back), and the way back (stock slot A,
  or EDL with the unlocked phone). The entry lands in the repository
  before the write that uses it.
- Risk: none yet; it only reads.

### M1.5 — write slot B (the first writes)

- Build the root image with `ROOTFS_PACKAGES` from the descriptor's
  package (`tools/build-rootfs` — its first user outside Tensor), flash
  `userdata` through `tools/install-phone`'s guards and `boot_b` by hand
  at M1.1's recipe, now with the persistent root config.
- Keep stock `dtbo_b` at first: ABOOT applies it onto the boot image's
  appended DTB. The Pixel 4 XL notes in review
  ([#52](https://github.com/derekross/omarchy-mobile/pull/52)) tame that
  overlay with a matching 12-entry no-op dtbo; if the stock overlay
  fights our nodes, flash our own `dtbo_b` (a matching table with our
  one change) and record which entry changed.
- Pass criteria as M1.2 plus: the root mounts `rw` on `userdata`, every
  other partition still reports `ro` after boot, and the guard's
  allowlist file matches the descriptor's three names.
- Risk: `userdata` was already wiped by the unlock; `boot_b` held a stock
  copy that the factory image can restore (flash-all restores both slots'
  images including GPT-independent state; the factory image is saved
  off-device before this gate).

### M1.6 — mark slot B bootable (CONTRIBUTING 3.1's named exception)

- The only risky write of this plan, by hand, once, never from a service.
  Set slot B's bootable attributes on the LUN M1.3 named, exactly the
  bits the merged exception entry names.
- Before and after: dd the four LBAs, re-run `gdisk v`, compare CRCs;
  **refuse the reboot unless both headers parse and the headers outside
  the written entries are byte-identical to the saved ones.**
- Pass: the phone boots slot B by itself (`androidboot.slot_suffix=_b` in
  `/proc/cmdline`); after a healthy boot, `reboot-to bootloader` still
  reaches fastboot; after the success bit is applied (the same named
  write, second use), `getvar all` reports slot B successful.
- Rollback: dd the saved sectors back (attended, storage guard cannot
  block this write). Way back: slot A stock still boots throughout.
- Risk: high; this is the gate the M1.4 capture exists for.

### M1.7 — stay booted

- systemd reaches the session on the software renderer; the device
  package's policy (power key ignored for logind, `usb0` unmanaged by
  NetworkManager, whole-disk node hidden from desktop tools) is in place
  from the package, not hand-copied.
- A systemd reboot and a `reboot-to bootloader` round trip survive; the
  field reports' warm-reboot warning is verified on this phone and its
  result recorded (if warm reboots are poisoned, the reboot path gets a
  cold-boot policy and this line cites the evidence).
- `tools/phone-smoke` runs and its report opens the pull request.

## What first light does not claim

Wi-Fi (WCN3990 needs the `Google_blueline` calibration from the owner's
firmware and `rmtfs` served read-only), Bluetooth (the BD-address note
above), modem and calls (the X20 comes up through PIL/QMI; calls are
weeks after data, like every device here), audio (WCD9340 codec), the
panel driver behind the simplefb console (DPMS is the display plan's
job), touch (upstream's DTS has **no touch node yet** — the FocalTech at
i2c2-0x49 is the bring-up's first real device-tree job after first
light), sensors, GNSS (it lives in the modem), cameras, fingerprint (rear
sensor, no upstream driver this kernel drives), suspend. First light is:
slot B, our kernel, the guard, SSH over USB, our root on `userdata`.

## Why this phone is worth the GPT risk

SDM845 is the mainline-est phone SoC in this tree, and the Pixel 3 is its
cheapest complete body: GPU (A630), display, USB, storage, remoteproc and
the QMI modem path all run upstream on dragonboard-class boards today.
The field notes cited above report a mainline Pixel 3 that makes and
receives real calls — the milestone the Pixel 7 Pro's own plan is weeks
to months from, on hardware where the modem is a Google S5300 over PCIe
with no field-proven path yet. On blueline the plan's whole risky asset
is one GPT write; everything after M1.6 is the same road cheetah took.

## Open questions for the maintainers

1. Is `android-v2` (the Pixel 4 XL's descriptor names it) the word this
   repository standardizes on for Qualcomm header-v2 phones, so
   `bin/omamobile`, `tools/install-phone` and `tools/build-rootfs` learn
   one method for this whole generation?
2. The shared `initramfs/init` reads its guard's allowlist the same way,
   but its probes are Tensor-keyed. Blueline-local init (flame's model)
   or one init with per-SoC sections?
3. The `MAIN_LUN`, `FIRMWARE_MAP`, `FACTORY_PRODUCT` and `USERDATA_FS`
   keys reserved in docs/RELEASES.md 3.2 fit this device exactly; values
   come from M1.3 and the owner's factory image.
