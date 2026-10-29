#!/bin/sh
# Kanonischer Suite-Lauf auf nativem arm64 (alpine:edge, --platform linux/arm64/v8).
# Aufruf: docker run --rm --platform linux/arm64/v8 -v "$PWD":/w:ro \
#   -v /private/tmp/fl-v0q:/fl-v0q:ro -v /private/tmp/refmod:/private/tmp/refmod:ro \
#   -v "$WS/pmos-ref-build":/pmos-ref-build:ro -v "$PWD/tools/ci-arm64.sh":/v.sh:ro \
#   alpine:edge sh /v.sh
# Zaehlt ok/total und mountet alle
# Artefakte, die tests/gadget-modules braucht (ohne ihre Mounts ist ein
# 'not ok' Dunkelheit, kein Rueckschritt - gemessen: 83/1 ohne, 121/0 mit).
set -u
apk add --no-cache git python3 bash perl diffutils findutils grep sed \
  coreutils zstd tar openssl >/dev/null 2>&1
cp -r /w /work
cd /work; chmod -R u+w .
mkdir -p /private/tmp; ln -sfn /fl-v0q /private/tmp/fl-v0q
mkdir -p /faktes
printf '%s\n' \
  '#!/bin/sh' 'args=""' \
  'while [ $# -gt 0 ]; do' \
  '  case "$1" in -a) shift ;; -*) ;; *) args="$args $1" ;; esac; shift' \
  'done' \
  'for f in $args; do printf "%s  %s\n" "$(sha256sum "$f" | cut -d" " -f1)" "$f"; done' \
  > /faktes/shasum
printf '%s\n' '#!/bin/sh' 'echo "   Product ID: 0x0001"' > /faktes/system_profiler
chmod 755 /faktes/*
leer=$(sha256sum /dev/null | cut -d' ' -f1)
gemessen=$(/faktes/shasum -a 256 /dev/null | cut -d' ' -f1)
[ "$leer" = "$gemessen" ] || { echo "not ok - shasum-Fake liefert $gemessen statt $leer"; exit 1; }
export PATH=/faktes:$PATH
out=$(./tests/all 2>&1); rc=$?
printf '%s\n' "$out" | grep '^not ok' | head -8
gesamt=$(printf '%s' "$out" | grep -c '^ok')
skip=$(printf '%s' "$out" | grep -c '^ok - # skip')
nok=$(printf '%s' "$out" | grep -c '^not ok')
echo "SUITE: ok=$gesamt (davon skip=$skip) not-ok=$nok exit=$rc"
[ "$nok" -eq 0 ] && [ "$rc" -eq 0 ] && echo "SUITE GRUEN"
