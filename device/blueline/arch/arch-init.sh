#!/bin/sh
# /init der Arch-Wurzel (Omarchy-Basis) auf userdata.
#
# Das Initramfs hat /proc, /sys, /dev, /run und usb0 (172.16.42.1) schon
# aufgebaut und macht `switch_root /ud /init`. Diese Datei ist damit PID 1;
# sie zieht die Pseudo-Dateisysteme nach, die systemd erwartet, und uebergibt
# dann an systemd. Kein Telnet, kein eigener Rueckweg: der Zugang ist SSH
# ueber usb0, der Rueckweg ins Fastboot ist /bin/restart2 im Root.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

mkdir -p /run /dev/pts /dev/shm /tmp
chmod 1777 /tmp 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts 2>/dev/null
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm 2>/dev/null
grep -q ' /run ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=755 tmpfs /run 2>/dev/null

# systemd als PID 1. Es erbt die Mounts des Initramfs, also bleibt die Wurzel
# (/dev/loop0 auf userdata) bestehen.
exec /sbin/init
