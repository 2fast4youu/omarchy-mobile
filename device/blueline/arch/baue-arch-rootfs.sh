#!/bin/sh
# Baut das Arch-Linux-ARM-Rootfs (Omarchy-Basis) als ext4-Bild, im Container.
#
# Laeuft unter alpine:edge (arm64) und wird von baue-arch.sh gestartet:
#   /in   ArchLinuxARM-aarch64-latest.tar.gz (read-only)
#   /om   dieses Verzeichnis (arch-init.sh, read-only)
#   /out  Zielverzeichnis fuer rootfs.ext4
#
# Ergebnis: /out/rootfs.ext4 (SIZE_GB GiB, Label omamobile-root, ohne Vorlauf;
# den 1-MiB-Vorlauf und das Sparse-Bild macht danach baue-vorlauf-und-sparse.sh).
set -eu
TAR=${TAR:-/in/ArchLinuxARM-aarch64-latest.tar.gz}
OUT=${OUT:-/out}
PUB=${PUB:-}
SIZE_GB=${SIZE_GB:-4}

[ -f "$TAR" ] || { echo "nicht ok - $TAR fehlt"; exit 1; }
[ -n "$PUB" ] || { echo "nicht ok - PUB (oeffentlicher SSH-Schluessel) fehlt"; exit 1; }
apk add --no-cache e2fsprogs tar coreutils >/dev/null 2>&1

rm -rf /tmp/arch
mkdir -p /tmp/arch
echo "== entpacke $(basename "$TAR")"
tar -xzf "$TAR" -C /tmp/arch
rm -f /tmp/arch/etc/resolv.conf
cp /etc/resolv.conf /tmp/arch/etc/resolv.conf
# pacman 7 sandbox (Landlock/alpm user) laesst sich im Container nicht aufsetzen.
sed -i -e 's/^#DisableSandboxFilesystem/DisableSandboxFilesystem/' \
       -e 's/^#DisableSandboxSyscalls/DisableSandboxSyscalls/' /tmp/arch/etc/pacman.conf
sed -i 's/^CheckSpace/#CheckSpace/' /tmp/arch/etc/pacman.conf

# qcom-Firmware (a630_sqe.fw, a630_gmu.bin, a630_zap.mbn) fuer GPU/DSI.
if [ -d /fw/qcom ]; then
    mkdir -p /tmp/arch/usr/lib/firmware
    cp -a /fw/qcom /tmp/arch/usr/lib/firmware/
    echo "== Firmware: $(du -sh /tmp/arch/usr/lib/firmware/qcom | cut -f1)"
fi

echo "== SSH-Zugang und /init"
mkdir -p /tmp/arch/root/.ssh
printf '%s\n' "$PUB" > /tmp/arch/root/.ssh/authorized_keys
chmod 700 /tmp/arch/root/.ssh
chmod 600 /tmp/arch/root/.ssh/authorized_keys
if [ -d /pkgs ]; then
    cp -r /pkgs /tmp/arch/root/pkgs
    echo "== Paketquellen: $(ls /tmp/arch/root/pkgs | tr '\n' ' ')"
fi
cp /om/arch-init-standalone.sh /tmp/arch/init
cp /omarchy-4.0.6.pkg.tar.zst /tmp/arch/tmp/omarchy-4.0.6.pkg.tar.zst 2>/dev/null || true
cp /omarchy-settings-4.0.6.pkg.tar.zst /tmp/arch/tmp/omarchy-settings-4.0.6.pkg.tar.zst 2>/dev/null || true
chmod 755 /tmp/arch/init
: > /tmp/arch/etc/machine-id
printf '/dev/loop0 / ext4 defaults 0 1\n' > /tmp/arch/etc/fstab
mkdir -p /tmp/arch/usr/local/bin
cp /om/omamobile-time-sync /tmp/arch/usr/local/bin/omamobile-time-sync
chmod 755 /tmp/arch/usr/local/bin/omamobile-time-sync
mkdir -p /tmp/arch/usr/local/bin /tmp/arch/usr/local/lib/qbootctl
cp /qbootctl /tmp/arch/usr/local/bin/qbootctl
cp /ld-musl-aarch64.so.1 /tmp/arch/usr/local/lib/qbootctl/ld-musl-aarch64.so.1
chmod 755 /tmp/arch/usr/local/bin/qbootctl /tmp/arch/usr/local/lib/qbootctl/ld-musl-aarch64.so.1
mkdir -p /tmp/arch/opt/omamobile/mods
[ -f /leds-qcom-flash.ko ] && cp /leds-qcom-flash.ko /tmp/arch/opt/omamobile/leds-qcom-flash.ko
cp /mods/*.ko /tmp/arch/opt/omamobile/mods/ 2>/dev/null || true
if [ -f /gpi.ko ]; then
    mkdir -p /tmp/arch/opt/omamobile
    cp /gpi.ko /tmp/arch/opt/omamobile/gpi.ko
    echo "== gpi.ko ins Image"
fi
for b in rmtfs tqftpserv pd-mapper; do
    [ -f "/modembin/$b" ] && cp "/modembin/$b" /tmp/arch/usr/bin/ && chmod 755 /tmp/arch/usr/bin/$b
done
# libqrtr.so.1 aus dem Debian-qrtr-Paket (ALARM hat kein libqrtr-Paket)
l=/modembin-lib/aarch64-linux-gnu/libqrtr.so.1
[ -f "$l" ] && cp "$l" /tmp/arch/usr/lib/libqrtr.so.1 && chmod 755 /tmp/arch/usr/lib/libqrtr.so.1
mkdir -p /tmp/arch/usr/lib/firmware/qcom/sdm845/Google/blueline
for f in mba.mbn modem.mbn modemr.jsn modemuw.jsn wlanmdsp.mbn; do
    [ -f "/qcomfw/$f" ] && cp "/qcomfw/$f" /tmp/arch/usr/lib/firmware/qcom/sdm845/Google/blueline/
done
date -u +%Y-%m-%dT%H:%M:%SZ > /tmp/arch/etc/omamobile-buildtime

echo "== pacman: Schluessel und openssh"
ln -sf /proc/self/mounts /tmp/arch/etc/mtab
mkdir -p /tmp/arch/proc /tmp/arch/dev
mount -t proc proc /tmp/arch/proc
mount --bind /dev /tmp/arch/dev
printf '\n[omarchy]\nServer = https://pkgs.omarchy.org/stable/$arch\nSigLevel = Optional TrustAll\n' >> /tmp/arch/etc/pacman.conf
chroot /tmp/arch /bin/bash -euc '
  pacman-key --init >/dev/null 2>&1
  pacman-key --populate archlinuxarm >/dev/null 2>&1
  pacman -Sy --noconfirm --needed openssh
  pacman -S --noconfirm --needed omarchy
  pacman -S --noconfirm --needed squeekboard foot libbsd inotify-tools python-dbus python-gobject wf-recorder grim patch chromium nautilus bluez bluez-utils mpv imv gnome-text-editor v4l-utils libcamera-tools
  sed -i "s/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen
  locale-gen >/dev/null 2>&1
  groupadd -f video; groupadd -f input; groupadd -f seat
  id omarchy >/dev/null 2>&1 || useradd -m -G video,input,seat -s /bin/bash omarchy
  ln -sfn /proc/self/fd /dev/fd
  for p in omamobile-apps omamobile-omarchy omamobile-shell; do
    [ -d /root/pkgs/$p ] || continue
    ( cd /root/pkgs/$p
      rm -rf /tmp/stage-$p; mkdir -p /tmp/stage-$p
      if startdir=$PWD pkgdir=/tmp/stage-$p bash -c "source ./PKGBUILD; package" >/tmp/pkg-$p.log 2>&1; then
        cp -a /tmp/stage-$p/. /
        echo "paket $p installiert"
      else
        echo "paket $p FEHLER:"; tail -3 /tmp/pkg-$p.log
      fi )
  done
  pacman -U --noconfirm /tmp/omarchy-settings-4.0.6.pkg.tar.zst /tmp/omarchy-4.0.6.pkg.tar.zst >/tmp/omarchy-pin.log 2>&1 || { echo "WARN: Omarchy 4.0.6 nicht installiert"; tail -8 /tmp/omarchy-pin.log; }
  if ! omamobile-omarchy-patches apply >/tmp/omarchy-patches.log 2>&1; then
      echo "WARN: Omarchy-Patches nicht angewendet:"
      tail -20 /var/log/omamobile/omarchy-patches.log 2>/dev/null || tail -20 /tmp/omarchy-patches.log
  fi
  rm -rf /tmp/stage-* /tmp/pkg-*.log /root/pkgs
  ssh-keygen -A
  systemctl enable sshd 2>/dev/null || ln -sf /usr/lib/systemd/system/sshd.service \
    /etc/systemd/system/multi-user.target.wants/sshd.service
'
umount /tmp/arch/dev /tmp/arch/proc 2>/dev/null || true

echo "== ext4"
rm -f "$OUT/rootfs.ext4"
truncate -s "${SIZE_GB}G" "$OUT/rootfs.ext4"
mkfs.ext4 -F -q -L omamobile-root -d /tmp/arch "$OUT/rootfs.ext4"
sha256sum "$OUT/rootfs.ext4"
echo "== fertig: $OUT/rootfs.ext4"
