mark 'usb gadget setup (reference sequence)'
# Wortlaut aus postmarketos-initramfs root/init_functions.sh, nur dass die
# deviceinfo-Variablen durch ihre dortigen Defaultwerte ersetzt sind:
#   CONFIGFS=/sys/kernel/config/usb_gadget                          (Zeile 12)
#   usb_idVendor=0x18D1  usb_idProduct=0xD001                       (Zeile 843)
#   usb_network_function=ncm.usb0, Fallback rndis.usb0              (Zeile 846)
#   HOST_IP=172.16.42.1                                              (Zeile 15)
# get_usb_udc() nimmt /sys/class/udc | head -1, setup_usb_configfs_udc()
# leert erst das UDC und schreibt dann den Controller.
CONFIGFS=/sys/kernel/config/usb_gadget
mkdir -p "$(dirname "$CONFIGFS")"
mount -t configfs -o nodev,noexec,nosuid configfs "$(dirname "$CONFIGFS")" 2>/dev/null
if ! [ -e "$CONFIGFS" ]; then
    mark 'usb_gadget not found in configfs, skipping gadget setup'
else
    udc=$(ls /sys/class/udc 2>/dev/null | head -1)
    if [ -z "$udc" ]; then
        mark 'No UDC found, skipping gadget setup'
    else
        mkdir "$CONFIGFS/g1" || mark 'g1 nicht angelegt'
        echo 0x18D1 > "$CONFIGFS/g1/idVendor"
        echo 0xD001 > "$CONFIGFS/g1/idProduct"
        mkdir "$CONFIGFS/g1/strings/0x409" || mark 'strings/0x409 nicht angelegt'
        echo 'Omarchy Mobile' > "$CONFIGFS/g1/strings/0x409/manufacturer"
        echo 'omamobile-blueline' > "$CONFIGFS/g1/strings/0x409/serialnumber"
        echo 'Pixel 3 (blueline)' > "$CONFIGFS/g1/strings/0x409/product"
        netfunc=ncm.usb0
        if ! mkdir "$CONFIGFS/g1/functions/$netfunc"; then
            if mkdir "$CONFIGFS/g1/functions/rndis.usb0"; then
                netfunc=rndis.usb0
            fi
        fi
        mark "network function: $netfunc"
        mkdir "$CONFIGFS/g1/configs/c.1" || mark 'configs/c.1 nicht angelegt'
        mkdir "$CONFIGFS/g1/configs/c.1/strings/0x409"
        echo 'USB network' > "$CONFIGFS/g1/configs/c.1/strings/0x409/configuration"
        ln -s "$CONFIGFS/g1/functions/$netfunc" "$CONFIGFS/g1/configs/c.1" || mark 'ncm verlinkt nicht'
        # setup_usb_acm_configfs(): die serielle Konsole daneben. In der
        # Referenz leert das den UDC; hier wird der UDC ohnehin erst danach
        # gesetzt, also Funktion und Link - dieselbe Reihenfolge wie in der
        # Log-Recovery (netzwerk mit skip_udc, dann acm, dann ein UDC-Write).
        mkdir "$CONFIGFS/g1/functions/acm.GS0" || mark 'acm.GS0 nicht angelegt'
        ln -s "$CONFIGFS/g1/functions/acm.GS0" "$CONFIGFS/g1/configs/c.1" || mark 'acm verlinkt nicht'
        # setup_usb_configfs_udc(): erst leeren (Resource busy), dann binden.
        if [ -e "$CONFIGFS/g1/UDC" ] && [ "$(wc -w < "$CONFIGFS/g1/UDC")" -gt 0 ]; then
            echo "" > "$CONFIGFS/g1/UDC" || mark 'UDC leeren fehlgeschlagen'
        fi
        mark "binding UDC $udc"
        echo "$udc" > "$CONFIGFS/g1/UDC" || mark 'UDC binden fehlgeschlagen'
        mark "UDC steht auf: $(cat "$CONFIGFS/g1/UDC" 2>/dev/null)"
        # HOST_IP der Referenz. Ohne unudhcpd im Ramdisk bekommt der Host keine
        # Adresse, aber das NCM-Interface und die ACM-Konsole erscheinen - das
        # ist M1, die Adresse am Host setzen wir draussen.
        for iface in usb0 eth0 ncm0; do
            ifconfig "$iface" 172.16.42.1 2>/dev/null && mark "ifconfig $iface 172.16.42.1"
        done
    fi
fi