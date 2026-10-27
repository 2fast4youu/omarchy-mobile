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

The way back is held off-device: the stock factory image **Android 11
(RQ3A.211001.001, Oct 2021)** downloaded from Google's published URL,
`blueline-rq3a.211001.001-factory-2cca4239.zip`, sha256 verified equal to
the hash in its file name (`2cca42397f29cc3b032dbd2b627e65049ffd894be4801a39c292e663d01cbc71`),
kept outside the repository under `android-mainline/factory/`. It restores
both slots' stock images if the plan ever needs to unwind to Android.

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
