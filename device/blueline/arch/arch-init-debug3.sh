#!/bin/sh
# Debug-/init 3: kein systemd, PID 1 parkt, ein Getty auf ttyGS0 gibt Zugang.
# Damit ist der Arch-Root interaktiv pruefbar (ls, chroot-Tests, systemd-Diagnose).
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
exec >/dev/kmsg 2>&1
echo "ARCHINIT3: start uptime=$(cut -d. -f1 /proc/uptime)"
mkdir -p /run /dev/pts /dev/shm /tmp
chmod 1777 /tmp /dev/shm 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm
echo "ARCHINIT3: mounts ok; sh=$(ls -l /bin/sh 2>&1 | tr '\n' ' ')"
echo "ARCHINIT3: init=$(ls -l /sbin/init /usr/lib/systemd/systemd 2>&1 | tr '\n' ' ')"
( while :; do setsid /bin/sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1; sleep 2; done ) &
echo "ARCHINIT3: shell auf ttyGS0, PID 1 parkt"
while :; do sleep 3600; done
