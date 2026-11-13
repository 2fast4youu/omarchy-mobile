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

# qcom-Firmware (a630_sqe.fw, a630_gmu.bin, a630_zap.mbn) fuer GPU/DSI.
if [ -d /fw/qcom ]; then
    mkdir -p /tmp/arch/usr/lib/firmware
    cp -a /fw/qcom /tmp/arch/usr/lib/firmware/
    echo "== Firmware: $(du -sh /tmp/arch/usr/lib/firmware/qcom | cut -f1)"
fi

echo "== SSH-Zugang und /init"
mkdir -p /tmp/arch/root/.ssh
printf '%s\n' "$PUB" > /tmp/arch/root/.ssh/authorized_keys
chmod 700 /tmp/arch/root/.ssh
chmod 600 /tmp/arch/root/.ssh/authorized_keys
if [ -d /pkgs ]; then
    cp -r /pkgs /tmp/arch/root/pkgs
    echo "== Paketquellen: $(ls /tmp/arch/root/pkgs | tr '\n' ' ')"
fi
cp /om/arch-init-standalone.sh /tmp/arch/init
cp /omarchy-4.0.6.pkg.tar.zst /tmp/arch/tmp/omarchy-4.0.6.pkg.tar.zst 2>/dev/null || true
cp /omarchy-settings-4.0.6.pkg.tar.zst /tmp/arch/tmp/omarchy-settings-4.0.6.pkg.tar.zst 2>/dev/null || true
chmod 755 /tmp/arch/init
: > /tmp/arch/etc/machine-id
printf '/dev/loop0 / ext4 defaults 0 1\n' > /tmp/arch/etc/fstab
mkdir -p /tmp/arch/usr/local/bin
cp /om/omamobile-time-sync /tmp/arch/usr/local/bin/omamobile-time-sync
cp /om/omamobile-power-profile /tmp/arch/usr/local/bin/omamobile-power-profile
cp /om/omamobile-wakeup.sh /tmp/arch/usr/local/bin/omamobile-wakeup
cp /om/omamobile-suspend-test.sh /tmp/arch/usr/local/bin/omamobile-suspend-test
chmod 755 /tmp/arch/usr/local/bin/omamobile-suspend-test
# Pruefskripte fuer die Abnahme
cp /om/omamobile-verify-all.sh /tmp/arch/usr/local/bin/omamobile-verify-all
cp /om/omamobile-health.sh /tmp/arch/usr/local/bin/omamobile-health
chmod 755 /tmp/arch/usr/local/bin/omamobile-verify-all /tmp/arch/usr/local/bin/omamobile-health
# Abnahme-Checkliste mit auf das Geraet: sie wird am Telefon ausgefuellt.
mkdir -p /tmp/arch/root
cp /om/CHECKLISTE-ZUM-AUSFUELLEN-2026-11-11.txt /tmp/arch/root/ABNAHME-CHECKLISTE.txt 2>/dev/null || true
cp /om/INSTALL.md /tmp/arch/root/INSTALL.md 2>/dev/null || true
chmod 755 /tmp/arch/usr/local/bin/omamobile-time-sync
mkdir -p /tmp/arch/usr/local/bin /tmp/arch/usr/local/lib/qbootctl
cp /qbootctl /tmp/arch/usr/local/bin/qbootctl
cp /ld-musl-aarch64.so.1 /tmp/arch/usr/local/lib/qbootctl/ld-musl-aarch64.so.1
chmod 755 /tmp/arch/usr/local/bin/qbootctl /tmp/arch/usr/local/lib/qbootctl/ld-musl-aarch64.so.1
mkdir -p /tmp/arch/home/omarchy/.config/hypr
cp /om/hypridle/hypridle.conf /tmp/arch/home/omarchy/.config/hypr/hypridle.conf 2>/dev/null || true
mkdir -p /tmp/arch/usr/share/megapixels/config
cp /om/megapixels-config/*.conf /tmp/arch/usr/share/megapixels/config/ 2>/dev/null || true
# libcamera "simple"-Pipeline-Config: das Arch-Paket bringt keine fuer
# Qualcomm CAMSS mit. Ohne die Datei registriert libcamera den Handler,
# matcht aber kein Media-Device -> "cam -l" bleibt leer.
install -Dm644 /om/libcamera/simple.yaml \
    /tmp/arch/usr/share/libcamera/pipeline/simple/simple.yaml
# Megapixels-Binaries: wurden frueher nur manuell per scp installiert,
# fehlten damit im Image. Jetzt aus den Build-Verzeichnissen einbauen.
if [ -x /mega/megapixels/build/megapixels ]; then
    install -Dm755 /mega/megapixels/build/megapixels /tmp/arch/usr/bin/megapixels-gtk
    ln -sfn megapixels-gtk /tmp/arch/usr/bin/megapixels
    install -Dm644 /mega/megapixels/data/me.gapixels.Megapixels.gschema.xml \
        /tmp/arch/usr/share/glib-2.0/schemas/me.gapixels.Megapixels.gschema.xml
    # Desktop-Eintrag: ohne ihn erscheint Megapixels nicht im Launcher.
    install -Dm644 /mega/megapixels/data/me.gapixels.Megapixels.desktop \
        /tmp/arch/usr/share/applications/me.gapixels.Megapixels.desktop
    # Ressourcen (Shader, UI-Dateien) fuer den GL-Pfad.
    if [ -d /mega/megapixels/data ]; then
        install -d /tmp/arch/usr/share/megapixels
        cp -a /mega/megapixels/data/. /tmp/arch/usr/share/megapixels/ 2>/dev/null || true
    fi
fi
if [ -f /mega/libmegapixels/build/libmegapixels.so ]; then
    install -Dm644 /mega/libmegapixels/build/libmegapixels.so \
        /tmp/arch/usr/lib/libmegapixels.so.0
    ln -sfn libmegapixels.so.0 /tmp/arch/usr/lib/libmegapixels.so
fi
if [ -f /mega/libdng/build/libdng.so ]; then
    install -Dm644 /mega/libdng/build/libdng.so /tmp/arch/usr/lib/liblibdng.so.0.1
    ln -sfn liblibdng.so.0.1 /tmp/arch/usr/lib/libdng.so
    ln -sfn liblibdng.so.0.1 /tmp/arch/usr/lib/liblibdng.so
fi
mkdir -p /tmp/arch/opt/omamobile/mods
[ -f /leds-qcom-flash.ko ] && cp /leds-qcom-flash.ko /tmp/arch/opt/omamobile/leds-qcom-flash.ko
cp /mods/*.ko /tmp/arch/opt/omamobile/mods/ 2>/dev/null || true
if [ -f /gpi.ko ]; then
    mkdir -p /tmp/arch/opt/omamobile
    cp /gpi.ko /tmp/arch/opt/omamobile/gpi.ko
    echo "== gpi.ko ins Image"
fi
for b in rmtfs tqftpserv pd-mapper qrtr-lookup; do
    [ -f "/modembin/$b" ] && cp "/modembin/$b" /tmp/arch/usr/bin/ && chmod 755 /tmp/arch/usr/bin/$b
done
# pd-mapper ist ein musl-Binary und braucht den musl-Loader + eigene Libs
# in einem eigenen Verzeichnis (NICHT /lib/ld-musl-aarch64.so.1 ueberschreiben,
# sonst brechen insmod/rmmod/kmod, die glibc nutzen).
if [ -f /modembin-musl/ld-musl-aarch64.so.1 ]; then
    mkdir -p /tmp/arch/usr/lib/pdmapper
    cp /modembin-musl/ld-musl-aarch64.so.1 /tmp/arch/usr/lib/pdmapper/
    cp /modembin-musl/libqrtr-musl.so.1 /tmp/arch/usr/lib/pdmapper/libqrtr.so.1 2>/dev/null || true
    cp /modembin-musl/liblzma-musl.so.5 /tmp/arch/usr/lib/pdmapper/liblzma.so.5 2>/dev/null || true
    chmod 755 /tmp/arch/usr/lib/pdmapper/* 2>/dev/null || true
    echo "== pd-mapper musl-Libs installiert"
fi
# libqrtr.so.1 aus dem Debian-qrtr-Paket (ALARM hat kein libqrtr-Paket)
l=/modembin-lib/aarch64-linux-gnu/libqrtr.so.1
[ -f "$l" ] && cp "$l" /tmp/arch/usr/lib/libqrtr.so.1 && chmod 755 /tmp/arch/usr/lib/libqrtr.so.1
mkdir -p /tmp/arch/usr/lib/firmware/qcom/sdm845/Google/blueline
# adsp.mbn + adspr.jsn/adspua.jsn: der SLIMbus-Controller (qcom-ngd-ctrl)
# wartet auf den PDR-Service "avs/audio"/"msm/adsp/audio_pd"; den meldet
# der ADSP nur, wenn adspua.jsn mitgeladen wird.
for f in mba.mbn modem.mbn modemr.jsn modemuw.jsn wlanmdsp.mbn adsp.mbn adspr.jsn adspua.jsn; do
    [ -f "/qcomfw/$f" ] && cp "/qcomfw/$f" /tmp/arch/usr/lib/firmware/qcom/sdm845/Google/blueline/
done
date -u +%Y-%m-%dT%H:%M:%SZ > /tmp/arch/etc/omamobile-buildtime

echo "== pacman: Schluessel und openssh"
ln -sf /proc/self/mounts /tmp/arch/etc/mtab
mkdir -p /tmp/arch/proc /tmp/arch/dev
mount -t proc proc /tmp/arch/proc
mount --bind /dev /tmp/arch/dev
printf '\n[omarchy]\nServer = https://pkgs.omarchy.org/stable/$arch\nSigLevel = Optional TrustAll\n' >> /tmp/arch/etc/pacman.conf
# Schnellere ALARM-Mirrors zuerst: der Standard-Mirror ist oft ueberlastet
# und der Build bricht dann mit "download library error" ab.
cat > /tmp/arch/etc/pacman.d/mirrorlist <<'MIRRORS'
Server = http://de.mirror.archlinuxarm.org/$arch/$repo
Server = http://mirror.archlinuxarm.org/$arch/$repo
MIRRORS
chroot /tmp/arch /bin/bash -euc '
  pacman-key --init >/dev/null 2>&1
  pacman-key --populate archlinuxarm >/dev/null 2>&1
  # Omarchy Mobile: neue Pakete koennen einen Key mitbringen, der im
  # ALARM-Keyring noch fehlt (z. B. default-cursors). Der Keyring wird
  # im Container nicht aktualisiert, deshalb Signaturpruefung aus.
  sed -i "s/^SigLevel.*/SigLevel = Never/" /etc/pacman.conf
  # ALARM-Rolling bringt gelegentlich openssl-Versionsspruenge, die
  # alte Abhaengigkeiten (libcrypto.so=3-64) brechen. --overwrite
  # laesst den Build durchlaufen; die betroffenen Pakete werden beim
  # naechsten -Su mitgezogen.
  pacman -Sy --noconfirm --needed --overwrite='/usr/lib/*' openssh 2>&1 | tail -5
  pacman -S --noconfirm --needed omarchy
  pacman -S --noconfirm --needed squeekboard foot libbsd inotify-tools python-dbus python-gobject wf-recorder grim patch chromium nautilus bluez bluez-utils mpv imv gnome-text-editor v4l-utils libcamera-tools hypridle brightnessctl power-profiles-daemon upower pipewire pipewire-pulse pipewire-alsa wireplumber
  sed -i "s/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/" /etc/locale.gen
  locale-gen >/dev/null 2>&1
  groupadd -f video; groupadd -f input; groupadd -f seat
  id omarchy >/dev/null 2>&1 || useradd -m -G video,input,seat -s /bin/bash omarchy
  ln -sfn /proc/self/fd /dev/fd
  # XDG-Verzeichnisse + Megapixels-Postprozessor: ohne user-dirs.dirs
  # liefert g_get_user_special_dir(PICTURES) NULL, Megapixels kann keine
  # Fotos speichern (am Geraet belegt).
  mkdir -p /home/omarchy/Pictures /home/omarchy/Videos /home/omarchy/Downloads
  cat > /home/omarchy/.config/user-dirs.dirs <<"EOD"
XDG_DESKTOP_DIR="$HOME/Desktop"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
XDG_TEMPLATES_DIR="$HOME/Templates"
XDG_PUBLICSHARE_DIR="$HOME/Public"
XDG_DOCUMENTS_DIR="$HOME/Documents"
XDG_MUSIC_DIR="$HOME/Music"
XDG_PICTURES_DIR="$HOME/Pictures"
XDG_VIDEOS_DIR="$HOME/Videos"
EOD
  mkdir -p /home/omarchy/.config/megapixels
  cat > /home/omarchy/.config/megapixels/postprocess.sh <<"EOP"
#!/bin/sh
IN="$1"; OUT="$2"
if command -v convert >/dev/null 2>&1; then convert "$IN" "$OUT" 2>/dev/null && exit 0; fi
cp "$IN" "$OUT" 2>/dev/null || exit 1
EOP
  chmod 755 /home/omarchy/.config/megapixels/postprocess.sh
  chown -R omarchy:omarchy /home/omarchy/Pictures /home/omarchy/Videos /home/omarchy/Downloads /home/omarchy/.config
  # WLAN-Profil vorbereiten: SSID und Land sind gesetzt, das Passwort
  # fehlt absichtlich (kein Klartext im Image). Nach dem Boot einmal
  #   nmcli --ask connection up HOME-WLAN
  # und NetworkManager speichert das Passwort im Profil.
  mkdir -p /etc/NetworkManager/system-connections
  cat > /etc/NetworkManager/system-connections/HOME-WLAN.nmconnection <<'NMC'
[connection]
id=HOME-WLAN
uuid=9b1c2f3a-4d5e-4f60-8a7b-1c2d3e4f5a6b
type=wifi
autoconnect=true
autoconnect-priority=10

[wifi]
mode=infrastructure
ssid=HOME-WLAN

[wifi-security]
auth-alg=open
key-mgmt=wpa-psk

[ipv4]
method=auto

[ipv6]
method=auto
NMC
  chmod 600 /etc/NetworkManager/system-connections/HOME-WLAN.nmconnection
  # Hyprland-Configs: ohne sie startet Hyprland nicht (SIGSEGV, am Geraet
  # belegt). omamobile-setup-user legt sie normalerweise an, aber das
  # laeuft erst im Init - hier vorab aus dem Omarchy-Paket kopieren.
  mkdir -p /home/omarchy/.config/hypr
  [ -d /usr/share/omarchy/config/hypr ] && cp -a /usr/share/omarchy/config/hypr/. /home/omarchy/.config/hypr/ 2>/dev/null
  chown -R omarchy:omarchy /home/omarchy/.config/hypr
  for p in omamobile-apps omamobile-omarchy omamobile-shell; do
    [ -d /root/pkgs/$p ] || continue
    ( cd /root/pkgs/$p
      rm -rf /tmp/stage-$p; mkdir -p /tmp/stage-$p
      if startdir=$PWD pkgdir=/tmp/stage-$p bash -c "source ./PKGBUILD; package" >/tmp/pkg-$p.log 2>&1; then
        cp -a /tmp/stage-$p/. /
        echo "paket $p installiert"
      else
        echo "paket $p FEHLER:"; tail -3 /tmp/pkg-$p.log
      fi )
  done
  pacman -U --noconfirm /tmp/omarchy-settings-4.0.6.pkg.tar.zst /tmp/omarchy-4.0.6.pkg.tar.zst >/tmp/omarchy-pin.log 2>&1 || { echo "WARN: Omarchy 4.0.6 nicht installiert"; tail -8 /tmp/omarchy-pin.log; }
  if ! omamobile-omarchy-patches apply >/tmp/omarchy-patches.log 2>&1; then
      echo "WARN: Omarchy-Patches nicht angewendet:"
      tail -20 /var/log/omamobile/omarchy-patches.log 2>/dev/null || tail -20 /tmp/omarchy-patches.log
  fi
  rm -rf /tmp/stage-* /tmp/pkg-*.log /root/pkgs
  # Omarchy-Mobile-Plugins VORVERLINKEN (nach der Paketinstallation!):
  # omamobile-setup-user macht das normalerweise, aber wenn es scheitert,
  # startet Quickshell ohne Homescreen/Dock (am Geraet belegt).
  mkdir -p /home/omarchy/.config/omarchy/plugins
  for _pl in /usr/share/omamobile/shell/plugins/*; do
    [ -e "$_pl" ] || continue
    ln -sfn "$_pl" "/home/omarchy/.config/omarchy/plugins/$(basename "$_pl")" 2>/dev/null
  done
  chown -R omarchy:omarchy /home/omarchy/.config/omarchy 2>/dev/null
  echo "plugins verlinkt: $(ls /home/omarchy/.config/omarchy/plugins 2>/dev/null | wc -l)"
  # Shell-Profil (shell.json) VORAB setzen: omamobile-setup-user kopiert es
  # nur, wenn "omarchy-done ensure omamobile-shell-profile" greift. Ohne
  # die Datei hat Quickshell "plugins": [] und laedt KEINE omamobile-
  # Plugins -> kein Homescreen, kein Dock (am Geraet belegt).
  if [ -f /usr/share/omamobile/shell/profile/shell.json ]; then
    cp /usr/share/omamobile/shell/profile/shell.json /home/omarchy/.config/omarchy/shell.json
    chown omarchy:omarchy /home/omarchy/.config/omarchy/shell.json
  # /home/omarchy selbst gehoert dem Nutzer: sonst kann setup-user
  # kein ~/.local anlegen ("Permission denied"), und die Session
  # startet nicht (am Geraet belegt 2026-11-13).
  chown -R omarchy:omarchy /home/omarchy 2>/dev/null || true
  mkdir -p /home/omarchy/.local/state /home/omarchy/.local/share
  chown -R omarchy:omarchy /home/omarchy/.local 2>/dev/null || true
    echo "shell.json gesetzt: $(python3 -c "import json;print(len(json.load(open('/home/omarchy/.config/omarchy/shell.json')).get('plugins',[])))" 2>/dev/null) Plugins"
  fi
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
