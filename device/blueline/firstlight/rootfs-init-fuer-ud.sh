#!/bin/sh
# /init IN DER USERDATA-WURZEL (M1.5). Wird vom Initramfs aus mit switch_root
# gestartet; bis hierher hat das Initramfs Gadget, Netzwerk und Shell schon
# stehen — switch_root verlagert nur die Wurzel, der laufende Kernel bleibt.
#
# Dieses Stueck hat genau vier Aufgaben: Pseudo-Dateisysteme nachziehen, eine
# Beleg-Datei auf die echte Partition schreiben, eine Shell offenhalten, und den
# Funkstille-Rueckweg weiterfuehren. Der Rueckweg MUSS hier stehen: wer ihn nur
# im Initramfs haelt, verliert ihn genau in dem Moment, in dem die neue Wurzel
# uebernimmt — dieselbe Klasse wie das Modul hinter dem cpio-TRAILER.
#
# Kein Nicht-ASCII in diesem Block (Regel aus der Bring-up-Arbeit: die Zeilen
# laufen durch mehrere Schichten Text-Transport).
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
# mountpoint -q ist in diesem busybox nicht garantiert — die Liste der
# Mounts selbst ist es, also wird dort nachgesehen.
grep -q ' /proc /proc ' /proc/mounts 2>/dev/null || mount -t proc proc /proc 2>/dev/null
grep -q ' /sys /sys ' /proc/mounts 2>/dev/null || mount -t sysfs sysfs /sys 2>/dev/null
grep -q ' /dev /dev ' /proc/mounts 2>/dev/null || mount -t devtmpfs devtmpfs /dev 2>/dev/null
mkdir -p /dev/pts
grep -q ' /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts 2>/dev/null
mkdir -p /omamobile

# Beleg: was steht wirklich auf '/', und seit wann. Das ist die Erfolgsmeldung
# fuer M1.5, nicht das Verschwinden einer Fehlermeldung.
QUELLE=$(awk '$2=="/"{print $1" "$3" "$4}' /proc/mounts | head -1)
UPTIME=$(cut -d' ' -f1 /proc/uptime)
GADGET=$(ls /sys/kernel/config/usb_gadget 2>/dev/null | tr '\n' ' ')
UDC=$(cat /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null)
NETZ=$(ip -o -4 addr show 2>/dev/null | awk '{print $2" "$4}' | tr '\n' ';')
printf 'switch_root um %s, wurzel=%s, gadget=%s udc=%s netz=%s\n' \
  "$UPTIME" "$QUELLE" "${GADGET:-keins}" "${UDC:-keins}" "${NETZ:-keins}" \
  > /omamobile/beleg-switch-root 2>/dev/null
sync
echo "OMAMOBILE: Wurzel auf userdata, $QUELLE, Shell 172.16.42.1:23" > /dev/console 2>/dev/null

# Shell: der Telnetd-Master aus dem Initramfs laeuft weiter (sein Programm liegt
# im Speicher), also braucht die neue Wurzel nur einen Sprung, falls keiner mehr
# auf 23 horcht. Neue Verbindungen exec /bin/sh — das ist jetzt HIER.
if ! grep -q ':0017 ' /proc/net/tcp 2>/dev/null; then
    if [ -x /usr/sbin/telnetd ]; then
        /usr/sbin/telnetd -l /bin/sh -b 172.16.42.1:23 2>/dev/null
    elif [ -x /usr/bin/nc ]; then
        ( while :; do nc -l -p 23 -e /bin/sh; done ) &
    else
        echo "OMAMOBILE: kein telnetd und kein nc in der neuen Wurzel" > /dev/console
    fi
fi

# Schreibtest auf die echte Partition: ueberlebt er einen Neustart, ist userdata
# wirklich unsere Wurzel (und nicht doch der Initramfs-Tempfs).
echo "geschrieben um $UPTIME" > /omamobile/ueberlebt.txt 2>/dev/null
sync

# Funkstille-Rueckweg, gleiche Logik wie v0af: gehalten durch ein offenes
# Pseudo-Terminal oder /tmp/halt, Zurueck nach 60 Runden a 5s ohne alles,
# Obergrenze 60 Minuten. restart2 liegt in diesem Root unter /bin/restart2.
stille=0
wachen=0
while [ "$wachen" -lt 720 ]; do
    wer=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c /dev/pts)
    if [ -e /tmp/halt ] || [ "${wer:-0}" -gt 0 ]; then
        stille=0
    else
        stille=$((stille + 1))
        [ "$stille" -ge 60 ] && break
    fi
    sleep 5
    wachen=$((wachen + 1))
done
sync
echo "OMAMOBILE: Funkstille $stille Runden nach $((wachen * 5))s, rueckweg nach fastboot" \
  > /dev/console 2>/dev/null
if [ -x /bin/restart2 ]; then
    /bin/restart2
elif [ -x /usr/bin/restart2 ]; then
    /usr/bin/restart2
fi
exec /bin/sh
