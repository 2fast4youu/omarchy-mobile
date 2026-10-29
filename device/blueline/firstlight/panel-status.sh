              echo "udc=$(ls /sys/class/udc 2>/dev/null) gebunden=$(cat /sys/kernel/config/usb_gadget/*/UDC 2>/dev/null)"
              echo "dwc3 rolle=$(cat /sys/class/typec/*/data_role 2>/dev/null) typec=$(ls /sys/class/typec 2>/dev/null) vbus=$(cat /sys/class/power_supply/usb/online 2>/dev/null)"
              echo "pid1=$(cat /proc/1/comm 2>/dev/null) state=$(cut -d" " -f3 /proc/1/stat 2>/dev/null) kinder=$(ls /proc/1/task/1/children 2>/dev/null | wc -w)"
              echo "letzter Schritt: $(tail -1 /run/steps.log 2>/dev/null)"
