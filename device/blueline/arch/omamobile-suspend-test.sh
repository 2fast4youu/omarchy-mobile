#!/bin/sh
# Suspend-Test mit RTC-Wakeup: schlaeft N Minuten und muss von selbst
# zurueckkommen. Belegt damit (a) dass s2idle funktioniert und (b) dass
# der RTC-Alarm weckt.
#
#   sh omamobile-suspend-test.sh [Minuten]     (Default 10)
set -u
MIN=${1:-10}
SEC=$((MIN * 60))
LOG=/var/log/suspend-test.log

echo "== vor dem Suspend" | tee -a "$LOG"
date -u +%s | tee -a "$LOG"
cat /sys/class/power_supply/qcom-battery/capacity | tee -a "$LOG"
cat /sys/power/suspend_stats/success | tee -a "$LOG"
cat /sys/power/suspend_stats/fail | tee -a "$LOG"

# Wakeup-Quellen (inkl. RTC) freischalten
if [ -x /usr/local/bin/omamobile-wakeup ]; then
    /usr/local/bin/omamobile-wakeup | tee -a "$LOG"
fi

# RTC-Alarm setzen
if [ -w /sys/class/rtc/rtc0/wakealarm ]; then
    echo 0 > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
    echo "+$SEC" > /sys/class/rtc/rtc0/wakealarm 2>/dev/null
    echo "wakealarm: $(cat /sys/class/rtc/rtc0/wakealarm)" | tee -a "$LOG"
else
    echo "FEHLER: /sys/class/rtc/rtc0/wakealarm nicht beschreibbar" | tee -a "$LOG"
    exit 1
fi

# Zeit vor dem Schlafen merken
T0=$(date -u +%s)
echo "suspend fuer $MIN min ($SEC s)" | tee -a "$LOG"
echo mem > /sys/power/state

# Hier geht es erst nach dem Resume weiter
T1=$(date -u +%s)
DT=$((T1 - T0))
echo "== nach dem Resume" | tee -a "$LOG"
echo "geschlafen: ${DT} s (erwartet ~${SEC} s)" | tee -a "$LOG"
cat /sys/class/power_supply/qcom-battery/capacity | tee -a "$LOG"
cat /sys/power/suspend_stats/success | tee -a "$LOG"
cat /sys/power/suspend_stats/fail | tee -a "$LOG"
if [ "$DT" -ge $((SEC - 30)) ] && [ "$DT" -le $((SEC + 120)) ]; then
    echo "ERGEBNIS: RTC-Wakeup FUNKTIONIERT" | tee -a "$LOG"
else
    echo "ERGEBNIS: Wakeup-Zeit unerwartet" | tee -a "$LOG"
fi
