#!/bin/sh
# Baut das 1-GiB-ext4-Image fuer die userdata-Partition (M1.5), im Container.
# Aufruf (der Rechner kann kein ext4):
#   docker run --rm --platform linux/arm64/v8 -v REPO:/w:ro -v WS:/ws \
#     -v WS/tools-bau:/bau alpine:edge sh /w/device/blueline/firstlight/baue-userdata-image.sh
#
# Warum ein Image und kein Telnet-Upload: ein 1-GiB-Image ueber die Leitung zu
# schieben war bisher bei 160 KB Schluss (Stueck-fuer-Stueck-verifiziert);
# fastboot flash userdata ist ein einziger, von ABOOT pruefter Schreibvorgang.
#
# Das Image traegt neben dem Alpine-minirootfs einen eigenen /init: der
# Initramfs-Teil hat das Gadget schon gebunden und das Netzwerk steht, also muss
# /init nur Haenden, Belegen und den Funkstille-Rueckweg mitbringen. Ohne
# restart2 im neuen Root waere der Rueckweg nach dem switch_root weg - derselbe
# Fehler wie das Modul, das im Archiv hinter dem TRAILER lag.
set -eu
ZIEL=/ws/images/userdata-alpine
BAU=/tmp/bau-ud   # der Baum lebt auf dem Container-eigenen Overlay:
# der erste Lauf verlor auf der Mac-Freigabe ('set_inode_xattr: No such file or
# directory ... "arch"'), weil e2fsprogs beim Fuellen xattrs lesen will und die
# virtiofs-Freigabe keine hat. Overlay kann es, also bleibt die Freigabe nur
# fuer das fertige Bild zustaendig.
GRuesse=1073741824                      # 1 GiB, absichtlich klein: schneller Schreib
# Achtung: mke2fs nimmt als Schlussfeld die BLOCKZAHL, nicht Bytes - mit der
# Bytezahl entstand ein 1-TiB-Image. Die Groesse steht nur im truncate.
# tune2fs liegt in Alpine in einem eigenen Paket; ohne es lief die
# Kopf-Pruefung als 'tune2fs: not found' durch, weil die Zeile in einer
# Rohrleitung steht und die Leitung den Exit von sed meldet.
apk add --no-cache e2fsprogs e2fsprogs-extra curl >/dev/null 2>&1 \
  || apk add --no-cache e2fsprogs e2fsprogs-extra curl
# Der Index wird mit wget gelesen: das kahle alpine-Image hat curl nicht, und
# der erste Lauf scheiterte genau dort ('curl: not found'), weil die Zeile vor
# dem apk stand.
MINI=$(wget -qO- https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/ \
       | grep -o 'alpine-minirootfs-[0-9.]*-aarch64\.tar\.gz' | sort -u | tail -1)
[ -n "$MINI" ] || { echo "kein minirootfs im Index"; exit 1; }
mkdir -p "$ZIEL" "$BAU/wurzeln"
cd "$BAU"
[ -f "$MINI" ] || curl -sSLO "https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/aarch64/$MINI"
rm -rf "$BAU/wurzeln/ud"
mkdir -p "$BAU/wurzeln/ud"
tar -xzf "$MINI" -C "$BAU/wurzeln/ud"
# restart2 muss aus dem Baum kommen; der Pfad wird gesucht, nicht geraten.
R2=$(ls /w/device/blueline/firstlight/*/restart2 /w/device/blueline/firstlight/restart2 2>/dev/null | head -1)
[ -n "${R2:-}" ] || { echo "restart2 nicht gefunden - Rueckweg waere blind"; exit 1; }
install -m 755 "$R2" "$BAU/wurzeln/ud/bin/restart2"
cp /w/device/blueline/firstlight/rootfs-init-fuer-ud.sh "$BAU/wurzeln/ud/init" 2>/dev/null \
  || echo "ACHTUNG: rootfs-init-fuer-ud.sh fehlt, /init bleibt der Alpine-init"
chmod 755 "$BAU/wurzeln/ud/init" 2>/dev/null
# Der Uebergabetest im Init lautet [ -x /ud/init ]. Eine 644-Quelldatei bleibt im
# Dateisystem 644, und die Uebergabe bleibt stumm aus - genau so in der Nacht auf
# den 2026-11-02 gemessen: 'uebergabe bleibt aus: init_da=66 schalter=/sbin/switch_root'.
[ -x "$BAU/wurzeln/ud/init" ] || { echo "/init im Bild ist nicht ausfuehrbar"; exit 1; }
mkdir -p "$BAU/wurzeln/ud/omamobile"
echo "M1.5-Wurzel auf userdata, gebaut $(date -u +%FT%TZ)" > "$BAU/wurzeln/ud/omamobile/HERKUNFT"
df -k "$BAU/wurzeln/ud" | tail -1
rm -f "$ZIEL/rootfs.ext4"
truncate -s "$GRuesse" "$ZIEL/rootfs.ext4"
# -d legt die Dateisystem-Inhalte ohne loop-Geraet an (im Container keines da).
mke2fs -q -t ext4 -d "$BAU/wurzeln/ud" -L OMAMOBILE -U 47a3a1b4-0d0e-4c11-9b7f-000000000155 \
  "$ZIEL/rootfs.ext4"
tune2fs -l "$ZIEL/rootfs.ext4" | sed -n '/Filesystem UUID/,/Free blocks/p;/Block Count/p'
sha256sum "$ZIEL/rootfs.ext4" | tee "$ZIEL/rootfs.ext4.sha256" > /dev/null
cat "$ZIEL/rootfs.ext4.sha256"
ls -l "$ZIEL"
