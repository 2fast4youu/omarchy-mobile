19:34:26 ### echo up=$(cut -d. -f1 /proc/uptime)s kernel=$(uname -r)
19:34:26 echo up=$(cut -d. -f1 /proc/uptime)s kernel=$(uname -r)
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
~ # echo up=$(cut -d. -f1 /proc/uptime)s kernel=$(uname -r)
up=838s kernel=7.1.0-rc1-sdm845
~ # [6n
19:34:30 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\000' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | uniq -c
19:34:30 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\000' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | 
uniq -c
      1 OMAMOBILE-SCHREIBTEST-1101
~ # [6n
19:34:34 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -cd '[:print:]\n' | head -c 4000
19:34:34 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -cd '[:print:]\n' | head -c 4000

~ # [6n
19:34:38 ### ls -l /dev/disk/by-partlabel/ 2>&1 | head -30
19:34:38 ls -l /dev/disk/by-partlabel/ 2>&1 | head -30
total 0
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 ALIGN_TO_128K_1 -> ../../sdd1
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 ALIGN_TO_128K_2 -> ../../sdf1
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 ImageFv -> ../../sdf14
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 abl_a -> ../../sde4
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 abl_b -> ../../sde16
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 aop_a -> ../../sde1
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 aop_b -> ../../sde13
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 apdp_a -> ../../sda15
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 apdp_b -> ../../sda16
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 boot_a -> ../../sda11
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 boot_b -> ../../sda12
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 cdt -> ../../sdd2
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 cmnlib64_a -> ../../sde7
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 cmnlib64_b -> ../../sde19
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 cmnlib_a -> ../../sde6
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 cmnlib_b -> ../../sde18
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 ddr -> ../../sdd3
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 devcfg_a -> ../../sde8
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 devcfg_b -> ../../sde20
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 devinfo -> ../../sdf7
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 dip -> ../../sdf8
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 dtbo_a -> ../../sde11
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 dtbo_b -> ../../sde23
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 frp -> ../../sda4
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 fsc -> ../../sdf6
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 fsg -> ../../sdf5
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 hyp_a -> ../../sde3
lrwxrwxrwx    1 0        0               11 Jan  1 00:00 hyp_b -> ../../sde15
lrwxrwxrwx    1 0        0               10 Jan  1 00:00 keymaster_a -> ../../sde5
~ # [6n
19:34:38 === fertig ===
