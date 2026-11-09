#!/bin/sh
# Wakeup-Quellen fuer s2idle konfigurieren, damit das Telefon nach dem
# Suspend per Power-Knopf/Touch/USB aufwacht. Ohne das bleibt es im
# Suspend (keine RTC im mainline-Boot).
set -u
n=0
for d in /sys/devices/platform/soc@0/c440000.spmi/spmi-0/0-00/*/power/wakeup \
         /sys/devices/platform/soc@0/c440000.spmi/spmi-0/0-02/*/power/wakeup \
         /sys/bus/i2c/devices/*/power/wakeup \
         /sys/devices/platform/soc@0/*/power/wakeup; do
    [ -e "$d" ] || continue
    echo enabled > "$d" 2>/dev/null && n=$((n + 1))
done
# Power-Knopf und Resin explizit (pm8941_pwrkey/resin)
for d in /sys/devices/platform/soc@0/c440000.spmi/spmi-0/0-00/*/power/wakeup; do
    [ -e "$d" ] && echo enabled > "$d" 2>/dev/null
done
echo "wakeup aktiviert: $n"
