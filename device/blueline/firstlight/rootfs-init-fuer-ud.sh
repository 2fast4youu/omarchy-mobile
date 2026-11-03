#!/bin/sh
# /init IN DER USERDATA-WURZEL (M1.5). Wird vom Initramfs aus mit switch_root
# gestartet; bis hierher hat das Initramfs Gadget, Netzwerk und Shell schon
# stehen - switch_root verlagert nur die Wurzel, der laufende Kernel bleibt.
#
# Dieses Stueck hat genau vier Aufgaben: Pseudo-Dateisysteme nachziehen, eine
# Beleg-Datei auf die echte Partition schreiben, eine Shell offenhalten, und den
# Funkstille-Rueckweg weiterfuehren. Der Rueckweg MUSS hier stehen: wer ihn nur
# im Initramfs haelt, verliert ihn genau in dem Moment, in dem die neue Wurzel
# uebernimmt - dieselbe Klasse wie das Modul hinter dem cpio-TRAILER.
#
# Kein Nicht-ASCII in diesem Block (Regel aus der Bring-up-Arbeit: die Zeilen
# laufen durch mehrere Schichten Text-Transport).
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
# mountpoint -q ist in diesem busybox nicht garantiert - die Liste der
# Mounts selbst ist es, also wird dort nachgesehen.
grep -q '^[^ ]* /proc ' /proc/mounts 2>/dev/null || mount -t proc proc /proc 2>/dev/null
grep -q '^[^ ]* /sys ' /proc/mounts 2>/dev/null || mount -t sysfs sysfs /sys 2>/dev/null
grep -q '^[^ ]* /dev ' /proc/mounts 2>/dev/null || mount -t devtmpfs devtmpfs /dev 2>/dev/null
mkdir -p /dev/pts
grep -q '^[^ ]* /dev/pts ' /proc/mounts 2>/dev/null || mount -t devpts devpts /dev/pts 2>/dev/null
mkdir -p /omamobile

# ---------------------------------------------------------------------------
# Die Platte offenhalten, fuer die ganze Laufzeit. switch_root laesst die
# Hintergrundprozesse des Initramfs laufen, aber seine Halteschleife lebte im
# Init-Skript selbst und stirbt in dem Moment, in der switch_root die Wurzel
# ersetzt. Danach legt die Storage-Wache die UFS-Platte wieder unter ro, und
# ext4 verliert den naechsten Schreibvorgang. Gemessen 2026-11-03 15:2x in der
# ersten erfolgreichen Uebergabe: 'EXT4-fs (loop0): I/O error while writing
# superblock', 'Remounting filesystem read-only' bei Uptime 169 s, dazu
# blockdev --getro = 1 auf Platte UND Partition, waehrend loop0 selbst rw meldet.
# Getragen wird, was in der Mount-Zeile der Wurzel steht - bei einem Loop-Geraet
# der Datentraeger dahinter, denn die Partition folgt dem Schalter der Platte.
#
# Wo der Traeger steht, ist auf diesem Kernel anders als angenommen (gemessen
# 2026-11-03 an dem Boot, der bei 169 s auf ro fiel): der Sysfs-Zweig des
# Loop-Geraets heisst `/sys/class/block/loop0/loop/` mit den Attributen
# autoclear, backing_file, dio, offset, partscan, sizelimit - es gibt dort
# weder ein Untergeordnetes `loop0/`-Ordnerchen noch eine Datei `backing_dev`.
# Die erste Fassung suchte `loop/<name>/backing_dev`, fand nichts und hielt damit
# ein Geraet namens `keins`. Gesucht wird jetzt in allen drei bekannten Formen,
# und wenn keine davon etwas hergibt, fragt das Skript das Werkzeug selbst:
# busybox antwortet auf `losetup /dev/loop0` mit '/dev/loop0: 1048576 /dev/sda21',
# util-linux mit '/dev/loop0: [65025]:1234 (/dev/sda21)' - in beiden steht der
# Geraetepfad am Zeilenende. Namen sind dabei nur die halbe Wahrheit: die
# Minorzahl ist der bestaendige Schluessel, die Namen wandern zwischen Bootes.
# ---------------------------------------------------------------------------
WURZEL=$(awk '$2=="/" {print $1; exit}' /proc/mounts 2>/dev/null)
HALTETRN=""   # leer = nichts zu halten; die Schleife sagt das im Herzschlag
TRAGER=""
case "${WURZEL:-}" in
    /dev/loop*)
        GRUND=${WURZEL##*/}
        for pfad in "/sys/class/block/$GRUND/loop/backing_file" \
                    "/sys/block/$GRUND/loop/backing_file" \
                    "/sys/class/block/$GRUND/loop/$GRUND/backing_dev" \
                    "/sys/block/$GRUND/loop/$GRUND/backing_dev"; do
            if [ -f "$pfad" ]; then
                TRAGER=$(cat "$pfad" 2>/dev/null)
                [ -n "${TRAGER:-}" ] && break
            fi
        done
        if [ -z "${TRAGER:-}" ]; then
            TRAGER=$(losetup "$WURZEL" 2>/dev/null | tail -1 | sed -e 's/.*[ (]//' -e 's/)$//')
        fi
        ;;
esac
# Traeger (und jede andere haengende Partition) in die Halteliste: der Name wird
# ueber /sys/class/block/<name> aufgeloest - dieser Zweig schluesselt nach Namen,
# /sys/dev/block nach major:minor, und genau diese Verwechslung war Wurzel #22.
for knotenpfad in "${TRAGER:-}" $(awk '$3!="rootfs" && $1 ~ /^\/dev\/sd/ {print $1}' /proc/mounts 2>/dev/null); do
    [ -n "$knotenpfad" ] || continue
    case "$knotenpfad" in
        /dev/*) BASIS=${knotenpfad##*/} ;;
        *)      # aeltere Kernel nennen in backing_dev eine minor:minor-Nummer statt
                # eines Pfades; die steht nur in /sys/dev/block, nie unter dem Namen
                BASIS=$(basename "$(readlink -f "/sys/dev/block/$knotenpfad")" 2>/dev/null) ;;
    esac
    [ -n "${BASIS:-}" ] || continue
    case " $HALTETRN " in *" $BASIS "*) continue ;; esac
    if [ -e "/sys/class/block/$BASIS" ]; then
        ELTERN=$(basename "$(dirname "$(readlink -f "/sys/class/block/$BASIS")")" 2>/dev/null)
        if [ "$ELTERN" = block ]; then
            HALTETRN="$HALTETRN $BASIS"           # Wurzel auf einer ganzen Platte
        else
            HALTETRN="$HALTETRN $ELTERN $BASIS"   # Platte zuerst, dann die Partition
        fi
    fi
done
HALTETRN=$(printf '%s' "$HALTETRN" | sed -e 's/^ //')

# Halten, gegenmessen, melden. Die Gegenmessung ist der eigentliche Grund, diese
# Fassung zu bauen: eine Schleife, die gegen ein nicht existentes Geraet laeuft,
# sah bisher von aussen lebendig aus. Alle 30 Runden geht eine Zeile nach
# /dev/kmsg, die Traeger und gemessene ro-Schalter zusammen nennt - damit steht
# kinftig in dmesg, ob gehalten wird, statt dass eine Lesung das raten muss.
(
  runden=0
  while :; do
    for knoten in $HALTETRN; do
      blockdev --setrw "/dev/$knoten" 2>/dev/null
    done
    runden=$((runden + 1))
    if [ $((runden % 30)) -eq 1 ]; then
      schalter=""
      for knoten in $HALTETRN; do
        schalter="$schalter $knoten=$(blockdev --getro "/dev/$knoten" 2>/dev/null)"
      done
      echo "omamobile: halte=${HALTETRN:-keins} ro=${schalter:-keins} zeit=$(cut -d. -f1 /proc/uptime)" \
        > /dev/kmsg 2>/dev/null
    fi
    sleep 1
  done ) &

# ---------------------------------------------------------------------------
# Sichtbar machen, was hier laeuft. switch_root haelt den Kernel, aber es haengt
# auch das configfs ab: der Gadget-Satz des Initramfs ist damit weg, und ohne
# Netz ist diese Wurzel fuer den Mac taub - genau so in der Nacht auf den
# 2026-11-03 gemessen: kein Ping auf 172.16.42.1, kein Port 23, nur der
# USB-Name 'Pixel 3 (blueline)' am Baum. Der Block folgt Zeile fuer Zeile dem
# arbeitenden Gadget-Block des Initramfs (idVendor 18D1, idProduct D002,
# ncm.usb0 + acm.GS0, Konfiguration c.1, dann der UDC-Write, dann ifconfig).
# ---------------------------------------------------------------------------
mkdir -p /sys/kernel/config
grep -q '^[^ ]* /sys/kernel/config ' /proc/mounts 2>/dev/null \
  || mount -t configfs -o nodev,noexec,nosuid configfs /sys/kernel/config 2>/dev/null
CFG=/sys/kernel/config/usb_gadget
NETZ=keins
if ! [ -d "$CFG/g1" ]; then
    UDCNEU=$(ls /sys/class/udc 2>/dev/null | head -1)
    if [ -n "${UDCNEU:-}" ]; then
        mkdir -p "$CFG/g1/strings/0x409" "$CFG/g1/functions" "$CFG/g1/configs/c.1/strings/0x409"
        echo 0x18D1 > "$CFG/g1/idVendor" 2>/dev/null
        echo 0xD002 > "$CFG/g1/idProduct" 2>/dev/null
        echo 'Omarchy Mobile' > "$CFG/g1/strings/0x409/manufacturer" 2>/dev/null
        echo 'omamobile-blueline' > "$CFG/g1/strings/0x409/serialnumber" 2>/dev/null
        echo 'Pixel 3 (blueline)' > "$CFG/g1/strings/0x409/product" 2>/dev/null
        NETF=ncm.usb0
        mkdir "$CFG/g1/functions/$NETF" 2>/dev/null \
          || { mkdir "$CFG/g1/functions/rndis.usb0" 2>/dev/null && NETF=rndis.usb0; }
        echo 'USB network' > "$CFG/g1/configs/c.1/strings/0x409/configuration" 2>/dev/null
        ln -s "$CFG/g1/functions/$NETF" "$CFG/g1/configs/c.1" 2>/dev/null
        mkdir "$CFG/g1/functions/acm.GS0" 2>/dev/null \
          && ln -s "$CFG/g1/functions/acm.GS0" "$CFG/g1/configs/c.1" 2>/dev/null
        sleep 1
        echo "$UDCNEU" > "$CFG/g1/UDC" 2>/dev/null
    fi
fi
ip link set lo up 2>/dev/null
z=0
while [ "$z" -lt 30 ]; do
    for iface in usb0 eth0 ncm0; do
        if [ -e "/sys/class/net/$iface" ]; then
            ip link set "$iface" up 2>/dev/null
            ifconfig "$iface" 172.16.42.1 2>/dev/null
            NETZ=$iface
            break 2
        fi
    done
    z=$((z + 1)); sleep 1
done

# Frueher Stempel, VOR dem Gadget-Kram: der Boot von 15:34 ist bei 169 s auf ro
# gefallen, und der spaete Stempel hat deshalb nie die Partition erreicht -
# /omamobile/LEBEN existierte in diesem Boot ueberhaupt nicht. Der fruehe Stempel
# liegt auf der Platte, solange sie noch offen ist, und sagt zumindest, dass
# diese Wurzel uebernommen hat und was sie vorhat offen zu halten.
{
    echo "frueh-zeit=$(date -u +%FT%TZ) uptime=$(cut -d' ' -f1 /proc/uptime)"
    echo "halte=${HALTETRN:-keins} ro_vorher=$(for k in ${HALTETRN:-}; do printf '%s=%s ' \"$k\" \"$(blockdev --getro \"/dev/$k\" 2>/dev/null)\"; done)"
} > /omamobile/LEBEN-frueh 2>/dev/null
sync

# Stempel auf der echten Partition: wann hat diese Wurzel uebernommen, von wo
# und mit welchem Kernel. Das ist der Beleg fuer M1.5, nicht das Fehlen einer
# Fehlermeldung. Datei bleibt, ein Neustart mit switch_root schreibt sie um.
{
    echo "uebergabe-zeit=$(date -u +%FT%TZ)"
    echo "uptime=$(cut -d' ' -f1 /proc/uptime)"
    echo "wurzel=$(awk '$2=="/"{print $1" "$3" "$4}' /proc/mounts | head -1)"
    echo "kernel=$(uname -r)"
    echo "netz=$NETZ udc=$(cat $CFG/g1/UDC 2>/dev/null)"
    echo "halte=${HALTETRN:-keins} ro=$(blockdev --getro "/dev/${HALTETRN%% *}" 2>/dev/null)/$(blockdev --getro "/dev/${HALTETRN##* }" 2>/dev/null)"
} > /omamobile/LEBEN 2>/dev/null
sync
( while :; do telnetd -l /bin/sh; sleep 2; done ) &


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
# auf 23 horcht. Neue Verbindungen exec /bin/sh - das ist jetzt HIER.
if ! grep -q ':0017 ' /proc/net/tcp 2>/dev/null; then
    if [ -x /usr/sbin/telnetd ]; then
        /usr/sbin/telnetd -l /bin/sh -b 172.16.42.1:23 2>/dev/null
    elif [ -x /usr/bin/nc ]; then
        # ohne Schlaf dreht dieser Zweier durch, wenn Port 23 schon belegt ist
        ( while :; do nc -l -p 23 -e /bin/sh; sleep 2; done ) &
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
