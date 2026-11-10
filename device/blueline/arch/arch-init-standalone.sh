#!/bin/sh
# Eigenstaendige /init der Arch-Wurzel (ohne systemd).
#
# Belegt am 2026-11-04: der Uebergang switch_root -> /init traegt, und das
# Arch-Root laeuft (Getty meldet "Arch Linux ARM 7.1.0-rc1-sdm845"). Der
# systemd-Start als PID 1 endet dagegen mit Exit 127; solange das nicht
# geklaert ist, bringt diese Fassung das System ohne systemd hoch:
#   - sshd auf usb0 (172.16.42.1), Root nur per Schluessel
#   - eine Root-Shell auf ttyGS0 (ACM-Konsole am Mac)
#   - PID 1 parkt; kein Panic, kein Reboot.
# Damit ist die Wurzel interaktiv und per Netz erreichbar - die Basis, auf der
# systemd und danach Omarchy nachgezogen werden.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

mkdir -p /run /run/sshd /dev/pts /dev/shm /tmp
ln -sfn /proc/self/fd /dev/fd 2>/dev/null
chmod 1777 /tmp /dev/shm 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts 2>/dev/null
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm 2>/dev/null
grep -q ' /run ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=755 tmpfs /run 2>/dev/null
hostname omamobile 2>/dev/null

# Keine RTC: der Kernel startet auf 1970, und gpg haelt dann die
# Paketsignaturen fuer Zukunftsdaten (pacman: "invalid or corrupted package
# (PGP signature)"). Beim Boot die eingebackene Bauzeit setzen; sobald Netz da
# ist, kann NTP nachziehen.
if [ "$(date +%Y 2>/dev/null)" -lt 2020 ] 2>/dev/null; then
    if [ -s /etc/omamobile-buildtime ]; then
        date -u -s "$(cat /etc/omamobile-buildtime)" >/dev/null 2>&1
    fi
fi
# Danach die echte Zeit holen, sobald usb0 steht (HTTP-Date-Header, kein NTP).
[ -x /usr/local/bin/omamobile-time-sync ] && ( /usr/local/bin/omamobile-time-sync >/dev/null 2>&1 & )

# Nur den Initramfs-Dropbear toeten: er haelt Port 22, und sein KEX scheitert
# nach switch_root (sein /dev ist mit dem alten Root verschwunden). Die
# Halteschleife des Boot-Images und der Getty bleiben unangetastet - ein
# pauschales Aufraeumen aller "/bin/sh /init" riss die Halteschleife mit und
# liess das Telefon in einen Reboot-Zyklus fallen (13:28-13:32).
pkill -x dropbear 2>/dev/null
pkill -f '^dropbear' 2>/dev/null
sleep 1

/usr/bin/ssh-keygen -A 2>/dev/null
/usr/sbin/sshd -o UsePAM=no 2>/dev/null
echo "omamobile: Arch-Wurzel bereit, sshd auf 172.16.42.1:22" > /dev/kmsg 2>/dev/null


# --- Sitzung: Display, Eingabe, Mobile-Shell ------------------------------
# Gemessen am 2026-11-04: ohne diese Schritte bleibt das Panel schwarz bzw.
# der Compositor sieht keine Eingabe. Wichtig: die GANZE Sitzung laeuft unter
# EINEM dbus-run-session, sonst kann die Shell die Tastatur nicht rufen
# (QuickSettings nutzt busctl --user sm.puri.OSK0 SetVisible).
mkdir -p /run/user/1000 /dev/input
chown omarchy:omarchy /run/user/1000 2>/dev/null
chmod 700 /run/user/1000 2>/dev/null
[ -s /etc/machine-id ] || dbus-uuidgen > /etc/machine-id 2>/dev/null
chown root:video /dev/dri/card0 /dev/dri/renderD128 2>/dev/null
chmod 660 /dev/dri/card0 /dev/dri/renderD128 2>/dev/null
[ -e /opt/omamobile/gpi.ko ] && insmod /opt/omamobile/gpi.ko 2>/dev/null
[ -e /opt/omamobile/leds-qcom-flash.ko ] && insmod /opt/omamobile/leds-qcom-flash.ko 2>/dev/null
[ -e /sys/class/leds/white:flash/brightness ] && chmod 666 /sys/class/leds/white:flash/brightness 2>/dev/null
# Hardware-Module (aus dem Kernel-Out mitgebaut): BT-Kette, WLAN-Kette,
# jeweils in Abhaengigkeitsreihenfolge; Doppelladungen sind harmlos.
for m in rfkill ecc ecdh_generic bluetooth btqca btbcm hci_uart rfcomm \
         cfg80211 mac80211 ath ath10k_core qcom_pil_info qcom_glink_smem \
         qcom_common qrtr qrtr-smd pwrseq-qcom-wcn ath10k_snoc; do
    [ -e /opt/omamobile/mods/$m.ko ] && insmod /opt/omamobile/mods/$m.ko 2>/dev/null
done

# Kamera: videodev/videobuf2 -> CCI-Controller -> camcc (GDSCs) -> camss
# -> Sensoren. Diese Reihenfolge ist die einzige, die den
# v4l2-async-Bind zuverlaessig herstellt (als Built-in probten die
# Sensoren vor dem camcc und die MCLK blieb mit -EBUSY blockiert).
for m in mc videodev v4l2-common v4l2-async v4l2-fwnode v4l2-cci \
         videobuf2-common videobuf2-v4l2 videobuf2-memops \
         videobuf2-dma-contig videobuf2-vmalloc videobuf2-dma-sg \
         i2c-qcom-cci camcc-sdm845 qcom-camss imx355 imx363; do
    [ -e /opt/omamobile/mods/$m.ko ] && insmod /opt/omamobile/mods/$m.ko 2>/dev/null
done
# KEIN Re-Bind der Sensoren: das loeste einen zweiten power_on aus und
# die geteilte MCLK2 scheiterte mit -EBUSY (am Geraet belegt). Die
# Sensoren werden nach dem camss geladen und proben dort einmalig.
chmod 666 /dev/dma_heap/* 2>/dev/null
chmod 666 /dev/media* 2>/dev/null

# Modem (MSS) + Firmware-Sichtbarkeit (am Geraet belegt):
# Der Kernel liest Firmware ueber init_task.fs (PID 1 = Initramfs-Root),
# nicht ueber unsere ext4-Wurzel. Die Dateien deshalb zusaetzlich nach
# /proc/1/root/lib/firmware/... spiegeln - sonst ENOENT fuer mba/modem,
# ath10k und qca trotz vorhandener Dateien.
for _fw in qcom/sdm845/Google/blueline/mba.mbn \
           qcom/sdm845/Google/blueline/modem.mbn \
           qcom/sdm845/Google/blueline/wlanmdsp.mbn \
           ath10k/WCN3990/hw1.0/firmware-5.bin \
           ath10k/WCN3990/hw1.0/board-2.bin \
           qca/crbtfw21.tlv qca/crnv21.bin; do
    [ -f "/usr/lib/firmware/$_fw" ] || continue
    mkdir -p "/proc/1/root/lib/firmware/$(dirname "$_fw")" 2>/dev/null
    cp "/usr/lib/firmware/$_fw" "/proc/1/root/lib/firmware/$_fw" 2>/dev/null
done
# rmtfs braucht die Modem-Dateisysteme; sie liegen auf sdf3..6.
mkdir -p /boot
for _p in 3:modem_fs1 4:modem_fs2 5:modem_fsg 6:modem_fsc; do
    _n=${_p%%:*}; _f=${_p#*:}
    [ -e "/dev/sdf$_n" ] && dd if="/dev/sdf$_n" of="/boot/$_f" bs=1M 2>/dev/null
done
# qcom_sysmon und reset-qcom-pdc zuerst; ohne sie scheitert der MSS-Probe
# (Unknown symbol qcom_sysmon_shutdown_acked / pdc reset).
# Akku: RRADC (PMI8998) -> Charger (smbx) -> Fuel-Gauge (pmi8998_fg).
# Ohne den RRADC scheitert der Charger an "usbin_v", ohne den Charger
# bleibt der Fuel-Gauge deferred.
for m in qcom-spmi-rradc qcom_smbx pmi8998_fg; do
    [ -e /opt/omamobile/mods/$m.ko ] && insmod /opt/omamobile/mods/$m.ko 2>/dev/null
done
for m in qcom_sysmon reset-qcom-pdc qcom_q6v5 qcom_q6v5_mss; do
    [ -e /opt/omamobile/mods/$m.ko ] && insmod /opt/omamobile/mods/$m.ko 2>/dev/null
done
[ -x /usr/bin/rmtfs ] && /usr/bin/rmtfs >/tmp/rmtfs.log 2>&1 &
[ -x /usr/bin/tqftpserv ] && /usr/bin/tqftpserv >/tmp/tqftpserv.log 2>&1 &
[ -x /usr/bin/pd-mapper ] && /usr/bin/pd-mapper >/tmp/pd-mapper.log 2>&1 &
sleep 2
for r in /sys/class/remoteproc/remoteproc*; do
    [ -e "$r/state" ] && echo start > "$r/state" 2>/dev/null
done

# System-Bus: bluetoothd und NetworkManager sprechen ueber den System-
# DBus, der ohne systemd hier nicht existiert. Ohne ihn scheitern beide,
# egal wie gut Kernel/Treiber sind.
mkdir -p /run/dbus
[ -x /usr/bin/dbus-daemon ] && /usr/bin/dbus-daemon --system >/tmp/dbus-system.log 2>&1 &
for _i in 1 2 3 4 5 6 7 8 9 10; do
    [ -S /run/dbus/system_bus_socket ] && break
    sleep 0.5
done
# BlueZ und NetworkManager: eigene Daemons, weil diese Wurzel ohne
# systemd laeuft. bluetoothd braucht hci0 (kommt mit der Firmware), NM
# nimmt wlan0, sobald der WLAN-Stack steht.
[ -x /usr/lib/bluetooth/bluetoothd ] && /usr/lib/bluetooth/bluetoothd -n >/tmp/bluetoothd.log 2>&1 &
[ -x /usr/bin/NetworkManager ] && /usr/bin/NetworkManager --no-daemon >/tmp/nm.log 2>&1 &
# Helligkeit fuer den Sitzungsnutzer schreibbar (Idle-Daemon/Shell).
chmod 666 /sys/class/backlight/*/brightness 2>/dev/null
# Wakeup-Quellen fuer s2idle: ohne sie bleibt das Telefon nach "echo mem"
# schlafen (keine RTC). Der Power-Knopf (pm8941_pwrkey) und die PMIC-
# Geraete wecken. Am Geraet belegt: suspend success=3, fail=0.
[ -x /usr/local/bin/omamobile-wakeup ] && /usr/local/bin/omamobile-wakeup >/tmp/wakeup.log 2>&1
# UPower: die Shell (Quickshell.Services.UPower) liest den Akku darueber.
[ -x /usr/lib/upowerd ] && /usr/lib/upowerd >/tmp/upowerd.log 2>&1 &
# Power-Profile (ppd) + Abbildung auf die CPU-Kappe.
[ -x /usr/lib/power-profiles-daemon ] && DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket /usr/lib/power-profiles-daemon >/tmp/ppd.log 2>&1 &
/usr/lib/systemd/systemd-udevd --daemon 2>/dev/null
for d in /sys/class/input/event*/uevent; do echo add > "$d" 2>/dev/null; done
chown root:input /dev/input/event* 2>/dev/null
chmod 660 /dev/input/event* 2>/dev/null
setsid seatd -g seat >/dev/null 2>&1 &
sleep 1
# Ramdisk-Diagnoseschleifen beenden: ab hier haelt der Root-SSHD Port 22
# (der Ramdisk-dropbear ist damit ersetzt; am Geraet belegt: SSH/USB
# bleiben, Last 5,0 -> 2,7, Temperatur 64 -> 57 Grad C). PID 1 parkt
# weiter in der Ramdisk.
( sleep 60; for _p in $(pgrep -f '^/bin/sh /init$' 2>/dev/null); do
    [ "$_p" = "1" ] || kill "$_p" 2>/dev/null
done ) &

cat > /run/omamobile-session.sh <<'SITZUNG'
#!/bin/sh
export XDG_RUNTIME_DIR=/run/user/1000 LIBSEAT_BACKEND=seatd LANG=en_US.UTF-8
export http_proxy=http://172.16.42.2:3128 https_proxy=http://172.16.42.2:3128
# Benutzer-Setup VOR dem Compositor: Plugins verlinken, Profil setzen,
# Omarchy-Marker (z. B. "Learn Keybindings" nicht mehr zeigen).
( timeout 20 omamobile-setup-user >/tmp/setup-user.log 2>&1 ) &
# Foot/Omarchy-Theme: das Include in ~/.config/foot/foot.ini zeigt auf
# eine Theme-Datei, die ohne Theme-Anwendung fehlt.
mkdir -p /home/omarchy/.local/state/omarchy/current/theme
[ -f /home/omarchy/.local/state/omarchy/current/theme/foot.ini ] || : > /home/omarchy/.local/state/omarchy/current/theme/foot.ini
[ -f /home/omarchy/.local/state/omarchy/current/background ] || cp /usr/share/omarchy/themes/catppuccin/backgrounds/2-waves.png /home/omarchy/.local/state/omarchy/current/background 2>/dev/null || true
chown -R omarchy:omarchy /home/omarchy/.local/state/omarchy 2>/dev/null
su - omarchy -c 'omarchy-done mark first-run-user' >/dev/null 2>&1 || true
# Deutsches Tastatur-Layout fuer die Bildschirmtastatur (Squeekboard liest
# die GNOME-xkb-Einstellung; ohne sie bleibt die OSK leer).
su - omarchy -c 'gsettings set org.gnome.desktop.input-sources sources "[('"'"'xkb'"'"','"'"'de'"'"')]"' >/dev/null 2>&1 || true
start-hyprland >/tmp/hyprland.log 2>&1 &
i=0
while [ $i -lt 30 ]; do
    sig=$(ls /run/user/1000/hypr/ 2>/dev/null | head -1)
    [ -n "$sig" ] && break
    sleep 1; i=$((i + 1))
done
sleep 2
export WAYLAND_DISPLAY=wayland-1 HYPRLAND_INSTANCE_SIGNATURE=$sig
squeekboard >/tmp/squeekboard.log 2>&1 &
# Idle-Daemon: Helligkeit runter, dann Bildschirm aus (Akku).
hypridle >/tmp/hypridle.log 2>&1 &
quickshell -p /usr/share/omarchy/shell >/tmp/quickshell.log 2>&1 &
wait
SITZUNG
chmod 755 /run/omamobile-session.sh
# Slot-Erfolgsmarke: ohne sie verbraucht ABOOT bei jedem Start einen von
# drei Versuchen und faellt nach drei Starts in den Fastboot. qbootctl ist
# der pmOS-Bootctrl-Port; er braucht /dev/disk/by-partlabel.
# Die Initramfs-Schleifen (ABLESUNG, weicher-bind, raw-log, telnetd,
# v0z) kosten rund 150 % CPU und heizen das Geraet auf 78-84 Grad C.
# Sie werden NICHT mehr frueh beendet (das riss nach einem Flash den
# USB-Zugang ab); die Helligkeit wird stattdessen sicher gedrosselt.
for bl in /sys/class/backlight/*/brightness; do
    [ -e "$bl" ] || continue
    max=$(cat "$(dirname "$bl")/max_brightness" 2>/dev/null)
    [ -n "$max" ] && echo $((max * 40 / 100)) > "$bl" 2>/dev/null
done

# Die Initramfs-Schleifen drehen die CPU im Leerlauf hoch; ohne Drossel
# wird das Geraet 78-84 Grad C warm. 1,2 GHz (naechste OPP) und 40 %
# Helligkeit halten es bei ~62 Grad C (gemessen).
for cf in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do
    [ -e "$cf" ] || continue
    echo 1800000 > "$cf" 2>/dev/null
done

mkdir -p /dev/disk/by-partlabel
i=0
for n in ssd misc keystore frp system_a system_b product_a product_b vendor_a vendor_b boot_a boot_b modem_a modem_b apdp_a apdp_b msadp_a msadp_b klog metadata userdata; do
    i=$((i + 1))
    ln -sfn /dev/sda$i /dev/disk/by-partlabel/$n
done
su - omarchy -c 'dbus-run-session -- /run/omamobile-session.sh' >/dev/null 2>&1 &
(
    sleep 15
    QB=/usr/local/lib/qbootctl
    /usr/local/lib/qbootctl/ld-musl-aarch64.so.1 --library-path "$QB" /usr/local/bin/qbootctl -m >/tmp/qbootctl-mark.log 2>&1
) &
echo "omamobile: Sitzung gestartet (dbus-run-session, Hyprland/Quickshell/Squeekboard)" > /dev/kmsg 2>/dev/null

# PID 1 bleibt am Leben. Kein exec systemd, solange der 127 nicht erklaert ist.
while :; do sleep 3600; done
