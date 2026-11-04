#!/bin/sh
# Eigenstaendige /init der Arch-Wurzel (ohne systemd).
#
# Belegt am 2026-11-04: der Uebergang switch_root -> /init traegt, und das
# Arch-Root laeuft (Getty meldet "Arch Linux ARM 7.1.0-rc1-sdm845"). Der
# systemd-Start als PID 1 endet dagegen mit Exit 127; solange das nicht
# geklaert ist, bringt diese Fassung das System ohne systemd hoch:
#   - sshd auf usb0 (172.16.42.1), Root nur per Schluessel
#   - eine Root-Shell auf ttyGS0 (ACM-Konsole am Mac)
#   - PID 1 parkt; kein Panic, kein Reboot.
# Damit ist die Wurzel interaktiv und per Netz erreichbar - die Basis, auf der
# systemd und danach Omarchy nachgezogen werden.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

mkdir -p /run /run/sshd /dev/pts /dev/shm /tmp
chmod 1777 /tmp /dev/shm 2>/dev/null
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts 2>/dev/null
grep -q ' /dev/shm ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=1777 tmpfs /dev/shm 2>/dev/null
grep -q ' /run ' /proc/mounts 2>/dev/null || mount -t tmpfs -o mode=755 tmpfs /run 2>/dev/null
hostname omamobile 2>/dev/null

# Initramfs-Reste toeten: der Getty-Loop haelt ttyGS0 (zwei Leser zerlegen
# jede Eingabe), Dropbear haelt Port 22 und stirbt nach switch_root an
# fehlendem /dev/urandom. Beides muss weg, bevor sshd und unsere Shell starten.
for p in /proc/[0-9]*; do
    [ "${p##*/}" = 1 ] && continue
    cmd=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
    case "$cmd" in
        "/bin/sh /init "*) kill -9 "${p##*/}" 2>/dev/null ;;
        dropbear*) kill -9 "${p##*/}" 2>/dev/null ;;
    esac
done
sleep 1

/usr/bin/ssh-keygen -A 2>/dev/null
/usr/sbin/sshd 2>/dev/null
echo "omamobile: Arch-Wurzel bereit, sshd auf 172.16.42.1:22" > /dev/kmsg 2>/dev/null

# Serielle Root-Shell auf der ACM-Konsole (kein Login, nur am Kabel).
( while :; do setsid /bin/sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1; sleep 2; done ) &

# PID 1 bleibt am Leben. Kein exec systemd, solange der 127 nicht erklaert ist.
while :; do sleep 3600; done
