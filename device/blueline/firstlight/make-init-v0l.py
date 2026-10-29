#!/usr/bin/env python3
"""v0l-Init aus dem v0h-Init: Claude-Checkin 2026-10-29 Punkt 1+2.

Der Statusblock muss einem einzelnen Foto den vollen USB-Stand liefern —
denn dass `reboot bootloader` geehrt wird, ist UNBELEGT (v0as 78 s waren
der VFS-Panic mit panic=10; v0ks Sonde feuerte, ohne je in Fastboot
zurueckzukehren). Also zeigt das Panel jetzt: Uptime, PID/Status von init,
UDC-Klasse und configfs-Bindung, dwc3-Rolle und Typec, Watchdog, letzten
Schritt. Ausserdem sitzt der Gadget-Baum wie in der Distro-Referenz unter
/sys/kernel/config/usb_gadget/g1 (setup_usb_network_configfs, 1:1)."""
import sys

src = open(sys.argv[1]).read()

def sub(old, new):
    global src
    assert src.count(old) == 1, f"Anker genau einmal erwartet: {old[:60]!r} ({src.count(old)}x)"
    src = src.replace(old, new)

sub("mkdir -p /dev/pts /sys/fs/pstore /config",
    "mkdir -p /dev/pts /sys/fs/pstore /sys/kernel/config")
sub("mount -t configfs configfs /config || mark 'mount configfs FAILED'",
    "mount -t configfs configfs /sys/kernel/config || mark 'mount configfs FAILED'")
sub("g=/config/usb_gadget/omamobile",
    "# Lage und Name wie setup_usb_network_configfs der Distro-Referenz\n"
    "g=/sys/kernel/config/usb_gadget/g1")
sub('echo 0x1d6b > "$g/idVendor" 2>/dev/null\necho 0x0104 > "$g/idProduct" 2>/dev/null',
    'echo 0x18D1 > "$g/idVendor" 2>/dev/null\necho 0xD001 > "$g/idProduct" 2>/dev/null')

old_block = '''            { echo "--- ${up}s ---"
              echo "wdt bootstatus=$(cat /sys/class/watchdog/*/bootstatus 2>/dev/null) timeout=$(cat /sys/class/watchdog/*/timeout 2>/dev/null)"
              echo "udc=$(ls /sys/class/udc 2>/dev/null) gebunden=$(cat /config/usb_gadget/*/UDC 2>/dev/null)"
              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"
            } > /dev/console 2>/dev/null'''
new_block = '''            { echo "--- ${up}s ---"
              echo "init: comm=$(cat /proc/1/comm 2>/dev/null) state=$(cut -d' ' -f3 /proc/1/stat 2>/dev/null) kinder=$(ls /proc | grep -cE '^[0-9]+$')"
              echo "udc=$(ls /sys/class/udc 2>/dev/null) gebunden=$(cat /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null)"
              echo "dwc3: $(for d in /sys/bus/platform/devices/*dwc3*; do [ -e "$d" ] || continue; echo -n "${d##*/} rolle=$(cat "$d/role" 2>/dev/null) modus=$(cat "$d/mode" 2>/dev/null) "; done)"
              echo "typec: $(for c in /sys/class/typec/*; do [ -e "$c" ] || continue; echo -n "${c##*/}=$(cat "$c"/*_state 2>/dev/null | tr \\\\n'/' ) "; done) vbus=$(cat /sys/class/power_supply/usb/online 2>/dev/null)"
              echo "wdt bootstatus=$(cat /sys/class/watchdog/*/bootstatus 2>/dev/null) timeout=$(cat /sys/class/watchdog/*/timeout 2>/dev/null)"
              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"
            } > /dev/console 2>/dev/null'''
sub(old_block, new_block)

old_bind = '''if [ -n "$udc" ]; then
    mark "binding UDC $udc"
    echo "$udc" > "$g/UDC" 2>/dev/null && mark 'UDC bound' || mark 'UDC bind FAILED\''''
new_bind = '''if [ -n "$udc" ]; then
    mark "binding UDC $udc"
    # setup_usb_configfs_udc der Referenz: gebundene UDC erst leeren, sonst
    # write error: Resource busy beim erneuten Binden
    [ "$(wc -w < "$g/UDC" 2>/dev/null)" ] && [ "$(wc -w < "$g/UDC" 2>/dev/null)" -gt 0 ] && \\
        echo "" > "$g/UDC" 2>/dev/null
    echo "$udc" > "$g/UDC" 2>/dev/null && mark 'UDC bound' || mark 'UDC bind FAILED\''''
sub(old_bind, new_bind)

open(sys.argv[2], "w").write(src)
print(f"init v0l geschrieben: {len(src)} Bytes (vorher {len(open(sys.argv[1]).read())})")
