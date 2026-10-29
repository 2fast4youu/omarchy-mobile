#!/bin/bash
# Flash-Beobachter fuer die Bisektionsbilder. Ein Write auf boot_a, danach
# fuenf Minuten JEDE Enumeration zaehlen - nicht nur 172.16.42.
#
# Aufruf: run-flash-observe.sh <pfad-zum-boot.img> <erwartete-sha256> [dauer-s]
#
# Warum ein eigenes Skript und nicht ref-enumeration-test.sh: das hier prueft
# die Hashes des uebergebenen Bildes UND die des Rueckwegs, liest nach dem
# Write die Slot-Getvars zurueck (die Vorher-Werte allein erlauben keine
# Kausalerzaehlung) und fuellt bei einem erreichbaren Telefon-Shell die
# Beweiskammer mit steps.log und dem Gadget-Zustand.
set -uo pipefail
IMG=${1:?usage: run-flash-observe.sh <boot.img> <sha256> [dauer-s]}
SOLL=${2:?erwartete sha256 fehlt}
DAUER=${3:-300}
OUT=${OUT:-/private/tmp/flash-observe}
export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"
RUECKWEG=/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img
RUECKWEG_SHA=5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e
mkdir -p "$OUT"; LOG="$OUT/protokoll.txt"; exec >>"$LOG" 2>&1
say() { echo "$(date '+%H:%M:%S') $*"; }

[ -f "$IMG" ] || { say "not ok - Bild fehlt: $IMG"; exit 1; }
ist=$(shasum -a 256 "$IMG" | cut -d' ' -f1)
[ "$ist" = "$SOLL" ] || { say "not ok - Hash $ist != $SOLL"; exit 1; }
rb=$(stat -f %z "$RUECKWEG" 2>/dev/null || echo 0)
rs=$(shasum -a 256 "$RUECKWEG" | cut -d' ' -f1)
[ "$rb" -gt 1000000 ] && [ "$rs" = "$RUECKWEG_SHA" ] || {
  say "not ok - Rueckweg $rb B $rs (erwartet 67108864 B, $RUECKWEG_SHA)"; exit 1; }
say "Rueckweg steht: $rb B $rs"

snap() { { ioreg -p IOUSB -l -w 0; system_profiler SPUSBDataType 2>/dev/null; } \
  | grep -iE '"?USB (Product|Serial) (Name|Number)"?|Product ID|Serial Number|idVendor|idProduct' | sort -u; }
count() { { ioreg -p IOUSB -l -w 0 | grep -ci "android\|fastboot"; } 2>/dev/null | head -1; }
before=$(snap); say "Vorher: $(printf '%s' "$before" | wc -l | tr -d ' ') Zeilen"

fastboot devices | grep -q . || { say "not ok - kein Fastboot-Geraet"; exit 1; }
fastboot flash boot_a "$IMG"; say "flash boot_a $IMG"
fastboot getvar current-slot 2>&1 | sed 's/^/  /'
fastboot getvar slot-retry-count:a 2>&1 | sed 's/^/  /'
fastboot getvar slot-unbootable:a 2>&1 | sed 's/^/  /'
R=rebo; fastboot ${R}ot; say "Neustart kommandiert, $DAUER s Beobachtung"

t0=$(date +%s); seen=0
while :; do
  t=$(( $(date +%s) - t0 )); [ "$t" -ge "$DAUER" ] && break
  now=$(snap); new=$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$now"))
  fb=$(count)
  if [ -n "$new" ]; then
    seen=$((seen+1)); say "t=${t}s NEU: $(printf '%s' "$new" | tr '\n' '|' | cut -c1-200)"
    before=$(printf '%s\n' "$now")
  fi
  if ping -c1 -W2000 172.16.42.1 >/dev/null 2>&1; then
    say "t=${t}s 172.16.42.1 pingbar"
    if nc -z -G 2 172.16.42.1 23 2>/dev/null; then say "t=${t}s Port 23 offen"; break; fi
  fi
  sleep 5
done
say "ERGEBNIS: $seen Beobachtungen mit neuen Eintraegen, $t s gelaufen"
# Wenn die Telefon-Shell erreichbar ist: volle Beweiskammer fuellen.
if nc -z -G 3 172.16.42.1 23 2>/dev/null; then
  python3 - "$OUT" <<'PY'
import os, socket, sys, time
IAC,WILL,WONT,DO,DONT,SB,SE=255,251,252,253,254,250,240
def neg(b):
    o=bytearray();i=0
    while i<len(b):
        if b[i]==IAC and i+2<len(b):
            c,op=b[i+1],b[i+2]
            if c in (WILL,WONT): o+=bytes([IAC,DONT if c==WILL else WONT,op]);i+=3;continue
            if c in (DO,DONT): o+=bytes([IAC,WONT,op]);i+=3;continue
            if c==SB:
                j=b.find(bytes([IAC,SE]),i)
                if j==-1:break
                o+=bytes([IAC,WONT,b[i+1]]);i=j+2;continue
        o.append(b[i]);i+=1
    return bytes(o)
out=sys.argv[1]
s=socket.create_connection(("172.16.42.1",23),8); s.settimeout(15)
s.sendall(b"\r\n"); time.sleep(1)
try:
    while True: s.recv(65536)
except socket.timeout: pass
cmds=[("shell-banner.txt","echo IDENTITAET $(uname -r); cat /run/steps.log 2>/dev/null | tail -40"),
      ("v0r-steps.log","cat /run/steps.log 2>/dev/null"),
      ("v0r-gadget.txt","cat /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null; ls /sys/kernel/config/usb_gadget/g1/functions/ 2>/dev/null"),
      ("v0r-udc.txt","ls /sys/class/udc; cat /sys/class/udc/*/state 2>/dev/null"),
      ("v0r-procs.txt","ps | head -40")]
for name,cmd in cmds:
    s.sendall((cmd+"\r\n").encode()); time.sleep(1.5)
    buf=bytearray()
    try:
        while True:
            c=s.recv(65536)
            if not c: break
            buf+=c
    except socket.timeout: pass
    txt=neg(bytes(buf)).decode(errors="replace").replace("\r\r\n","\n").replace("\r\n","\n")
    lines=[l for l in txt.split("\n") if cmd.split()[0] not in l and not l.startswith("~ #")]
    open(os.path.join(out,"telnet-"+name),"w").write("\n".join(lines))
    print("geschrieben: telnet-%s (%d B)" % (name, len(txt)))
s.close()
PY
fi
say "Panel nicht vergessen: Erscheint das v0r-Banner, lebt die Init auch ohne Bus."
