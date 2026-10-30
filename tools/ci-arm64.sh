#!/bin/sh
# Kanonischer Suite-Lauf auf nativem arm64 (alpine:edge, --platform linux/arm64/v8).
# Aufruf: docker run --rm --platform linux/arm64/v8 -v "$PWD":/w:ro \
#   -v ~/hermes-workspace/images:/images:ro \
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
# Ein Mount fuer alle Bilder: ~/hermes-workspace/images (der langlebige Ort;
# /private/tmp raeumt macOS). Die Tests suchen zuerst unter $WS/images, deshalb
# genuegt ein Link auf den Standardpfad. Zuvor waren es fuenf Einzelmounts —
# und ein fehlender davon meldete ein 'not ok', das Dunkelheit war, kein
# Rueckschritt.
if [ -d /images ]; then
  mkdir -p /Users/gregor/hermes-workspace
  ln -sfn /images /Users/gregor/hermes-workspace/images
else
  echo "nicht ok - /images fehlt: ohne Bild-Mount sind Bildpruefungen Dunkelheit"
fi
mkdir -p /private/tmp
for d in fl-v0q fl-refpacked fl-v0r refmod; do
  if [ -d "/images/$d" ]; then ln -sfn "/images/$d" "/private/tmp/$d"
  elif [ -d "/$d" ]; then ln -sfn "/$d" "/private/tmp/$d"; fi
done
mkdir -p /faktes
# Der shasum-Fake muss die WAHREN Hashes liefern, nicht einen Pauschalwert:
# der Flash-Runner vergleicht shasum-Ausgaben gegen erwartete sha256 von Bild
# und Rueckweg. Ein Fake, der immer den Null-Hash meldet, liess das Gate den
# korrekten Inhalt verwerfen - der Harness log, nicht das Geraet.
printf '%s\n' \
  '#!/bin/sh' 'args=""' \
  'while [ $# -gt 0 ]; do' \
  '  case "$1" in -a|-a256) shift ;; -*) ;; *) args="$args $1" ;; esac; shift' \
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
