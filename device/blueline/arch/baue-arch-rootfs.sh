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

echo "== SSH-Zugang und /init"
mkdir -p /tmp/arch/root/.ssh
printf '%s\n' "$PUB" > /tmp/arch/root/.ssh/authorized_keys
chmod 700 /tmp/arch/root/.ssh
chmod 600 /tmp/arch/root/.ssh/authorized_keys
cp /om/arch-init.sh /tmp/arch/init
chmod 755 /tmp/arch/init
: > /tmp/arch/etc/machine-id
printf '/dev/loop0 / ext4 defaults 0 1\n' > /tmp/arch/etc/fstab

echo "== pacman: Schluessel und openssh"
ln -sf /proc/self/mounts /tmp/arch/etc/mtab
mkdir -p /tmp/arch/proc /tmp/arch/dev
mount -t proc proc /tmp/arch/proc
mount --bind /dev /tmp/arch/dev
chroot /tmp/arch /bin/bash -euc '
  pacman-key --init >/dev/null 2>&1
  pacman-key --populate archlinuxarm >/dev/null 2>&1
  pacman -Sy --noconfirm --needed openssh
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
