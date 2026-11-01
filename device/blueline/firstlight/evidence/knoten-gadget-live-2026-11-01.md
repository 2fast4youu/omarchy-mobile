19:36:06 ### ls -l /sys/class/block/sda11/ 2>&1 | head -20
19:36:06 ls -l /sys/class/block/sda11/ 2>&1 | head -20
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
~ # ls -l /sys/class/block/sda11/ 2>&1 | head -20
total 0
-r--r--r--    1 0        0             4096 Jan  1 00:15 alignment_offset
-r--r--r--    1 0        0             4096 Jan  1 00:00 dev
-r--r--r--    1 0        0             4096 Jan  1 00:15 discard_alignment
drwxr-xr-x    2 0        0                0 Jan  1 00:15 holders
-r--r--r--    1 0        0             4096 Jan  1 00:15 inflight
-r--r--r--    1 0        0             4096 Jan  1 00:00 partition
drwxr-xr-x    2 0        0                0 Jan  1 00:15 power
-r--r--r--    1 0        0             4096 Jan  1 00:15 ro
-r--r--r--    1 0        0             4096 Jan  1 00:00 size
-r--r--r--    1 0        0             4096 Jan  1 00:00 start
-r--r--r--    1 0        0             4096 Jan  1 00:15 stat
lrwxrwxrwx    1 0        0                0 Jan  1 00:15 subsystem -> ../../../../../../../../../../class/block
-rw-r--r--    1 0        0             4096 Jan  1 00:00 uevent
~ # [6n
19:36:10 ### echo class-dev=$(cat /sys/class/block/sda11/dev 2>/dev/null) block-dev=$(cat /sys/block/sda/sda11/dev 2>/dev/null) stat=$(stat -c '%t %T' /dev/sda11 2>/dev/null)
19:36:10 echo class-dev=$(cat /sys/class/block/sda11/dev 2>/dev/null) block-dev=$(cat
 /sys/block/sda/sda11/dev 2>/dev/null) stat=$(stat -c '%t %T' /dev/sda11 2>/dev/
null)
class-dev=8:11 block-dev=8:11 stat=8 b
~ # [6n
19:36:14 ### for p in sda11 sde11; do echo $p uevent:; cat /sys/block/sda/$p/uevent 2>/dev/null || cat /sys/block/sde/$p/uevent 2>/dev/null; done | head -20
19:36:14 for p in sda11 sde11; do echo $p uevent:; cat /sys/block/sda/$p/uevent 2>/de
v/null || cat /sys/block/sde/$p/uevent 2>/dev/null; done | head -20
sda11 uevent:
MAJOR=8
MINOR=11
DEVNAME=sda11
DEVTYPE=partition
DISKSEQ=10
PARTN=11
PARTNAME=boot_a
PARTUUID=597de9ae-b417-439d-ab3c-85526db3866f
sde11 uevent:
MAJOR=8
MINOR=75
DEVNAME=sde11
DEVTYPE=partition
DISKSEQ=14
PARTN=11
PARTNAME=dtbo_a
PARTUUID=84241bae-5265-4a50-bf44-ffbbfcee664b
~ # [6n
19:36:18 ### echo ueventd=$(ls /sys/class/uevent 2>/dev/null | head -2) mdev=$(which mdev) ueventd_p=$(which ueventd) hotplug=$(cat /proc/sys/kernel/hotplug 2>/dev/null)
19:36:18 echo ueventd=$(ls /sys/class/uevent 2>/dev/null | head -2) mdev=$(which mdev
) ueventd_p=$(which ueventd) hotplug=$(cat /proc/sys/kernel/hotplug 2>/dev/null)
ueventd= mdev=/usr/bin/mdev ueventd_p= hotplug=
~ # [6n
19:36:22 ### echo init=$(cat /proc/1/cmdline | tr '\0' ' ') pid1=$(readlink /proc/1/exe)
19:36:22 echo init=$(cat /proc/1/cmdline | tr '\0' ' ') pid1=$(readlink /proc/1/exe)
init=/bin/busybox ash /init_2nd.sh pid1=/usr/bin/busybox
~ # [6n
19:36:26 ### echo --- GADGET ---; ls /sys/kernel/config 2>&1 | head -3; mount | grep -E 'config|debugfs' ; ls /sys/kernel/config/usb_gadget 2>&1 | head -5; ls /sys/class/udc 2>&1
19:36:26 echo --- GADGET ---; ls /sys/kernel/config 2>&1 | head -3; mount | grep -E '
config|debugfs' ; ls /sys/kernel/config/usb_gadget 2>&1 | head -5; ls /sys/class
/udc 2>&1
--- GADGET ---
pci_ep
usb_gadget
configfs on /sys/kernel/config type configfs (rw,nosuid,nodev,noexec,relatime)
none on /sys/kernel/debug type debugfs (rw,relatime)
g1
[1;36ma600000.usb[m
~ # [6n
19:36:30 ### echo --- libcomposite ---; grep -c libcomposite /proc/modules; lsmod 2>/dev/null | grep -E 'libcomposite|udc|ncm|mass_storage|g_ether' | head -8
19:36:30 echo --- libcomposite ---; grep -c libcomposite /proc/modules; lsmod 2>/dev/
null | grep -E 'libcomposite|udc|ncm|mass_storage|g_ether' | head -8
--- libcomposite ---
1
usb_f_mass_storage     73728  2 
usb_f_ncm              32768  2 
u_ether                36864  1 usb_f_ncm
libcomposite           98304 16 usb_f_acm,u_serial,usb_f_mass_storage,usb_f_ncm,u_ether
~ # [6n
19:36:34 ### cat /sys/kernel/debug/devices_deferred 2>&1 | head -8
19:36:34 cat /sys/kernel/debug/devices_deferred 2>&1 | head -8
~ # [6n
19:36:34 === fertig ===
