#!/bin/sh
# SPDX-License-Identifier: MIT
# Run on Arch Linux ARM with the dependencies listed in INSTALL.md.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${CAMERA_ARTIFACTS:?Set CAMERA_ARTIFACTS to an absolute staging directory}"
case "$CAMERA_ARTIFACTS" in
    /*) ;;
    *) echo 'CAMERA_ARTIFACTS must be absolute' >&2; exit 1 ;;
esac

build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
cd "$build"

checkout() {
    git init -q "$1"
    git -C "$1" fetch --depth 1 "https://gitlab.com/megapixels-org/$1.git" "$2"
    git -C "$1" checkout -q --detach FETCH_HEAD
}

checkout libmegapixels 1f86f248a835bd1cf92752a1a7cac471d65a403e
checkout libdng 438df53ee06d9f21202e0398c90a9c3bf9e86591
checkout megapixels 5fb1f24f1aeef80ea18224ab5829fda85653a4e8
git -C megapixels apply "$here/megapixels-patches/0001-requeue-discarded-frame.patch"

# Keep dependency headers and pkg-config files isolated from the build host.
prefix=$build/deps
for library in libmegapixels libdng; do
    meson setup "$library-build" "$library" --prefix="$prefix" --libdir=lib --buildtype=release
    ninja -C "$library-build" install
done

export PKG_CONFIG_PATH="$prefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
meson setup megapixels-build megapixels --prefix=/usr --libdir=lib --buildtype=release
mkdir -p "$CAMERA_ARTIFACTS/usr/lib"
DESTDIR="$CAMERA_ARTIFACTS" ninja -C megapixels-build install
cp -a "$prefix"/lib/libmegapixels.so.1* "$prefix"/lib/libdng.so.1* "$CAMERA_ARTIFACTS/usr/lib/"
