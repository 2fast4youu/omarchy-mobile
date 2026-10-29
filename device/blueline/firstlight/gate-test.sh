#!/bin/bash
# Ad-hoc-Gegentest des Freigabe-Gate in firstlight/run.sh, OHNE Telefon:
# ein fake fastboot liefert einmal ein Geraet und danach keins mehr, HOME zeigt
# in einen leeren Kasten. Scenario A: keine Freigabe-Datei -> Exit 3, kein
# --set-active. Scenario B: Freigabe nach 10 s -> set-active laeuft, danach
# Abbruch mit "kein NCM" (hier: ein ACM-Knoten erscheint, Weg 2).
# Schnelle Zeitmassstaebe nur fuer diesen Test (sleep 5 -> 1, 180 -> 8, 40 -> 4).
# Lauf: RUN_SH=/pfad/zu/run.sh bash gate-test.sh   (braucht firstlight.img daneben)
set -uo pipefail
V=$(mktemp -d "${TMPDIR:-/private/var/folders/mw/b3m3hvy12pb95lt_56zdq6rh0000gn/T}/hermes-gate-XXXXXX")
trap 'rm -rf "$V"' EXIT
SRC="${RUN_SH:-/private/tmp/fl-v0q/run.sh}"

mk_case() {  # $1 = Zielordner
  mkdir -p "$1/home" "$1/mockbin"
  cp "$(dirname "$SRC")/firstlight.img" "$1/firstlight.img"
  sed -e "s#/private/tmp/fl-v0q#$1#g" -e 's#/dev/cu\.usb#$1/dev/cu.usb#g' \
      -e 's/sleep 5/sleep 1/g' \
      -e 's/seq 1 180/seq 1 8/g' -e 's/seq 1 40/seq 1 4/g' \
      -e 's/sleep 15/sleep 3/g' "$SRC" > "$1/run.sh"
  # fake fastboot: ein Geraet, das nach dem 2. Aufruf verschwindet (Scenario A)
  # bzw. bleiben darf (Scenario B, gesteuert ueber die Datei $1/mockbin/stay)
  cat > "$1/mockbin/fastboot" <<'FB'
#!/bin/bash
d=$(dirname "$0")
case "$1" in
  devices) [ -e "$d/stay" ] && echo "PIXEL3-SERIAL  fastboot"; exit 0;;
  getvar)  echo "$2: v0qmock"; echo "finished. total time: 0.001s"; exit 0;;
  flash)   echo "OKAY [ 0.001s]"; echo "finished. total time: 0.002s"; exit 0;;
  --set-active=a) echo "setting active slot to slot a...OKAY"; echo "finished. total time: 0.001s";
                  echo gesetzt >> "$d/auktion"; exit 0;;
  reboot)  echo rebooted >> "$d/auktion"; exit 0;;
  *) exit 0;;
esac
FB
  chmod +x "$1/mockbin/fastboot"
}

echo "== Scenario A: keine Freigabe-Datei =="
mk_case "$V/A"
( cd "$V" && HOME="$V/A/home" PATH="$V/A/mockbin:$PATH" bash "$V/A/run.sh" > "$V/A/out.txt" 2>&1; echo "EXIT=$?" > "$V/A/exit" ) &
pid=$!
sleep 6
if grep -q "set-active" "$V/A/out.txt"; then echo "FAIL: set-active vor Freigabe gelaufen"; else echo "ok  kein set-active, solange die Freigabe fehlt"; fi
echo "  bisher: $(grep -c 'geflasht' "$V/A/out.txt") flash-Meldung, Kanal-Zeilen: $(wc -l < "$V/A/kanal.txt" | tr -d ' ')"
touch "$V/A/mockbin/stay"   # Gerat bleibt am Bus, damit A bis zum Timeout wartet
wait $pid
echo "  $(cat "$V/A/exit")  $(grep 'ERGEBNIS' "$V/A/out.txt" | tail -1)"
grep -q "EXIT=3" "$V/A/exit" && grep -q "keine Freigabe" "$V/A/out.txt" \
  && echo "ok  A endet mit Exit 3 und 'keine Freigabe'" || echo "FAIL: A endet nicht wie erwartet"
[ -e "$V/A/mockbin/auktion" ] && echo "FAIL: A hat Slot gesetzt oder neu gestartet" || echo "ok  A hat weder Slot gesetzt noch neu gestartet"

echo "== Scenario B: Freigabe nach 10 s, ACM-Knoten taucht auf =="
mk_case "$V/B"
( cd "$V" && HOME="$V/B/home" PATH="$V/B/mockbin:$PATH" bash "$V/B/run.sh" > "$V/B/out.txt" 2>&1; echo "EXIT=$?" > "$V/B/exit" ) &
pid=$!
sleep 4
if grep -q "set-active" "$V/B/out.txt"; then echo "FAIL: zu frueh gesetzt"; else echo "ok  wartet"; fi
mkdir -p "$V/B/dev"; : > "$V/B/dev/cu.usbmodem101"
touch "$V/B/mockbin/stay"
touch "$V/B/home/ok-set-active"
wait $pid
echo "  $(cat "$V/B/exit")"
echo "  Aktionen in Mock-Reihenfolge: $(tr '\n' ' ' < "$V/B/mockbin/auktion" 2>/dev/null || echo keine)"
echo "  $(grep 'ERGEBNIS' "$V/B/out.txt" | tail -1)"
grep -q "gesetzt" "$V/B/mockbin/auktion" 2>/dev/null && grep -q "rebooted" "$V/B/mockbin/auktion" \
  && echo "ok  B setzt Slot und startet neu, nachdem die Freigabe erscheint" || echo "FAIL: B hat nicht reagiert"
grep -q "SERIELLE KONSOLE" "$V/B/out.txt" && echo "ok  B meldet ACM-Zweig" || echo "Hinweis: B endet im 600s-Zweig (kurze Zeit)"
rm -rf "$V/B/dev"
