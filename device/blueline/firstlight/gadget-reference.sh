1|mark 'usb gadget setup (reference sequence)'
2|# Wortlaut aus postmarketos-initramfs root/init_functions.sh, nur dass die
3|# deviceinfo-Variablen durch ihre dortigen Defaultwerte ersetzt sind:
4|#   CONFIGFS=/sys/kernel/config/usb_gadget                          (Zeile 12)
5|#   usb_idVendor=0x18D1  usb_idProduct=0xD001                       (Zeile 843)
6|#   usb_network_function=ncm.usb0, Fallback rndis.usb0              (Zeile 846)
7|#   HOST_IP=172.16.42.1                                              (Zeile 15)
8|# get_usb_udc() nimmt /sys/class/udc | head -1, setup_usb_configfs_udc()
9|# leert erst das UDC und schreibt dann den Controller.
10|CONFIGFS=/sys/kernel/config/usb_gadget
11|mkdir -p "$(dirname "$CONFIGFS")"
12|mount -t configfs -o nodev,noexec,nosuid configfs "$(dirname "$CONFIGFS")" 2>/dev/null
13|if ! [ -e "$CONFIGFS" ]; then
14|    mark 'usb_gadget not found in configfs, skipping gadget setup'
15|else
16|    udc=$(ls /sys/class/udc 2>/dev/null | head -1)
17|    if [ -z "$udc" ]; then
18|        mark 'No UDC found, skipping gadget setup'
19|    else
20|        mkdir "$CONFIGFS/g1" || mark 'g1 nicht angelegt'
21|        echo 0x18D1 > "$CONFIGFS/g1/idVendor"
22|        echo 0xD001 > "$CONFIGFS/g1/idProduct"
23|        mkdir "$CONFIGFS/g1/strings/0x409" || mark 'strings/0x409 nicht angelegt'
24|        echo 'Omarchy Mobile' > "$CONFIGFS/g1/strings/0x409/manufacturer"
25|        echo 'omamobile-blueline' > "$CONFIGFS/g1/strings/0x409/serialnumber"
26|        echo 'Pixel 3 (blueline)' > "$CONFIGFS/g1/strings/0x409/product"
27|        netfunc=ncm.usb0
28|        if ! mkdir "$CONFIGFS/g1/functions/$netfunc"; then
29|            if mkdir "$CONFIGFS/g1/functions/rndis.usb0"; then
30|                netfunc=rndis.usb0
31|            fi
32|        fi
33|        mark "network function: $netfunc"
34|        mkdir "$CONFIGFS/g1/configs/c.1" || mark 'configs/c.1 nicht angelegt'
35|        mkdir "$CONFIGFS/g1/configs/c.1/strings/0x409"
36|        echo 'USB network' > "$CONFIGFS/g1/configs/c.1/strings/0x409/configuration"
37|        ln -s "$CONFIGFS/g1/functions/$netfunc" "$CONFIGFS/g1/configs/c.1" || mark 'ncm verlinkt nicht'
38|        # setup_usb_acm_configfs(): die serielle Konsole daneben. In der
39|        # Referenz leert das den UDC; hier wird der UDC ohnehin erst danach
40|        # gesetzt, also Funktion und Link - dieselbe Reihenfolge wie in der
41|        # Log-Recovery (netzwerk mit skip_udc, dann acm, dann ein UDC-Write).
42|        mkdir "$CONFIGFS/g1/functions/acm.GS0" || mark 'acm.GS0 nicht angelegt'
43|        ln -s "$CONFIGFS/g1/functions/acm.GS0" "$CONFIGFS/g1/configs/c.1" || mark 'acm verlinkt nicht'
44|        # setup_usb_configfs_udc(): erst leeren (Resource busy), dann binden.
45|        if [ -e "$CONFIGFS/g1/UDC" ] && [ "$(wc -w < "$CONFIGFS/g1/UDC")" -gt 0 ]; then
46|            echo "" > "$CONFIGFS/g1/UDC" || mark 'UDC leeren fehlgeschlagen'
47|        fi
48|        mark "binding UDC $udc"
49|        echo "$udc" > "$CONFIGFS/g1/UDC" || mark 'UDC binden fehlgeschlagen'
50|        mark "UDC steht auf: $(cat "$CONFIGFS/g1/UDC" 2>/dev/null)"
51|        # HOST_IP der Referenz. Ohne unudhcpd im Ramdisk bekommt der Host keine
52|        # Adresse, aber das NCM-Interface und die ACM-Konsole erscheinen - das
53|        # ist M1, die Adresse am Host setzen wir draussen.
54|        for iface in usb0 eth0 ncm0; do
55|            ifconfig "$iface" 172.16.42.1 2>/dev/null && mark "ifconfig $iface 172.16.42.1"
56|        done
57|    fi
58|fi