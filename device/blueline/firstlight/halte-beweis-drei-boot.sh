#!/bin/sh
# Haelt die Wurzel? Drei kalte Neustarts, nichts wird neu geschrieben.
# boot_a traegt v0an (Platte bleibt offen, solange /ud haengt), userdata traegt
# die Wurzel e59b319b (Raeum-Aktion, Halteschleife, ehrliche Nachmessung).
# Gelesen wird ueber die Uebergabe-Shell; ihr Pfad ist anfangs leer, deshalb
# steht PATH in jeder Lesung dabei - sonst meldet sie 'cat: not found'.
set -u
FL=/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
KNOTE=/Users/gregor/.hermes/cache/scratch
LOG=$HOME/hermes-workspace/halte-drei-neustart-$(date +%H%M).log
# Hinweis: lies-halte.txt muss PATH mitfuehren, die Uebergabe-Shell kommt ohne Pfad.
KANAL=http://127.0.0.1:8081
CHAT=1335604113
TOKEN=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' "$HOME/.hermes/.env" | head -1)
melde() { curl -s -m 12 "$KANAL/bot$TOKEN/sendMessage" -d chat_id=$CHAT -d text="Omamobile: $1" >/dev/null 2>&1; }
say() { echo "$(date +%H:%M:%S) $*"; }
cat > $KNOTE/lies-halte.txt <<'EOM'
PATH=/usr/bin:/bin:/usr/sbin:/sbin; export PATH
echo @@UPTIME
cut -d. -f1 /proc/uptime
echo @@WURZEL
grep ' / ' /proc/mounts
echo @@NACH3S
cat /omamobile/LEBEN-nach3s 2>&1
echo @@STICHPROBEN
grep -o 'stichproben=[01]*' /omamobile/LEBEN-frueh 2>&1
echo @@PLATTENRO
printf 'platte=%s partition=%s' $(cat /sys/class/block/sda/ro) $(cat /sys/class/block/sda21/ro)
echo
echo @@ENDE
EOM
{
say "=== Halte-Beweis: drei kalte Neustarts, Start $(date -u +%FT%TZ)"
gehalten=0
for runde in 1 2 3; do
    # Telefon erreichen, dann selbst neu starten (erst uebers Fastboot, kalt)
    w=0
    while [ $w -lt 30 ]; do
        nc -z -G 3 172.16.42.1 23 2>/dev/null && break
        sleep 10; w=$((w + 1))
    done
    if [ $w -ge 30 ]; then say "Runde $runde: Telefon nicht erreichbar"; melde "Halte-Beweis: Telefon in Runde $runde nicht erreichbar"; break; fi
    # Nach drei Starts ohne Erfolgsmeldung ist der Zaehler leer und ABOOT
    # faellt auf Slot b zurueck (gemessen 17:52: Runde 3 sass im Bootloader).
    # --set-active=a fuellt ihn auf 3; das ist kein Tastendruck, nur ein Kommando.
    echo 'restart2 bootloader' > $KNOTE/rueckweg-halte.txt
    python3 $FL/sende-befehl.py @$KNOTE/rueckweg-halte.txt >/dev/null 2>&1
    f=0
    until /Users/gregor/Library/Android/sdk/platform-tools/fastboot devices 2>/dev/null | grep -Eq 'PIXEL3-SERIAL|fastboot'; do
        sleep 2; f=$((f + 1)); [ $f -ge 30 ] && break
    done
    [ $f -lt 30 ] || { say "Runde $runde: Fastboot kam nicht"; melde "restart2 brachte in Runde $runde kein Fastboot"; break; }
    /Users/gregor/Library/Android/sdk/platform-tools/fastboot --set-active=a >/dev/null 2>&1
    /Users/gregor/Library/Android/sdk/platform-tools/fastboot reboot >/dev/null 2>&1
    say "Runde $runde: Neustart kommandiert ($((f * 2)) s bis Fastboot)"
    b=0
    while [ $b -lt 30 ]; do
        sleep 10; b=$((b + 1))
        nc -z -G 3 172.16.42.1 23 2>/dev/null && break
    done
    v=0
    while [ $v -lt 12 ]; do
        sleep 25; v=$((v + 1))
        python3 $KNOTE/lesung.py $KNOTE/lies-halte.txt > $KNOTE/halte-lesung.txt 2>/dev/null
        grep -q '@@ENDE' $KNOTE/halte-lesung.txt && break
    done
    say "Runde $runde, Lesung nach $((25 * v)) s:"
    sed -e 's/^/    | /' $KNOTE/halte-lesung.txt
    if grep -q 'emergency_ro' $KNOTE/halte-lesung.txt; then
        say "Runde $runde: HALTUNG VERLOREN"
    elif grep -q ' / ext4 rw' $KNOTE/halte-lesung.txt && grep -q 'schreib=0' $KNOTE/halte-lesung.txt; then
        gehalten=$((gehalten + 1)); say "Runde $runde: GEHALTEN (rw, Schreibtest 0)"
    else
        say "Runde $runde: Lage unklar, nachmessen"
    fi
    sleep 5
done
say "URTEIL: $gehalten/3 Bootes mit offener Wurzel"
[ $gehalten -eq 3 ] || melde "Halte-Beweis: nur $gehalten von 3 Bootes gehalten"
} 2>&1 | tee "$LOG"
