#!/bin/sh
# Megapixels passes the burst directory, output basename, and save-raw flag.
set -eu

burst=$1
output=$2
save_raw=${3:-0}

set -- "$burst"/*.jpg
if [ -f "$1" ]; then
    cp "$1" "$output.jpg"
    printf '%s\n' "$output.jpg"
    exit 0
fi

set -- "$burst"/*.dng
[ -f "$1" ] || exit 1
if magick "$1" -quality 92 "$output.jpg" && [ -s "$output.jpg" ]; then
    if [ "$save_raw" = 1 ]; then
        cp "$1" "$output.dng"
    fi
    printf '%s\n' "$output.jpg"
else
    cp "$1" "$output.dng"
    printf '%s\n' "$output.dng"
fi
