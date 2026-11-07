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
echo "== wlan"; dmesg | grep -i -e 'ath10k' -e 'wlfw' -e 'wlan' | tail -8
echo "== taschenlampe"; ls /sys/class/leds/ 2>/dev/null
echo "== rmtfs/tqftpserv"; pgrep -a rmtfs; pgrep -a tqftpserv; tail -3 /tmp/rmtfs.log 2>/dev/null; tail -3 /tmp/tqftpserv.log 2>/dev/null
echo "== fehler"; dmesg | grep -i -e 'panic' -e 'Oops' -e 'failed' | tail -8
