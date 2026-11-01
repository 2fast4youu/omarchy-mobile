=== Schreibtest boot_a-Ende, an der laufenden Referenz ===
### echo up=$(cut -d. -f1 /proc/uptime)s
echo up=$(cut -d. -f1 /proc/uptime)s
postmarketOS debug shell
https://postmarketos.org/debug-shell

  Device: Google Pixel 3 (google-blueline)
  Kernel: 7.1.0-rc1-sdm845
  OS ver: edge
  initrd: 3.12.5-r0

Run 'pmos_continue_boot' to continue booting.
Read the initramfs log with 'cat /pmOS_init.log'.
Run 'pmos_logdump' to generate a log dump and expose it over USB.
You can expose storage devices over USB with
'setup_usb_storage_configfs /dev/DEVICE'
~ # 
~ # echo up=$(cut -d. -f1 /proc/uptime)s
up=210s
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); echo geraet=$D groesse=$(blockdev --getsize64 $D)
D=$(readlink -f /dev/disk/by-partlabel/boot_a); echo geraet=$D groesse=$(blo
ckdev --getsize64 $D)
geraet=/dev/sda11 groesse=67108864
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); ro=$(blockdev --getro $D); blockdev --setrw $D; echo ro_vor=$ro ro_nach=$(blockdev --getro $D)
D=$(readlink -f /dev/disk/by-partlabel/boot_a); ro=$(blockdev --getro $D); b
lockdev --setrw $D; echo ro_vor=$ro ro_nach=$(blockdev --getro $D)
ro_vor=0 ro_nach=0
~ # [6n
### printf 'OMAMOBILE-SCHREIBTEST-1101\n' > /run/marker.txt; wc -c /run/marker.txt
printf 'OMAMOBILE-SCHREIBTEST-1101\n' > /run/marker.txt; wc -c /run/marker.t
xt
27 /run/marker.txt
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=/run/marker.txt of=$D bs=131072 seek=504 conv=notrunc,fsync 2>&1 | tail -2; rc=$?; echo schreib_rc=$rc
D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=/run/marker.txt of=$D 
bs=131072 seek=504 conv=notrunc,fsync 2>&1 | tail -2; rc=$?; echo schreib_rc=$rc
0+1 records out
27 bytes (27B) copied, 0.004759 seconds, 5.5KB/s
schreib_rc=0
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1 skip=66060288 count=48 2>/dev/null | od -c | head -4
D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1 skip=66060288 
count=48 2>/dev/null | od -c | head -4
0000000   O   M   A   M   O   B   I   L   E   -   S   C   H   R   E   I
0000020   B   T   E   S   T   -   1   1   0   1  \n  \0  \0  \0  \0  \0
0000040  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0
0000060
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); blockdev --setro $D; echo ro_wieder=$(blockdev --getro $D)
D=$(readlink -f /dev/disk/by-partlabel/boot_a); blockdev --setro $D; echo ro
_wieder=$(blockdev --getro $D)
ro_wieder=1
~ # [6n
### D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1M 2>/dev/null | grep -ac OMAMOBILE
D=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$D bs=1M 2>/dev/null |
 grep -ac OMAMOBILE
=== Schreibtest fertig ===
