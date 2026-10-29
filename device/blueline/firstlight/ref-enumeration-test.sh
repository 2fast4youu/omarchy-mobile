#!/usr/bin/env bash
# Referenz-Enumerations-Test: boot_a mit dem unveraenderten Distro-boot.img fuellen
# und 5 min lang JEDE USB-Enumeration am Mac zaehlen, nicht nur 172.16.42.1.
#
# Warum: die Referenz wurde am Bus nie gemessen (ERGEBNIS-REF.txt: "kein boot.img
# in /work/export gefunden" - der Flasher stieg vor seiner Schleife aus). Wenn sie
# hier in vollem Modus enumeriert, liegt der Unterschied an v0q; wenn sie nie
# erscheint, liegt es an Host/Kabel/macOS und jede Gadget-Arbeit ist umsonst.
#
# Schreibscope: boot_a (ein Write). Vorher sha256 + Groesse der Datei pruefen, und
# der Rueckweg factory/sp1a/boot.img muss existieren und passen.
set -u
export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"
REF="/Users/gregor/hermes-workspace/pmos-ref-build/ref/boot.img"
REF_SHA="ed2c225f79ad6e5ad2dc8a7ac8582fdfdeadddfd76805fdeddd0b75311f76f82"
FACTORY="/Users/gregor/hermes-workspace/android-mainline/factory/sp1a/boot.img"
FAC_SHA="5c1ce19e814e2f198baa877a7351306079272fe67e13404e31f3bab213bb506e"
OUT="${1:-/private/tmp/ref-enum}"
DAUER="${2:-300}"
mkdir -p "$OUT"
K="$OUT/enum.log"

usbliste() {
  ioreg -p IOUSB -l -w 0 2>/dev/null \
    | sed -n 's/.*"USB Product Name" = "\(.*\)"/\1/p; s/.*"USB Vendor Name" = "\(.*\)"/[V] \1/p; s/.*"idVendor" = \([0-9]*\).*/[id] \1/p' \
    | sort | uniq -c | awk '{$1=""; sub(/^ /,""); print}'
  system_profiler SPUSBDataType 2>/dev/null | sed -n 's/^ *\(Product ID\|Vendor ID\|Serial Number\|.*Speed\): */\1: /p' | sort | uniq -c \
    | awk '{$1=""; sub(/^ /,""); print}'
}

say() { echo "$(date +%H:%M:%S) $*" | tee -a "$K"; }

# 1) Rueckweg und Referenz vor jedem Write nachmessen (Eigengewicht, nicht Notiz)
[ -f "$FACTORY" ] || { say "ABBRUCH: Rueckweg fehlt: $FACTORY"; exit 1; }
fs=$(shasum -a 256 "$FACTORY" | cut -d' ' -f1)
[ "$fs" = "$FAC_SHA" ] || { say "ABBRUCH: Rueckweg-sha256 weicht ab: $fs"; exit 1; }
say "Rueckweg ok: factory/sp1a/boot.img 67108864 B sha256 $fs"
rs=$(shasum -a 256 "$REF" | cut -d' ' -f1)
[ "$rs" = "$REF_SHA" ] || { say "ABBRUCH: Referenz-sha256 weicht ab: $rs"; exit 1; }
say "Referenz ok: $REF $(stat -f %z "$REF") B sha256 $rs"

# 2) Vorher-Snapshot des Busses (nach Grundlinie, vor dem Write)
sleep 5; usbliste > "$OUT/usb-vorher.txt" 2>&1
say "Vorher-Snapshot: $(wc -l < "$OUT/usb-vorher.txt" | tr -d ' ') Zeilen"

# 3) Auf Fastboot warten
say "warte auf Telefon in Fastboot ..."
while [ -z "$(fastboot devices 2>/dev/null | grep fastboot)" ]; do sleep 3; done
say "Telefon in Fastboot: $(fastboot devices 2>/dev/null | head -1)"
fastboot getvar current-slot 2>&1 | grep -v '^(bootloader)' | tee -a "$K"

# 4) Der einzige Write
say "flash boot_a (Referenz) $(date +%H:%M:%S)"
fastboot flash boot_a "$REF" 2>&1 | tail -2 | tee -a "$K"
fastboot reboot >/dev/null 2>&1
T0=$(date +%s)
NEU=0
for i in $(seq 1 $((DAUER / 5))); do
  sleep 5; t=$(( $(date +%s) - T0 ))
  usbliste > "$OUT/usb-${t}s.txt" 2>&1
  d=$(diff "$OUT/usb-vorher.txt" "$OUT/usb-${t}s.txt" 2>/dev/null | grep -c '^>')
  fbn=$(fastboot devices 2>/dev/null | grep -c fastboot)
  ncm=$(ifconfig -a 2>/dev/null | grep -c 172.16.42)
  ser=$(ls /dev/cu.usb* 2>/dev/null | wc -l | tr -d ' ')
  if [ "$d" != "0" ]; then
    say "t=${t}s NEUE USB-EINTRAEGE: $d (fastboot=$fbn ncm=$ncm seriell=$ser)"
    diff "$OUT/usb-vorher.txt" "$OUT/usb-${t}s.txt" | grep '^>' | sed 's/^> /   neu: /' | tee -a "$K"
    NEU=$((NEU+1))
  else
    [ $((t % 60)) -eq 0 ] && say "t=${t}s keine Veraenderung am Bus (fastboot=$fbn ncm=$ncm seriell=$ser)"
  fi
  [ "$ncm" != "0" ] && { say "ERGEBNIS: NCM-Interface bei ${t}s - Referenz zeigt das Gadget am Mac"; break; }
done

if [ "$NEU" = "0" ]; then
  say "ERGEBNIS: ${DAUER}s nach dem Referenz-Boot KEIN einziger neuer USB-Eintrag — Host/Kabel/macOS-Seite, nicht v0q"
else
  say "ERGEBNIS: Referenz enumeriert ($NEU Beobachtungen mit neuen Eintraegen) — Unterschied liegt an v0q"
fi
say "Panel nicht vergessen: pmOS-Login sichtbar = Referenz bootet (dann Telefon per Power+Leiser zurueck ins Fastboot-Menue)"
