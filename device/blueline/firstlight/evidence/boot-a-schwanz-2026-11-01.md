17:25:20 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
17:25:20 Fastboot: current-slot: a
17:25:31 fastboot boot ref:               OKAY [ 10.097s] Finished. Total time: 10.887s 
17:28:53 Telnet in 200 s nicht offen — Referenz erreicht, Lesung entfaellt
17:31:01 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
17:31:01 Fastboot: current-slot: a
17:31:12 fastboot boot ref:               OKAY [  9.960s] Finished. Total time: 10.750s 
17:34:36 Telnet in 200 s nicht offen — Referenz erreicht, Lesung entfaellt
17:35:27 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
17:35:28 Fastboot: current-slot: a
17:35:38 fastboot boot ref:               OKAY [  9.960s] Finished. Total time: 10.750s 
17:39:00 Telnet in 200 s nicht offen — Referenz erreicht, Lesung entfaellt
17:39:25 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
17:39:25 Fastboot: current-slot: a
17:39:26 vorher: slot-retry-count:b: 3
17:39:26 vorher: slot-unbootable:b: no
17:39:26 set-active=b:                 OKAY [  0.402s] Finished. Total time: 0.482s
17:39:27 nachher: current-slot: b
17:39:27 nachher: slot-retry-count:b: 3
17:39:27 nachher: slot-unbootable:b: no
17:39:38 fastboot boot ref:               OKAY [  9.957s] Finished. Total time: 10.787s 
17:40:56 Telnet offen bei t=78s
17:40:59 ### echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
17:40:59 echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
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
17:41:02 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_geraet=${A:-KEINER}
17:41:02 A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_gera
et=${A:-KEINER}
boot_a_geraet=/dev/sda11
~ # [6n
17:41:05 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
17:41:05 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
0
~ # [6n
17:41:08 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head -150
17:41:08 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head 
-150
~ # [6n
17:41:08 === Lesung fertig ===
