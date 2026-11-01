20:13:06 eigene Shell offen nach 24s
20:13:10 ### echo up=$(cut -d. -f1 /proc/uptime)s
20:13:10 echo up=$(cut -d. -f1 /proc/uptime)s
~ # 
~ # echo up=$(cut -d. -f1 /proc/uptime)s
up=13s
~ # [6n
20:13:14 ### uname -a
20:13:14 uname -a
Linux (none) 7.1.0-rc1-sdm845 #5-postmarketos-qcom-sdm845 SMP PREEMPT Tue Jul 14 03:51:45 UTC  aarch64 Linux
~ # [6n
20:13:18 ### echo moduli=$(wc -l < /proc/modules)
20:13:18 echo moduli=$(wc -l < /proc/modules)
moduli=5
~ # [6n
20:13:22 ### grep -c libcomposite /proc/modules
20:13:22 grep -c libcomposite /proc/modules
1
~ # [6n
20:13:26 ### ls /sys/class/udc
20:13:26 ls /sys/class/udc
[1;36ma600000.usb[m
~ # [6n
20:13:30 ### cat /sys/class/udc/*/state 2>/dev/null
20:13:30 cat /sys/class/udc/*/state 2>/dev/null
configured
~ # [6n
20:13:34 ### ls /sys/kernel/config/usb_gadget
20:13:34 ls /sys/kernel/config/usb_gadget
[1;34mg1[m
~ # [6n
20:13:38 ### cat /sys/kernel/config/usb_gadget/g1/UDC
20:13:38 cat /sys/kernel/config/usb_gadget/g1/UDC
a600000.usb
~ # [6n
20:13:42 ### ls /sys/kernel/config/usb_gadget/g1/functions
20:13:42 ls /sys/kernel/config/usb_gadget/g1/functions
[1;34macm.GS0[m   [1;34mncm.usb0[m
~ # [6n
20:13:46 ### ls /sys/kernel/config/usb_gadget/g1/strings/0x1
20:13:46 ls /sys/kernel/config/usb_gadget/g1/strings/0x1
ls: /sys/kernel/config/usb_gadget/g1/strings/0x1: No such file or directory
~ # [6n
20:13:50 ### ip -o addr show 2>/dev/null | head -6
20:13:50 ip -o addr show 2>/dev/null | head -6
1: lo    inet 127.0.0.1/8 scope host lo\       valid_lft forever preferred_lft forever
1: lo    inet6 ::1/128 scope host proto kernel_lo \       valid_lft forever preferred_lft forever
3: usb0    inet 172.16.42.1/16 brd 172.16.255.255 scope global usb0\       valid_lft forever preferred_lft forever
3: usb0    inet 172.16.42.1/24 scope global usb0\       valid_lft forever preferred_lft forever
3: usb0    inet6 fe80::8f0:85ff:fe5b:622c/64 scope link proto kernel_ll \       valid_lft forever preferred_lft forever
~ # [6n
20:13:54 ### echo module_da: $(ls /usr/lib/modules/*/kernel/drivers/usb/gadget/*.ko 2>/dev/null | wc -l)
20:13:54 echo module_da: $(ls /usr/lib/modules/*/kernel/drivers/usb/gadget/*.ko 2>/de
v/null | wc -l)
module_da: 1
~ # [6n
20:13:58 ### tail -24 /run/steps.log
20:13:58 tail -24 /run/steps.log
[5s] step: usb gadget setup (reference sequence)
[5s] step: vor mkdir: configfs=$(grep -c " type configfs " /proc/mounts) libcomposite=$(grep -c libcomposite /proc/modules 2>/dev/null) module=$(wc -l < /proc/modules 2>/dev/null)
[6s] step: nach mount: configfs=$(grep -c " type configfs " /proc/mounts) ordner=$([ -d "$CONFIGFS" ] && echo ja || echo nein) udc=$(ls /sys/class/udc 2>/dev/null | xargs)
[6s] step: udc-lesung 1: uptime 6.02s, inhalt: a600000.usb 
[6s] step: udc nach 0 runden gefunden: a600000.usb, uptime 6.05s
[6s] step: network function: ncm.usb0
[6s] step: binding UDC a600000.usb
[6s] step: UDC steht auf: a600000.usb
[6s] step: ifconfig usb0 172.16.42.1
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
[7s] step: schreib_rc=0 8+0 records in 8+0 records out 1048576 bytes (1.0MB) copied, 0.011441  platte=/dev/sda ro_achter=1
[26s] step:  | g1 war da: g1  | gebunden=a600000.usb | connect rc=0 text=ohne pfad=/sys/class/udc/a600000.usb/soft_connect state=configured netz=lo sit0 usb0 
[46s] step:  | g1 war da: g1  | gebunden=a600000.usb | connect rc=0 text=ohne pfad=/sys/class/udc/a600000.usb/soft_connect state=configured netz=lo sit0 usb0  | g1 war da: g1  | gebunden=a600000.usb | connect rc=0 text=ohne pfad=/sys/class/udc/a600000.usb/soft_connect state=configured netz=lo sit0 usb0 
[47s] step: dmesg gesichert: /run/dmesg-12s.txt /run/dmesg-2s.txt /run/dmesg-42s.txt 
~ # [6n
20:14:02 ### cat /run/steps.log | grep -c nonexistent
20:14:02 cat /run/steps.log | grep -c nonexistent
0
~ # [6n
20:14:06 ### ls /sys/fs/pstore
20:14:06 ls /sys/fs/pstore
[0;0mconsole-ramoops-0[m  [0;0mdmesg-ramoops-0[m
~ # [6n
20:14:06 === Lesung der eigenen Shell fertig ===
