19:40:44 ### echo anfang sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
19:40:44 echo anfang sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
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
~ # echo anfang sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/s
da11)
anfang sda=0 sda11=0
~ # [6n
19:40:50 ### blockdev --setro /dev/sda; blockdev --setrw /dev/sda11; echo gesetzt sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
19:40:50 blockdev --setro /dev/sda; blockdev --setrw /dev/sda11; echo gesetzt sda=$(b
lockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
gesetzt sda=1 sda11=1
~ # [6n
19:40:56 ### printf 'OMAMOBILE-RO-BLOCK-1101\n' > /tmp/p; dd if=/tmp/p of=/dev/sda11 bs=131072 seek=504 conv=notrunc,fsync; echo dd_rc=$?
19:40:56 printf 'OMAMOBILE-RO-BLOCK-1101\n' > /tmp/p; dd if=/tmp/p of=/dev/sda11 bs=1
31072 seek=504 conv=notrunc,fsync; echo dd_rc=$?
dd: error writing '/dev/sda11': Operation not permitted
0+1 records in
0+0 records out
0 bytes (0B) copied, 0.000136 seconds, 0B/s
dd_rc=1
~ # [6n
19:41:02 ### dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3
19:41:02 dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3
0000000   O   M   A   M   O   B   I   L   E   -   S   C   H   R   E   I
0000020   B   T   E   S   T   -   1   1   0   1  \n  \0  \0  \0  \0  \0
0000040
~ # [6n
19:41:08 ### blockdev --setrw /dev/sda; echo platte_rw=$(blockdev --getro /dev/sda); dd if=/tmp/p of=/dev/sda11 bs=131072 seek=504 conv=notrunc,fsync; echo dd_rc=$?
19:41:08 blockdev --setrw /dev/sda; echo platte_rw=$(blockdev --getro /dev/sda); dd i
f=/tmp/p of=/dev/sda11 bs=131072 seek=504 conv=notrunc,fsync; echo dd_rc=$?
platte_rw=0
0+1 records in
0+1 records out
24 bytes (24B) copied, 0.004474 seconds, 5.2KB/s
dd_rc=0
~ # [6n
19:41:14 ### dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3
19:41:14 dd if=/dev/sda11 bs=1 skip=66060288 count=32 2>/dev/null | od -c | head -3
0000000   O   M   A   M   O   B   I   L   E   -   R   O   -   B   L   O
0000020   C   K   -   1   1   0   1  \n   0   1  \n  \0  \0  \0  \0  \0
0000040
~ # [6n
19:41:20 ### blockdev --setro /dev/sda; blockdev --setro /dev/sda11; echo Ende sda=$(blockdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
19:41:20 blockdev --setro /dev/sda; blockdev --setro /dev/sda11; echo Ende sda=$(bloc
kdev --getro /dev/sda) sda11=$(blockdev --getro /dev/sda11)
Ende sda=1 sda11=1
~ # [6n
19:41:20 === fertig ===
