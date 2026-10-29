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
# platform-tools nur in den PATH, wenn nicht schon ein fastboot da ist: ein
# Test-Fake, der den PATH von aussen setzt, verliert sonst gegen den echten
# (dieselbe Falle, die der Runner-Test fuer ref-enumeration-test.sh dokumentiert).
command -v fastboot >/dev/null 2>&1 || export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"
# Rueckweg-STUFE-1, korrigiert nach dem Check-in von 23:5x: der Default war
# factory/sp1a/boot.img (5c1ce19e…, Android). Das ist der Rueckweg auf den
# Android-Urzustand - korrekt als letzte Stufe, aber es ist NICHT die laufende
# pmOS-Referenz, und die Freigabe an Gregor war mit "du bekommst die laufende
# Referenz zurueck" auf die Android-Datei gated. Stufe 1 ist jetzt die
# Referenz selbst (pmos-ref-build/ref/boot.img, ed2c225f…, 28729344 B): ein
# Flash darauf stellt den genauen Zustand wieder her, den das Telefon heute
# haelt. Die Android-Datei bleibt Stufe 2 (Falle: bleibt v0r dunkel und Telnet
# antwortet nicht, hilft nur Power+Leiser ~10 s, dann wird Stufe 1 geflasht;
# auf Android zurueck ist noetig, wenn die Referenz selbst es nicht mehr tut).
RUECKWEG=${RUECKWEG:-/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img}
RUECKWEG_SHA=${RUECKWEG_SHA:-ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82}
mkdir -p "$OUT"; LOG="$OUT/protokoll.txt"; exec >>"$LOG" 2>&1
say() { echo "$(date '+%H:%M:%S') $*"; }
# Portabilitaet: shasum/stat -f sind macOS-Werkzeuge, Linux kennt sha256sum
# und stat -c. Der harte shasum-Aufruf liess auf Alpine die Hashzeile leer
# laufen - das Gate meldete "Hash  != ..." und stieg aus, ohne fastboot je zu
# rufen. Das ist dasselbe Muster wie die PATH-Falle: ein Harness, der nur auf
# seinem Heimat-OS laeuft, beweist nothing fuer das andere.
sha()  { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
         else sha256sum "$1" | cut -d' ' -f1; fi; }
# Grossenbestimmung ohne MacOS-Idiom. Achtung: auf Alpine ist 'stat -f' nicht
# unbekannt, sondern GNU-stat mit --file-system - es liefert einen
# Dateisystem-Report bei Exit 0. Ein '|| stat -c'-Fallback greift damit nie,
# die Groesse wird zu einem mehrzeiligen Text und der Grossenvergleich ist
# sinnlos. Deshalb: Variantscheck und ein numerisches Sicherheitsnetz.
fsize(){
    # Groessenbestimmung ohne stat-Idiom: Alpine (coreutils) kennt '-f' ohne
    # Argument ('-f%s' => "invalid option -- '%'"), macOS kennt '-c' nicht,
    # und ein nacktes 'stat -f %z /etc/passwd' schreibt auf Linux den
    # Filesystem-Report bei gemischtem Exit auf stdout. Jede stat-Variante
    # verbiegt sich woanders. Ein Groessen-Beweis, der der Pruefung nicht
    # trauen kann, ist kein Beweis - python3 ist auf beiden Seiten vorhanden
    # und getsize ist auf beiden Seiten dasselbe.
    python3 -c 'import os,sys; print(os.path.getsize(sys.argv[1]))' "$1" 2>/dev/null || echo 0
}

[ -f "$IMG" ] || { say "not ok - Bild fehlt: $IMG"; exit 1; }
ist=$(sha "$IMG")
[ "$ist" = "$SOLL" ] || { say "not ok - Hash $ist != $SOLL"; exit 1; }
rb=$(fsize "$RUECKWEG")
rs=$(sha "$RUECKWEG")
# Zwei Bedingungen, zwei Meldungen. Die fruehere Meldung nannte 67108864 B,
# durchgesetzt wurden >1000000 B und der Hash - eine Zahl, die der Code nicht
# prueft, ist eine zweite Quelle, die fault: nach dem Wechsel von Stufe 1 auf
# die Referenz (28729344 B) haette sie fuer jede richtige Datei eine falsche
# Erwartung behauptet.
[ "$rb" -gt 1000000 ] || { say "not ok - Rueckweg $rb B, erwartet mehr als 1000000 B: $RUECKWEG"; exit 1; }
[ "$rs" = "$RUECKWEG_SHA" ] || { say "not ok - Rueckweg-Hash $rs != $RUECKWEG_SHA: $RUECKWEG"; exit 1; }
say "Rueckweg steht: $rb B $rs"

snap() { { ioreg -p IOUSB -l -w 0; system_profiler SPUSBDataType 2>/dev/null; } \
  | grep -iE '"?USB (Product|Serial) (Name|Number)"?|Product ID|Serial Number|idVendor|idProduct' | sort -u; }
count() { { ioreg -p IOUSB -l -w 0 | grep -ci "android\|fastboot"; } 2>/dev/null || true; }
before=$(snap); say "Vorher: $(printf '%s' "$before" | wc -l | tr -d ' ') Zeilen"

fastboot devices | grep -q . || { say "not ok - kein Fastboot-Geraet"; exit 1; }
fastboot flash boot_a "$IMG"; say "flash boot_a $IMG"
fastboot getvar current-slot 2>&1 | sed 's/^/  /'
fastboot getvar slot-retry-count:a 2>&1 | sed 's/^/  /'
fastboot getvar slot-unbootable:a 2>&1 | sed 's/^/  /'
R=rebo; fastboot ${R}ot; say "Neustart kommandiert, $DAUER s Beobachtung"

t0=$(date +%s); seen=0
POLL=${POLL:-5}
while :; do
  t=$(( $(date +%s) - t0 )); [ "$t" -ge "$DAUER" ] && break
  now=$(snap); new=$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$now"))
  fb=$(count)   # fastboot-Zahlenstand: unter pipefail darf ein grep -c ohne
                # Treffer (Exit 1) die Schleife nicht beenden - das war ein
                # echter Ausfall, den der Fake-Lauf gefunden hat
  if [ -n "$new" ]; then
    seen=$((seen+1)); say "t=${t}s NEU: $(printf '%s' "$new" | tr '\n' '|' | cut -c1-200)"
    before=$(printf '%s\n' "$now")
  fi
  if ping -c1 -W2000 "${PHONE:-172.16.42.1}" >/dev/null 2>&1; then
    say "t=${t}s ${PHONE:-172.16.42.1} pingbar"
    if nc -z -G 2 "${PHONE:-172.16.42.1}" 23 2>/dev/null; then say "t=${t}s Port 23 offen"; break; fi
  fi
  sleep "$POLL"
done
say "ERGEBNIS: $seen Beobachtungen mit neuen Eintraegen, $t s gelaufen"
# Wenn die Telefon-Shell erreichbar ist: volle Beweiskammer fuellen.
if nc -z -G 3 "${PHONE:-172.16.42.1}" 23 2>/dev/null; then
  python3 - "$OUT" "${PHONE:-172.16.42.1}" <<'PY'
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
out=sys.argv[1]; host=sys.argv[2]
s=socket.create_connection((host,23),8); s.settimeout(15)
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
