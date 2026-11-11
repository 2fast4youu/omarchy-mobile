#!/bin/sh
# Ein-Shot-Pruefung aller Hardware-Funktionen nach einem Flash.
# Aufruf auf dem Telefon: sh omamobile-verify-all.sh
echo "== uptime/kernel"; cat /proc/uptime; uname -r
echo "== load"; cat /proc/loadavg
echo "== temperaturen"; for z in /sys/class/thermal/thermal_zone*; do
    t=$(cat "$z/type" 2>/dev/null); v=$(cat "$z/temp" 2>/dev/null)
    case "$t" in cpu0*|cpu7*|gpu-top*|aoss0*) echo "$t=$v";; esac
done
echo "== module"; lsmod 2>/dev/null | grep -E 'ath10k|qrtr|bluetooth|hci|rmtfs|leds' | head -12
echo "== system-dbus"; ls -l /run/dbus/system_bus_socket 2>/dev/null; pgrep -a dbus-daemon | head -2
echo "== bluetooth"; ls /sys/class/bluetooth 2>/dev/null; pgrep -a bluetoothd; dmesg | grep -i -e 'hci0' -e 'QCA' | tail -6
echo "== networkmanager"; pgrep -a NetworkManager; nmcli -t -f DEVICE,TYPE,STATE device 2>/dev/null | head -6
echo "== modem"; ls /sys/class/remoteproc 2>/dev/null; for r in /sys/class/remoteproc/remoteproc*; do
    [ -e "$r/state" ] && echo "$r: $(cat "$r/state")"
done
echo "== qrtr"; ls /sys/bus/rpmsg/devices/ 2>/dev/null | head -6; cat /sys/class/net/*/uevent 2>/dev/null | grep -c INTERFACE
echo "== netz"; ls /sys/class/net; ip -4 addr show 2>/dev/null | grep -E 'inet ' | head -4
echo "== wlan"; dmesg | grep -i -e 'ath10k' -e 'wlfw' -e 'wlan' | tail -10
echo "== wlan0"; ip link show wlan0 2>/dev/null | head -2; ls /sys/class/ieee80211 2>/dev/null; nmcli -t -f DEVICE,TYPE,STATE device 2>/dev/null | grep -i wlan
echo "== bt-adresse"; btmgmt info 2>&1 | head -6; bluetoothctl show 2>&1 | head -6
echo "== modem-dienste"; qrtr-lookup 69 2>/dev/null | grep -i -e wlfw -e rmtfs -e 0x45 | head -4
echo "== taschenlampe"; ls /sys/class/leds/ 2>/dev/null
echo "== rmtfs/tqftpserv"; pgrep -a rmtfs; pgrep -a tqftpserv; tail -3 /tmp/rmtfs.log 2>/dev/null; tail -3 /tmp/tqftpserv.log 2>/dev/null
echo "== fehler"; dmesg | grep -i -e 'panic' -e 'Oops' -e 'failed' | tail -8
echo "== akku"; for f in capacity status voltage_now current_now temp health charge_full charge_now; do
    printf '%s=' "$f"; cat "/sys/class/power_supply/qcom-battery/$f" 2>/dev/null || echo "?"
done
echo "== upower"; upower -i "$(upower -e 2>/dev/null | grep -i battery | head -1)" 2>/dev/null | grep -E 'percentage|state|energy-full' | head -4
echo "== power-profile"; powerprofilesctl get 2>/dev/null
echo "== suspend"; for f in success fail; do printf '%s=' "$f"; cat "/sys/power/suspend_stats/$f" 2>/dev/null; done
echo "== rtc-wakealarm"; ls -l /sys/class/rtc/rtc0/wakealarm 2>/dev/null; cat /sys/class/rtc/rtc0/device/power/wakeup 2>/dev/null
echo "== ladetyp"; cat /sys/class/power_supply/pmi8998-charger/usb_type 2>/dev/null; cat /sys/class/power_supply/pmi8998-charger/online 2>/dev/null
echo "== kameras"; command -v cam >/dev/null && timeout 25 cam -l 2>&1 | grep -E '^[0-9]:' | head -4
echo "== kamera-pads"; for sd in /dev/v4l-subdev*; do
    [ -e "$sd" ] || continue
    n=$(cat "/sys/class/video4linux/$(basename "$sd")/name" 2>/dev/null)
    case "$n" in *imx355*|*imx363*)
        pads=$(ls -d /sys/class/video4linux/"$(basename "$sd")"/../../*/ 2>/dev/null | wc -l)
        echo "$n: pad-check ueber media-ctl"
        media-ctl -p -d /dev/media0 2>/dev/null | grep -A2 "$n" | head -3
    ;; esac
done
echo "== libcamera-config"; ls -l /usr/share/libcamera/pipeline/simple/simple.yaml 2>/dev/null
echo "== megapixels-shell"; grep -c omamobile.home /home/omarchy/.config/omarchy/shell.json 2>/dev/null
echo "== megapixels-config"; c=/usr/share/megapixels/config/google,blueline.conf
if [ -f "$c" ]; then
    printf 'Front='; grep -c '^Front:' "$c"
    printf 'FrontAux='; grep -c '^FrontAux:' "$c"
    printf 'Rear='; grep -c '^Rear' "$c" 2>/dev/null || echo 0
    echo "(Rear=0 ist korrekt: IMX363 liefert keine Chip-ID)"
fi
echo "== media"; ls /dev/media* 2>/dev/null; ls /dev/video* 2>/dev/null | wc -l
echo "== megapixels"; ls -l /usr/bin/megapixels 2>/dev/null | head -1; ls /usr/share/megapixels/config/ 2>/dev/null
echo "== audio"; cat /proc/asound/cards 2>/dev/null | head -4; ls /dev/snd/ 2>/dev/null | head -4
echo "== slimbus"; ls /sys/bus/slimbus/devices/ 2>/dev/null; for d in /sys/bus/slimbus/devices/*/driver; do [ -e "$d" ] && readlink "$d"; done 2>/dev/null
echo "== adsp"; cat /sys/class/remoteproc/remoteproc*/name 2>/dev/null | head -4; for r in /sys/class/remoteproc/remoteproc*/; do
    printf '%s=%s ' "$(cat "$r/name" 2>/dev/null)" "$(cat "$r/state" 2>/dev/null)"
done; echo
echo "== shell"; pgrep -x Hyprland >/dev/null && echo "Hyprland laeuft"; pgrep -x quickshell >/dev/null && echo "quickshell laeuft"; pgrep -x squeekboard >/dev/null && echo "squeekboard laeuft"
echo "== speicher"; df -h / | tail -1
echo "== kaltstart"; printf 'uptime_s='; cut -d. -f1 /proc/uptime
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id 2>/dev/null
printf 'session_uid='; id -u omarchy 2>/dev/null
printf 'hyprland_sig='; ls /run/user/$(id -u omarchy 2>/dev/null)/hypr/ 2>/dev/null | head -1
printf 'shell_running='; pgrep -c quickshell 2>/dev/null || echo 0
printf 'homescreen_qml='; pgrep -f 'quickshell -p /usr/share/omarchy/shell' >/dev/null && echo ja || echo nein
echo "(Kaltstart bis Homescreen: uptime klein, Hyprland-Signatur da, quickshell laeuft)"
