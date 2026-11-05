#!/bin/sh
# Sammelt den Zustand des laufenden Systems fuer die Haenger-Analyse.
# Aufruf auf dem Telefon: sh omamobile-health.sh > /tmp/health.txt
echo "== uptime/load"; uptime; cat /proc/loadavg
echo "== speicher"; free -m 2>/dev/null | head -3
echo "== temperatur"; for t in /sys/class/thermal/thermal_zone*/temp; do
    [ -e "$t" ] && echo "$(dirname "$t"): $(cat "$t" 2>/dev/null)"
done
echo "== pstore"; ls -la /sys/fs/pstore 2>/dev/null; for f in /sys/fs/pstore/*; do
    [ -f "$f" ] && echo "--- $f" && head -40 "$f"
done
echo "== dmesg fehler"; dmesg 2>/dev/null | grep -i -e 'error' -e 'fail' -e 'hang' -e 'timeout' -e 'oom' | tail -25
echo "== gpu/dsi"; dmesg 2>/dev/null | grep -i -e adreno -e dsi -e msm | tail -8
echo "== prozesse"; ps -eo pid,pcpu,pmem,comm 2>/dev/null | sort -k2 -nr | head -8
echo "== ufs"; cat /proc/partitions | head -4
