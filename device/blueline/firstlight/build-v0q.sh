#!/bin/sh
# v0q: die Gadget-Module wandern in die Ramdisk, Init lädt sie vor dem Gadget.
#
# Was v0p verschwiegen hat: kernel-config-from-image.py zeigt, dass der
# Kernel-Blob unseres Bildes im gzip-Anteil BYTE-IDENTISCH zur Distro-Referenz
# ist (sha256 7112decbddcbe235..., 16042611 B, Vergleich gegen
# pmos-ref-build/ref/boot.img; der DTB-Anhang dahinter unterscheidet sich nur
# um den ramoops-Knoten). Es ist nicht unser Selbstbaukernel. Dessen Config -
# pmos-ref-build/pmaports/device/community/linux-postmarketos-qcom-sdm845/
# config-postmarketos-qcom-sdm845.aarch64 - setzt USB_LIBCOMPOSITE=m, U_ETHER=m,
# U_SERIAL=m, USB_F_NCM=m, USB_F_ACM=m, USB_CONFIGFS=m. Dort ist
# CONFIG_IKCONFIG=n, die Config ist aus dem Bild nicht extrahierbar; der
# identische Blob ist der Beleg. Unser out-blueline-kernel/.config (=y) ist ein
# anderer Kernel und war die Quelle der Aussage "NCM ist eingebaut, die Ramdisk
# braucht keine .ko". Die war falsch: ohne Module scheitert schon das
# configfs-Mount (USB_CONFIGFS=m), und damit alles danach.
#
# Die Module kommen aus dem Referenz-Initramfs selbst: refmodules.py liest die
# Schliessung aus dessen modules.dep und legt sie entpackt nach
# /private/tmp/refmod. busybox-insmod (sbin/insmod ist ein Hardlink auf
# /bin/busybox) kann kein zstd, also ohne .zst; es prueft den vermagic selbst.
#
# dr_mode ist als Erklaerung vom Tisch: unser DTB unterscheidet sich vom
# Referenz-DTB nur um den ramoops-Knoten (18 Diff-Zeilen im decompilierten
# Text), beide tragen dr_mode = "peripheral" am dwc3.
#
# Der Umbau steckt in patch-v0q.py, die Schlusspruefung aus dem fertigen Bild in
# verify-v0q.py - beide als Dateien. Ein frueherer Versuch, denselben Text als
# Heredoc in dieses Shellskript zu schreiben, ist an den Dollar-Expansionen
# kaputtgegangen: <<PY ohne Quotes expandiert "$m" und "$(basename ...)" weg.
set -eo pipefail
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
[ -f /private/tmp/fl-v0p/firstlight.img ] || { echo "v0p-Bild fehlt"; exit 1; }
[ -f /private/tmp/fl-v0p/new.cpio ] || { echo "v0p-Archiv fehlt"; exit 1; }
[ -f /private/tmp/refmod/libcomposite.ko ] || {
  echo "refmod fehlt: REF_IMG=... python3 $FL/refmodules.py /private/tmp/refmod"; exit 1; }
mkdir -p /private/tmp/fl-v0q
docker run --rm \
  -v /private/tmp/fl-v0p:/p:ro \
  -v /private/tmp/refmod:/m:ro \
  -v /private/tmp/fl-v0q:/q \
  -v "$FL":/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  alpine:edge sh -euc '
apk add --no-cache python3 gzip zstd >/dev/null 2>&1
python3 /om/patch-v0q.py /p/firstlight.img /m /p/new.cpio /q/new.cpio
chmod 644 /q/new.cpio
python3 /om/kernel-blob-from-image.py /p/firstlight.img /q/kernel-blob
gzip -n -9 -c /q/new.cpio > /q/ramdisk.gz
python3 /om/pack-v0.py \
  --kernel /q/kernel-blob --ramdisk /q/ramdisk.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /q/firstlight.img 2>&1 | tail -2
python3 /om/verify-v0q.py /q/firstlight.img
sha256sum /q/firstlight.img /q/new.cpio'
