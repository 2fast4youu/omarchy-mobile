#!/bin/sh
# Debug-/init: schreibt jeden Schritt nach /dev/kmsg, damit pstore nach einem
# Fehlschlag zeigt, wie weit der Uebergang kam.
exec >/dev/kmsg 2>&1
echo "ARCHINIT: start uptime=$(cut -d. -f1 /proc/uptime)"
echo "ARCHINIT: ls init $(ls -l /sbin/init /usr/lib/systemd/systemd /bin/sh 2>&1 | tr '\n' ' ')"
mkdir -p /run /dev/pts /dev/shm /tmp
chmod 1777 /tmp 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts
echo "ARCHINIT: devpts rc=$?"
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm
echo "ARCHINIT: shm rc=$?"
grep -q ' /run ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=755 tmpfs /run
echo "ARCHINIT: run rc=$?"
echo "ARCHINIT: mounts $(grep -E ' /(run|dev/pts|dev/shm) ' /proc/mounts | tr '\n' '|')"
echo "ARCHINIT: exec /sbin/init"
exec /sbin/init
echo "ARCHINIT: exec fehlgeschlagen rc=$?"
while :; do sleep 60; done
