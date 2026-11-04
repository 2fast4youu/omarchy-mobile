#!/bin/sh
# Baut den pmOS-sdm845-Kernel (7.1) im arm64-Alpine-Container.
# Basis: linux-sdm845 (sdm845-7.1-rc1-r0), Config aus pmaports.
set -eu
K=${K:-/Users/gregor/hermes-workspace/linux-sdm845}
OUT=${OUT:-/Users/gregor/hermes-workspace/pmos-kernel-out}
CFG=${CFG:-/tmp/pmos-sdm845.config}
mkdir -p "$OUT"
docker run --rm -v "$K":/k -v "$OUT":/out -v "$CFG":/cfg:ro alpine:edge sh -c '
apk add --no-cache clang lld llvm make bc flex bison dtc pahole openssl-dev elfutils-dev perl python3 bash gzip xz zstd tar coreutils gcc >/dev/null 2>&1
cd /k
cp /cfg /out/.config
make ARCH=arm64 LLVM=1 O=/out olddefconfig >/dev/null 2>&1
grep -E "^CONFIG_(ARCH_QCOM|MODULES|DRM_MSM|SCSI_UFS_QCOM)=" /out/.config
make ARCH=arm64 LLVM=1 O=/out -j12 Image.gz dtbs modules > /out/build.log 2>&1
echo "EXIT=$?"; tail -4 /out/build.log
'
