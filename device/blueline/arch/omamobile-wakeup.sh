#!/bin/sh
# Wakeup-Quellen fuer s2idle konfigurieren, damit das Telefon nach dem
# Suspend per Power-Knopf/Touch/USB/RTC aufwacht. Ohne das bleibt es im
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
# RTC (pm8941-rtc): kann per Alarm wecken. Ohne diesen Eintrag bleibt das
# Geraet nach "echo mem" schlafen, weil im s2idle auch der USB-Port
# abgeschaltet wird - dann ist weder SSH noch fastboot erreichbar.
for d in /sys/class/rtc/rtc*/device/power/wakeup; do
    [ -e "$d" ] || continue
    echo enabled > "$d" 2>/dev/null && n=$((n + 1))
done
echo "wakeup aktiviert: $n"
# RTC-Wakealarm pruefen (nur lesen; gesetzt wird er vom Aufrufer)
if [ -e /sys/class/rtc/rtc0/wakealarm ]; then
    echo "rtc0 wakealarm: $(cat /sys/class/rtc/rtc0/wakealarm 2>/dev/null)"
fi
