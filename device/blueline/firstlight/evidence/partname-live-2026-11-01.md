19:35:04 ### grep -c PARTNAME /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null | grep -v ':0' | head -8
19:35:04 grep -c PARTNAME /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null | grep -v ':0' | head -8
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
~ # grep -c PARTNAME /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null | gre
p -v ':0' | head -8
/sys/block/sda/sda1/uevent:1
/sys/block/sda/sda10/uevent:1
/sys/block/sda/sda11/uevent:1
/sys/block/sda/sda12/uevent:1
/sys/block/sda/sda13/uevent:1
/sys/block/sda/sda14/uevent:1
/sys/block/sda/sda15/uevent:1
/sys/block/sda/sda16/uevent:1
~ # [6n
19:35:08 ### echo PARTNAME-Zeilen in sda-Tree: $(grep -h PARTNAME /sys/block/sda*/uevent 2>/dev/null | wc -l)
19:35:08 echo PARTNAME-Zeilen in sda-Tree: $(grep -h PARTNAME /sys/block/sda*/uevent 
2>/dev/null | wc -l)
PARTNAME-Zeilen in sda-Tree: 0
~ # [6n
19:35:12 ### cat /sys/block/sda/uevent 2>/dev/null | head -5
19:35:12 cat /sys/block/sda/uevent 2>/dev/null | head -5
MAJOR=8
MINOR=0
DEVNAME=sda
DEVTYPE=disk
DISKSEQ=10
~ # [6n
19:35:16 ### grep -l 'PARTNAME=boot_a' /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/null
19:35:16 grep -l 'PARTNAME=boot_a' /sys/block/*/uevent /sys/block/*/*/uevent 2>/dev/n
ull
/sys/block/sda/sda11/uevent
~ # [6n
19:35:20 ### for u in /sys/block/*/uevent /sys/block/*/*/uevent; do grep -qx 'PARTNAME=boot_a' $u && echo TREFFER=$u cat=$(cat $u/dev 2>/dev/null); done
19:35:20 for u in /sys/block/*/uevent /sys/block/*/*/uevent; do grep -qx 'PARTNAME=bo
ot_a' $u && echo TREFFER=$u cat=$(cat $u/dev 2>/dev/null); done
TREFFER=/sys/block/sda/sda11/uevent cat=
~ # [6n
19:35:24 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=1 skip=66060288 count=64 2>/dev/null | od -c | head -6
19:35:24 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=1 skip=66060288 
count=64 2>/dev/null | od -c | head -6
0000000   O   M   A   M   O   B   I   L   E   -   S   C   H   R   E   I
0000020   B   T   E   S   T   -   1   1   0   1  \n  \0  \0  \0  \0  \0
0000040  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0  \0
*
0000100
~ # [6n
19:35:28 ### readlink /sys/block/sda/device 2>/dev/null; ls /sys/block/
19:35:28 readlink /sys/block/sda/device 2>/dev/null; ls /sys/block/
../../../0:0:0:0
[1;36mloop0[m  [1;36mloop2[m  [1;36mloop4[m  [1;36mloop6[m  [1;36msda[m    [1;36msdc[m    [1;36msde[m    [1;36mzram0[m
[1;36mloop1[m  [1;36mloop3[m  [1;36mloop5[m  [1;36mloop7[m  [1;36msdb[m    [1;36msdd[m    [1;36msdf[m
~ # [6n
19:35:28 === fertig ===
