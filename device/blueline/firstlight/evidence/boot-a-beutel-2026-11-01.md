19:56:27 === boot_a-Schwanz: Referenz aus dem RAM, dann dd ===
19:56:27 Fastboot: current-slot: a
19:56:27 vorher: slot-retry-count:b: 2
19:56:28 vorher: slot-unbootable:b: no
19:56:28 set-active=b:                 OKAY [  0.234s] Finished. Total time: 0.313s
19:56:28 nachher: current-slot: b
19:56:29 nachher: slot-retry-count:b: 3
19:56:29 nachher: slot-unbootable:b: no
19:56:40 fastboot boot ref:               OKAY [  9.822s] Finished. Total time: 10.671s 
19:57:58 Telnet offen bei t=78s
19:58:01 ### echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
19:58:01 echo up=$(cut -d. -f1 /proc/uptime)s; ls /dev/disk/by-partlabel 2>/dev/null | head -30
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
19:58:04 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_geraet=${A:-KEINER}
19:58:04 A=$(readlink -f /dev/disk/by-partlabel/boot_a 2>/dev/null); echo boot_a_gera
et=${A:-KEINER}
boot_a_geraet=/dev/sda11
~ # [6n
19:58:07 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
19:58:07 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | grep -c 'OMAMOBILE-LOG'
1
~ # [6n
19:58:10 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head -150
19:58:10 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | sed -n '/OMAMOBILE-LOG/,/ENDOF-LOG/p' | head 
-150
===== OMAMOBILE-LOG v1 up=131s =====
[5s] step: kernel 7.1.0-rc1-sdm845 aarch64
[6s] step: KEIN /usr/lib/modules/7.1.0-rc1-sdm845 - Gadget-Module fehlen
[6s] step: modul libcomposite.ko FEHLER 254
[6s] step: modul u_ether.ko FEHLER 254
[6s] step: modul usb_f_ncm.ko FEHLER 254
[6s] step: modul u_serial.ko FEHLER 254
[6s] step: modul usb_f_acm.ko FEHLER 254
[6s] step: moduli: 1 geladen, usb_f_ncm 0
[6s] step: usb gadget setup (reference sequence)
[6s] step: vor mkdir: configfs=$(grep -c " type configfs " /proc/mounts) libcomposite=$(grep -c libcomposite /proc/modules 2>/dev/null) module=$(wc -l < /proc/modules 2>/dev/null)
[6s] step: nach mount: configfs=$(grep -c " type configfs " /proc/mounts) ordner=$([ -d "$CONFIGFS" ] && echo ja || echo nein) udc=$(ls /sys/class/udc 2>/dev/null | xargs)
[6s] step: usb_gadget not found in configfs, skipping gadget setup
[6s] step: network bring-up
[6s] step: boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
[6s] step: boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
[6s] step: raw log channel live on /dev/sda11
[6s] step: boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
[6s] step: debug shell armed
[6s] step: storage guard pass 1
[6s] step: storage guard pass 1 done
[6s] step: init main flow complete; PID 1 parking
[6s] step: init main flow complete; v0aa steuert den Selbst-Rueckweg an
[6s] step: v0aa wartet das Messfenster der Runde aus
[7s] step: schreib_rc=0 8+0 records in 8+0 records out 1048576 bytes (1.0MB) copied, 0.010877  platte=/dev/sda ro_achter=1
[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[48s] step: dmesg gesichert: /run/dmesg-12s.txt /run/dmesg-2s.txt /run/dmesg-42s.txt 
[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[66s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[81s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[97s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[112s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[127s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[131s] step: warten beendet nach 125s, runde  fertig
[131s] step: v0ab Ziel erreicht: letztes logflush, dann Ablesung, dann Selbst-Rueckweg
[131s] step: udc=a600000.usb module=0 dunkel=888000.i2c geni_i2c: Failed to get tx DMA ch
[131s] step: boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
--- udcs ---
a600000.usb
--- deferred ---
888000.i2c      geni_i2c: Failed to get tx DMA ch
--- gadget ---
--- fb/vt ---
/dev/fb0
/dev/tty0
(M) frame buffer device
--- pstore ---
console-ramoops-0
dmesg-ramoops-0
--- dmesg tail ---
[   26.543521] omamobile-blueline: beat 26s steps:[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   28.585387] omamobile-blueline: beat 28s steps:[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   30.635416] omamobile-blueline: beat 30s steps:[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   32.686881] omamobile-blueline: beat 32s steps:[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   34.739317] omamobile-blueline: beat 34s steps:[21s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   36.326413] ldo22: disabling
[   36.438694] omamobile-blueline:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   36.792063] omamobile-blueline: beat 36s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   38.874418] omamobile-blueline: beat 38s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   40.743537] NOTICE: Automounting of tracing to debugfs is deprecated and will be removed in 2030
[   40.822531] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   40.872518] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   40.947583] omamobile-blueline: beat 40s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   42.955585] omamobile-blueline: beat 42s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   45.035510] omamobile-blueline: beat 45s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   47.114476] omamobile-blueline: beat 47s steps:[36s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   48.049592] omamobile-blueline: dmesg gesichert: /run/dmesg-12s.txt /run/dmesg-2s.txt /run/dmesg-42s.txt 
[   49.202947] omamobile-blueline: beat 49s steps:[48s] step: dmesg gesichert: /run/dmesg-12s.txt /run/dmesg-2s.txt /run/dmesg-42s.txt 
[   51.229258] omamobile-blueline: beat 51s steps:[48s] step: dmesg gesichert: /run/dmesg-12s.txt /run/dmesg-2s.txt /run/dmesg-42s.txt 
[   51.587777] omamobile-blueline:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   53.255389] omamobile-blueline: beat 53s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   55.356478] omamobile-blueline: beat 55s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   57.451218] omamobile-blueline: beat 57s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   59.544782] omamobile-blueline: beat 59s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   60.250172] NOTICE: Automounting of tracing to debugfs is deprecated and will be removed in 2030
[   60.331231] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   60.383622] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   61.638637] omamobile-blueline: beat 61s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   61.688612] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   61.763205] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   63.726281] omamobile-blueline: beat 63s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   65.821432] omamobile-blueline: beat 65s steps:[51s] step:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   66.760512] omamobile-blueline:  | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer | g1 NEU angelegt g1rc=1 funktion=rndis.usb0 knoepfe= | binden rc=1 text=/init: line 459: can't create /sys/kernel/config/usb_gadget/g1/UDC: nonexistent directory | Knopf nicht gedrueckt pfad=/sys/class/udc/a600000.usb/soft_connect gebunden=leer
[   81.113188] NOTICE: Automounting of tracing to debugfs is deprecated and will be removed in 2030
[   81.189246] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[   81.231719] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  100.575456] NOTICE: Automounting of tracing to debugfs is deprecated and will be removed in 2030
[  100.659212] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  100.708033] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  102.070339] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  102.123453] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  120.516427] NOTICE: Automounting of tracing to debugfs is deprecated and will be removed in 2030
[  120.603980] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  120.659539] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  122.038617] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  122.091479] Lockdown: cat: debugfs access is restricted; see man kernel_lockdown.7
[  131.611377] omamobile-blueline: warten beendet nach 125s, runde  fertig
[  131.624611] omamobile-blueline: v0ab Ziel erreicht: letztes logflush, dann Ablesung, dann Selbst-Rueckweg
[  131.646636] omamobile-blueline: udc=a600000.usb module=0 dunkel=888000.i2c geni_i2c: Failed to get tx DMA ch
[  131.670594] omamobile-blueline: boot_a selbst gefunden: sda11 (aus /sys/block/sda/sda11/uevent)
===== ENDOF-LOG =====
~ # [6n
19:58:13 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 count=8 2>/dev/null | tr -d '\0' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | uniq -c
19:58:13 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=131072 skip=504 
count=8 2>/dev/null | tr -d '\0' | grep -ao 'OMAMOBILE[A-Za-z0-9-]*' | sort | un
iq -c
      1 OMAMOBILE-LOG
~ # [6n
19:58:16 ### A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=1 skip=66060288 count=4096 2>/dev/null | tr -dc '[:print:]\n' | head -c 3000
19:58:16 A=$(readlink -f /dev/disk/by-partlabel/boot_a); dd if=$A bs=1 skip=66060288 
count=4096 2>/dev/null | tr -dc '[:print:]\n' | head -c 3000
p
[]tp:rnrr
[]tp:rirtn
[]tp:ipit
[]tp:tr
[]tp:n
[]tp:ri
[]tp:
[]tp:i:nn
[]tp:ttprrnn
[]tp:rir:nirptpniprntipitrpipitprnprn
[]tp:nnt:nirptpniprntrnr[]ninnr
[]tp:tntninniippinttp
[]tp:ntrrinp
[]tp:ttnn:nt
[]tp:ttnn:nt
[]tp:rnnin
[]tp:ttnn:nt
[]tp:r
[]tp:trrp
[]tp:trrpn
[]tp:initinptprin
[]tp:initinpttrtntn
[]tp:rttntrrn
[]tp:rirrrinrrttpipttrtr
[]tp:ntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnr
[]tp:ntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnr
[]tp:irt:rnttrnttrntt
[]tp:ntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnr
[]tp:ntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitrtptnntnnrntrntinrninpinnrttinit:in:ntrtrnnit:nnitntirtrnpnitr~ # [6n
19:58:16 === Lesung fertig ===
