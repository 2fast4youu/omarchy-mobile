#!/bin/sh
# Host-Wrapper: baut das Arch-Rootfs fuer blueline aus dem ALARM-Tarball.
#
#   device/blueline/arch/baue-arch.sh            (4 GiB, SSH-Schluessel aus ~/.ssh)
#   PUB="ssh-ed25519 ..." SIZE_GB=6 device/...  (eigener Schluessel/Groesse)
#
# Danach: baue-vorlauf-und-sparse.sh mit BILD=<Ziel> und QUELLE=arch-init.sh,
# dann das Sparse-Bild per fastboot auf userdata.
set -eu
HIER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CACHE=${CACHE:-$HOME/.cache/omamobile-rootfs}
ZIEL=${ZIEL:-$HOME/hermes-workspace/images/arch-userdata}
KEY=${KEY:-$HOME/.ssh/omamobile_blueline}
SIZE_GB=${SIZE_GB:-4}

[ -f "$CACHE/ArchLinuxARM-aarch64-latest.tar.gz" ] || {
    echo "nicht ok - ALARM-Tarball fehlt in $CACHE"; exit 1; }
if [ -z "${PUB:-}" ]; then
    [ -f "$KEY.pub" ] || ssh-keygen -t ed25519 -N '' -C omamobile-blueline -f "$KEY" >/dev/null
    PUB=$(cat "$KEY.pub")
fi
mkdir -p "$ZIEL"
docker run --rm --platform linux/arm64 --privileged \
  -v "$CACHE":/in:ro \
  -v "$HIER":/om:ro \
  -v "$ZIEL":/out \
  -e PUB="$PUB" -e SIZE_GB="$SIZE_GB" \
  alpine:edge sh /om/baue-arch-rootfs.sh
echo "Rootfs: $ZIEL/rootfs.ext4"
