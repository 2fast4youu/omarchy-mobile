#!/bin/sh
# SPDX-License-Identifier: MIT
# Ein Befehl baut das komplette Omarchy-Mobile-ROM fuer das Pixel 3
# (blueline): boot.img (Kernel + Initramfs + DTB) und userdata.img
# (Arch-Rootfs, sparse). Ergebnis landet mit SHA256SUMS in AUSGABE.
#
#   device/blueline/baue-rom.sh                 # alles bauen
#   NUR=rootfs device/blueline/baue-rom.sh      # nur das Rootfs neu
#   NUR=kernel device/blueline/baue-rom.sh      # nur Kernel/DTB neu
#   NUR=packen device/blueline/baue-rom.sh      # nur Bilder packen
#
# Voraussetzungen (werden geprueft, nicht installiert):
#   - Docker (arm64-Container fuer Kernel und Rootfs)
#   - ALARM-Tarball in $CACHE
#   - Kernel-Baum in $KERNEL (mit angewendetem Patch aus
#     device/blueline/arch/kernel-patches/)
#   - Omarchy-Pakete in $PKGS
#
# Alles ist wiederholbar: gleiche Eingaben -> gleiche SHA256.
set -eu

HIER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH= cd -- "$HIER/../.." && pwd)
WS=${WS:-$HOME/hermes-workspace}
KERNEL=${KERNEL:-$WS/linux-sdm845}
KOUT=${KOUT:-$WS/pmos-kernel-out}
CACHE=${CACHE:-$HOME/.cache/omamobile-rootfs}
PKGS=${PKGS:-$WS/pkgs}
FW=${FW:-$WS/firmware}
AUSGABE=${AUSGABE:-$WS/rom-blueline}
NUR=${NUR:-alle}
ARCH=$HIER/arch
FL=$HIER/firstlight
IMAGE=$WS/images/arch-userdata

rot() { printf '\033[31m%s\033[0m\n' "$*" >&2; }
gruen() { printf '\033[32m%s\033[0m\n' "$*"; }
schritt() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

pruefe() {
    fehlt=0
    for p in "$@"; do
        [ -e "$p" ] || { rot "fehlt: $p"; fehlt=1; }
    done
    [ "$fehlt" = 0 ] || { rot "Voraussetzungen fehlen - Abbruch."; exit 1; }
}

command -v docker >/dev/null || { rot "docker fehlt"; exit 1; }
mkdir -p "$AUSGABE"

# ---------------------------------------------------------------- Kernel
if [ "$NUR" = alle ] || [ "$NUR" = kernel ]; then
    schritt "Kernel + DTB bauen"
    pruefe "$KERNEL/Makefile" "$KOUT/.config"
    # Patch anwenden, falls noch nicht geschehen.
    if ! grep -q "Omarchy Mobile" "$KERNEL/arch/arm64/boot/dts/qcom/sdm845-google-common.dtsi" 2>/dev/null; then
        ( cd "$KERNEL" && git apply "$ARCH/kernel-patches/0001-omarchy-mobile-blueline.patch" )
        gruen "Kernel-Patch angewendet"
    else
        gruen "Kernel-Patch bereits angewendet"
    fi
    docker run --rm \
        -v "$KERNEL":/k -v "$KOUT":/out -v "$FW":/fw:ro \
        alpine:edge sh -c '
            apk add --no-cache clang lld llvm make bc flex bison dtc pahole \
                openssl-dev elfutils-dev perl python3 bash gzip xz zstd tar \
                coreutils gcc >/dev/null 2>&1
            cd /k
            make ARCH=arm64 LLVM=1 O=/out -j"$(nproc)" Image.gz dtbs modules
        '
    gruen "Kernel gebaut: $(ls -l "$KOUT/arch/arm64/boot/Image.gz" | awk '{print $5}') Bytes"
fi

# ---------------------------------------------------------------- Rootfs
if [ "$NUR" = alle ] || [ "$NUR" = rootfs ]; then
    schritt "Arch-Rootfs bauen"
    pruefe "$CACHE/ArchLinuxARM-aarch64-latest.tar.gz" "$PKGS" "$FW"
    CACHE="$CACHE" PKGS="$PKGS" FW="$FW" ZIEL="$IMAGE" \
        sh "$ARCH/baue-arch.sh"
    gruen "Rootfs gebaut: $(ls -l "$IMAGE/rootfs.ext4" | awk '{print $5}') Bytes"
fi

# ---------------------------------------------------------------- Packen
if [ "$NUR" = alle ] || [ "$NUR" = packen ]; then
    schritt "Boot-Image packen (Kernel + Initramfs + DTB)"
    pruefe "$KOUT/arch/arm64/boot/Image.gz" \
           "$KOUT/arch/arm64/boot/dts/qcom/sdm845-google-blueline.dtb" \
           "$FL/pack-v0.py"
    RAMDISK=${RAMDISK:-$WS/images/fl-v0ag/ramdisk.gz}
    pruefe "$RAMDISK"
    python3 - "$KOUT" "$RAMDISK" /tmp/kernel-blob <<'PY'
import sys
out, ramdisk, ziel = sys.argv[1], sys.argv[2], sys.argv[3]
g = open(out + "/arch/arm64/boot/Image.gz", "rb").read()
d = open(out + "/arch/arm64/boot/dts/qcom/sdm845-google-blueline.dtb", "rb").read()
open(ziel, "wb").write(g + d)
print("Kernel-Blob: %d Bytes (Image.gz %d + DTB %d)" % (len(g) + len(d), len(g), len(d)))
PY
    REF=${REF:-$WS/pmos-ref-build/ref/boot.img}
    pruefe "$REF"
    python3 "$FL/pack-v0.py" \
        --kernel /tmp/kernel-blob --ramdisk "$RAMDISK" \
        --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on panic=60 hung_task_panic=1 softlockup_panic=1 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
        --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
        --pagesize-field 0 --pagesize-align 4096 --reference "$REF" \
        -o "$AUSGABE/boot.img"

    schritt "userdata-Image bauen (sparse)"
    pruefe "$IMAGE/rootfs.ext4"
    rm -f "$IMAGE/rootfs-vorlauf.ext4"
    ( dd if=/dev/zero bs=1m count=1 2>/dev/null; cat "$IMAGE/rootfs.ext4" ) > "$IMAGE/rootfs-vorlauf.ext4"
    python3 "$FL/baue-sparse.py" "$IMAGE/rootfs-vorlauf.ext4" "$AUSGABE/userdata.img"
fi

# ---------------------------------------------------------------- Pruefen
schritt "SHA256 und Groessen"
( cd "$AUSGABE" && shasum -a 256 boot.img userdata.img > SHA256SUMS && cat SHA256SUMS )
ls -l "$AUSGABE"
gruen "\nFertig. Flashen:"
echo "  fastboot flash boot_a    $AUSGABE/boot.img"
echo "  fastboot flash userdata  $AUSGABE/userdata.img"
echo "  fastboot --set-active=a && fastboot reboot"
