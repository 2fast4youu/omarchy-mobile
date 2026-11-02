#!/bin/sh
# Misst die Einheit von mount -o offset= am echten Tel: ein Dateisystem liegt
# bei 1 MiB in einem Blockgeraet, und gemessen wird mit DEM mount, das im
# ausgelieferten Ramdisk-Archiv liegt (util-linux 2.41.6, mitgebracht aus
# pack-v0ah), nicht nur mit dem des Containers.
#
# Kein 2>/dev/null: der Fehlerwortlaut ist der eigentliche Beweis.
set -u
WAHL=${WAHL:-/w}
mkdir -p $WAHL /m
cp /alt/mount $WAHL/mount-archiv 2>/dev/null || echo "kein Archiv-mount mitgebracht"
chmod +x $WAHL/mount-archiv 2>/dev/null

dd if=/dev/zero of=$WAHL/fs.bin bs=1M count=2 status=none
mkfs.ext4 -q -F -m 0 $WAHL/fs.bin
dd if=/dev/zero of=$WAHL/traeger.bin bs=1M count=8 status=none
dd if=$WAHL/fs.bin of=$WAHL/traeger.bin bs=1M seek=1 conv=notrunc status=none

# Dem Telefon so aehnlich wie moeglich: ein Blockgeraet, keine Datei.
ls /dev/loop-control >/dev/null 2>&1 || mknod /dev/loop-control c 10 237 2>/dev/null
i=0
while [ $i -lt 8 ]; do
    [ -e "/dev/loop$i" ] || mknod /dev/loop$i b 7 $i 2>/dev/null
    i=$((i + 1))
done
modprobe loop 2>/dev/null
LOS=$(losetup -f --show $WAHL/traeger.bin 2>&1) || { echo "losetup fehlgeschlagen: $LOS"; exit 2; }
echo "Traeger als Blockgeraet: $LOS, Dateisystem beginnt bei 1 MiB = 1048576 B"

for programm in /bin/mount $WAHL/mount-archiv; do
    [ -x "$programm" ] || { echo "--- $programm fehlt"; continue; }
    echo "--- $programm ($($programm --version 2>&1 | head -1))"
    for wert in 1024 2048 1048576; do
        aus=$($programm -o ro,offset=$wert $LOS /m 2>&1); rc=$?
        if [ $rc -eq 0 ]; then
            inhalt=$(ls /m | tr '\n' ' ')
            umount /m
            echo "    offset=$wert -> ERFOLG ($inhalt)"
        else
            echo "    offset=$wert -> FEHLER rc=$rc: $(echo "$aus" | tr '\n' ' ' | cut -c1-110)"
        fi
    done
done
losetup -d $LOS 2>/dev/null
exit 0
