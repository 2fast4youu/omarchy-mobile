#!/bin/sh
# Debug-/init 2: Arch-Root ohne systemd, aber mit eigenem sshd. Damit ist
# pruefbar, ob das Root selbst traegt, und der Zugang fuer die systemd-Diagnose
# steht. PID 1 bleibt am Leben (kein Panic), wenn etwas fehlt.
exec >/dev/kmsg 2>&1
echo "ARCHINIT2: start uptime=$(cut -d. -f1 /proc/uptime)"
mkdir -p /run /run/sshd /dev/pts /dev/shm /tmp
chmod 1777 /tmp /dev/shm 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm
echo "ARCHINIT2: mounts ok"
/usr/bin/ssh-keygen -A 2>/dev/null
pkill -x dropbear 2>/dev/null
/usr/sbin/sshd -e 2>/dev/null
echo "ARCHINIT2: sshd rc=$? pid=$(cat /run/sshd.pid 2>/dev/null)"
echo "ARCHINIT2: ip=$(ip -o -4 addr show 2>/dev/null | tr '\n' ' ')"
echo "ARCHINIT2: bereit, PID 1 parkt"
while :; do sleep 3600; done
