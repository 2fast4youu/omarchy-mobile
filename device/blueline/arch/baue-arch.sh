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
SIZE_GB=${SIZE_GB:-8}
WS=${WS:-$HOME/hermes-workspace}
KOUT=${KOUT:-$WS/pmos-kernel-out}
FW=${FW:-$WS/firmware}
PKGS=${PKGS:-$HIER/../../../packages}
: "${CAMERA_ARTIFACTS:?CAMERA_ARTIFACTS muss auf die Megapixels-Buildartefakte zeigen}"
for f in usr/bin/megapixels usr/lib/libmegapixels.so.1.1.0 usr/lib/libdng.so.1.2.0 usr/share/glib-2.0/schemas/me.gapixels.Megapixels.gschema.xml; do
    [ -s "$CAMERA_ARTIFACTS/$f" ] || { echo "fehlt: $CAMERA_ARTIFACTS/$f" >&2; exit 1; }
done
[ -s "$KOUT/drivers/dma/qcom/gpi.ko" ] || { echo "gpi.ko fehlt in $KOUT" >&2; exit 1; }

[ -f "$CACHE/ArchLinuxARM-aarch64-latest.tar.gz" ] || {
    echo "nicht ok - ALARM-Tarball fehlt in $CACHE"; exit 1; }
if [ -z "${PUB:-}" ]; then
    [ -f "$KEY.pub" ] || ssh-keygen -t ed25519 -N '' -C omamobile-blueline -f "$KEY" >/dev/null
    PUB=$(cat "$KEY.pub")
fi
# Stage the modules used by the standalone init from this kernel build.
mkdir -p "$ZIEL"
moddir=$(mktemp -d "$ZIEL/.modules.XXXXXX")
trap 'rm -rf "$moddir"' EXIT
python3 - "$KOUT" "$HIER/arch-init-standalone.sh" "$moddir" <<'PYMOD'
from pathlib import Path
import re
import shutil
import sys

kernel, init, dest = map(Path, sys.argv[1:])
modules = {p.name: p for p in kernel.rglob("*.ko")}
built_in = {
    Path(line).name.replace("-", "_")
    for line in (kernel / "modules.builtin").read_text().splitlines()
}
for group in re.findall(r"for m in (.*?); do", init.read_text(), re.S):
    for module in group.replace("\\", "").split():
        name = module + ".ko"
        if name in modules:
            shutil.copyfile(modules[name], dest / name)
        elif name.replace("-", "_") not in built_in:
            print("Module not built (check kernel config): " + name, file=sys.stderr)
if "fastrpc.ko" in modules:
    shutil.copyfile(modules["fastrpc.ko"], dest / "fastrpc.ko")
PYMOD
SENSOR_ARTIFACTS=${SENSOR_ARTIFACTS:-$moddir}
docker run --rm --platform linux/arm64 --privileged \
  -v "$CACHE":/in:ro \
  -v "$FW":/fw:ro \
  -v "$PKGS":/pkgs:ro \
  -v "$KOUT/drivers/dma/qcom/gpi.ko":/gpi.ko:ro \
  -v "$KOUT/drivers/leds/flash/leds-qcom-flash.ko":/leds-qcom-flash.ko:ro \
  -v "$moddir":/mods:ro \
  -v "$CAMERA_ARTIFACTS":/mega:ro \
  -v "$SENSOR_ARTIFACTS":/sensors:ro \
  -v /tmp/modem-bin/usr/bin:/modembin:ro \
  -v /tmp/modem-bin/usr/lib:/modembin-lib:ro \
  -v /tmp/modem-bin:/modembin-musl:ro \
  -v "$WS/pmos-ref-build/pmbootstrap-work/chroot_rootfs_google-blueline/usr/lib/firmware/qcom/sdm845/Google/blueline":/qcomfw:ro \
  -v "$WS/omarchy-pkg/omarchy-4.0.6-1-aarch64.pkg.tar.zst":/omarchy-4.0.6.pkg.tar.zst:ro \
  -v "$WS/omarchy-pkg/omarchy-settings-4.0.6-1-aarch64.pkg.tar.zst":/omarchy-settings-4.0.6.pkg.tar.zst:ro \
  -v "$HIER":/om:ro \
  -v "$ZIEL":/out \
  -e PUB="$PUB" -e SIZE_GB="$SIZE_GB" \
  alpine:edge sh /om/baue-arch-rootfs.sh
echo "Rootfs: $ZIEL/rootfs.ext4"
