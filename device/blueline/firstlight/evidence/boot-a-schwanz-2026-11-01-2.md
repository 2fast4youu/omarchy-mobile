19:19:59 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
19:20:00 Fastboot: current-slot: b
19:20:00 vorher: slot-retry-count:b: 1
19:20:00 vorher: slot-unbootable:b: no
19:20:01 set-active=b:                 OKAY [  0.403s] Finished. Total time: 0.483s
19:20:01 nachher: current-slot: b
19:20:01 nachher: slot-retry-count:b: 3
19:20:02 nachher: slot-unbootable:b: no
19:20:13 fastboot boot ref:               OKAY [  9.961s] Finished. Total time: 10.810s 
19:21:31 Telnet offen bei t=78s
19:21:34 ### echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
19:21:34 echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
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
~ # echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null 
| head -30
up=67s
ALIGN_TO_128K_1
ALIGN_TO_128K_2
ImageFv
abl_a
abl_b
aop_a
aop_b
apdp_a
apdp_b
boot_a
boot_b
cdt
cmnlib64_a
cmnlib64_b
cmnlib_a
cmnlib_b
ddr
devcfg_a
devcfg_b
devinfo
dip
dtbo_a
dtbo_b
frp
fsc
fsg
hyp_a
hyp_b
keymaster_a
keymaster_b
~ # [6n
19:21:37 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_geraet=${A:-KEINER}
19:21:37 A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_gera
et=${A:-KEINER}
boot_a_geraet=/dev/sda11
~ # [6n
19:21:40 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
19:21:40 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
0
~ # [6n
19:21:43 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head -150
19:21:43 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head 
-150
~ # [6n
19:21:43 === Lesung fertig ===
