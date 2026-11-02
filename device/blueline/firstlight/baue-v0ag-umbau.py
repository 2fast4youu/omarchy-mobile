#!/usr/bin/env python3
"""v0af -> v0ag: die Wurzel zieht auf userdata (M1.5).

Grund (Anweisung 2026-11-02, 15:31): der kuerzeste Weg auf ein schreibbares Root
ist die userdata-Partition selbst, wie ihn auch pmOS geht — kein Telnet-Upload.
Vor dem Write ist belegt, dass die Partition keine Nutzerdaten traegt: Superblock
null, mount -o ro meldet 'wrong fs type, bad superblock', entsperrt (Nachtrag 21,
Beweise in evidence/vor-userdata/). Ein 64-GB-Backup gibt es nicht.

Drei Aenderungen, jede auf den im Bild gelesenen Text verankert:

  A) Die Partitionssuche steht VOR der Wache (Zeile 523). Die Wache ist ein
     Hintergrund-Unterlauf, der beim Fork kopiert: spaetere Variablen des Vaters
     sieht er nicht. Sie bekommt ihre Ausnahme aus /tmp/uddev und ueberspringt
     zusaetzlich die ganze Platte sda, solange eine userdata-Wurzel beansprucht
     ist — der ro-Schalter einer Partition folgt dem der Platte (19:40 gemessen),
     eine rw gemountete Partition unter einer ro Platte schreibt nicht.
     Gesucht wird ueber den Anfangssektor aus der GPT, nicht ueber PARTNAME:
     ein by-partlabel-Ordner fehlt in dieser Ramdisk (partlabel.txt = 0 B), und
     'die groesste Partition' ist geraten, nicht gelesen.
  B) Mount, Marker, switch_root — direkt vor der Halteschleife, damit Gadget,
     Telnet und Shell schon stehen. Jeder Fehlschlag faellt in die Halteschleife
     zurueck; der Funkstille-Rueckweg wird nicht verlassen, ohne dass er in der
     neuen Wurzel weiterlaufen kann (rootfs-init-fuer-ud.sh fuehrt ihn dort).
  C) Panel-Titel auf v0ag.

Der Rest bleibt, wie er ist: Module, Ordnereintraege, Rueckweg-Binaries, Guard.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc

GRUNDZEILEN = 611          # im v0af-Archiv gemessen, nicht im Kopf
TITEL_AN = "Omarchy Mobile first-light v0af - RAM only, Rueckkehr nach Funkstille"
TITEL_NEU = "Omarchy Mobile first-light v0ag - userdata rw, Rueckkehr nach Funkstille"

WACHE_AN = "            [ -n \"$bootdev\" ] && [ \"$bootdev\" = \"${s##*/}\" ] && continue\n"
WACHE_NEU = WACHE_AN + (
    "            # v0ag: die belegte userdata-Partition und die Platte darunter\n"
    "            # bleiben rw, alles andere unter der Wache. Die Liste liegt in\n"
    "            # /tmp/uddev, weil dieser Unterlauf die Variablen des Vaters\n"
    "            # nicht sieht (fork kopiert, gemessen).\n"
    "            ud=\"$(cat /tmp/uddev 2>/dev/null)\"\n"
    "            [ -n \"$ud\" ] && [ \"$ud\" = \"${s##*/}\" ] && continue\n"
    "            [ -n \"$ud\" ] && [ sda = \"${s##*/}\" ] && continue\n"
)

SUCHE = """# v0ag: userdata wird gesucht, bevor die Wache forked. Der Anfangssektor kommt
# aus der GPT-Auschrift (LBA 2068480, in 512-Byte-Blocken 16547840), nicht aus
# dem Kopf. Ein by-partlabel-Ordner existiert in dieser Ramdisk nicht.
UDSTART=16547840
UDNAME=""
for s in /sys/block/sda/sda*; do
    [ "$(cat "$s/start" 2>/dev/null)" = "$UDSTART" ] && UDNAME=${s##*/}
done
[ -n "$UDNAME" ] && echo "$UDNAME" > /tmp/uddev
mark "v0ag userdata-suche: partition=${UDNAME:-KEINE} sektor=$UDSTART"
logflush

"""

UEBERGABE = """# v0ag: Wurzel von userdata (M1.5). Platte zuerst rw, weil der ro-Schalter
# einer Partition dem der Platte folgt (19:40 gemessen). Alle anderen
# Partitionen werden einzeln zurueck unter ro gelegt und die Wache laeuft
# weiter. Ein Fehlschlag faellt in die Halteschleife; der Rueckweg bleibt.
if [ -n "$UDNAME" ]; then
    blockdev --setrw /dev/sda 2>/dev/null
    mkdir -p /ud/dev /ud/proc /ud/sys /ud/run /ud/tmp
    if mount -o rw "/dev/$UDNAME" /ud 2>/dev/null; then
        mark "v0ag userdata rw: $(mount | grep ' /ud ' | xargs)"
        if [ -f /ud/.v0ag-besuch ]; then
            mark "v0ag marker wiedergefunden: $(cat /ud/.v0ag-besuch 2>/dev/null)"
        else
            printf 'besuch zeit=%s\\n' "$(cut -d. -f1 /proc/uptime)" > /ud/.v0ag-besuch
            sync
            mark "v0ag marker geschrieben: $(cat /ud/.v0ag-besuch 2>/dev/null)"
        fi
        for s in /sys/block/sda/sda*; do
            [ "${s##*/}" = "$UDNAME" ] && continue
            blockdev --setro "/dev/${s##*/}" 2>/dev/null
        done
        echo probe > /ud/.v0ag-schreib 2>/dev/null
        sync
        mark "v0ag wache: platte_ro=$(blockdev --getro /dev/sda 2>/dev/null) ud_ro=$(blockdev --getro /dev/$UDNAME 2>/dev/null) schreibtest=$(cat /ud/.v0ag-schreib 2>/dev/null)"
        logflush
        if [ -x /ud/init ] && [ -x /sbin/switch_root ]; then
            mark "v0ag uebergabe: switch_root /ud /init"
            sync
            /sbin/switch_root /ud /init
            mark "v0ag switch_root kehrt zurueck: Ramdisk bleibt Wurzel"
            logflush
        else
            mark "v0ag uebergabe bleibt aus: init_da=$(ls -l /ud/init 2>/dev/null | wc -c) schalter=$(ls /sbin/switch_root 2>/dev/null)"
            logflush
        fi
    else
        mark "v0ag userdata mount rw fehlgeschlagen: $(dmesg | tail -3 | tr '\\n' ';')"
        blockdev --setro /dev/sda 2>/dev/null
        logflush
    fi
fi

"""

ANKER_SUCHE = "# Re-assert the guard: a late-appearing LUN (or a rw flip) is caught the"
ANKER_UEBERGABE = "# v0af: der Selbst-Rueckweg ist keine Stoppuhr mehr, die die Shell weg nimmt."


def umbau(text):
    for anker in (ANKER_SUCHE, ANKER_UEBERGABE, WACHE_AN, TITEL_AN):
        assert text.count(anker) == 1, "Anker nicht eindeutig: %.60s" % anker
    text = text.replace(WACHE_AN, WACHE_NEU)
    text = text.replace(ANKER_SUCHE, SUCHE + ANKER_SUCHE)
    text = text.replace(ANKER_UEBERGABE, UEBERGABE + ANKER_UEBERGABE)
    text = text.replace(TITEL_AN, TITEL_NEU)
    assert "first-light v0af" not in text, "der alte Titel steht noch im Bild"
    assert "userdata rw" in text and "switch_root /ud /init" in text, "v0ag fehlt"
    for zeile in text.splitlines():
        assert all(ord(c) < 128 for c in zeile), "Nicht-ASCII in: %.60s" % zeile
    return text


def elternpruefung(es, wo):
    namen = {e["name"] for e in es} | {e["name"][2:] for e in es}
    fehl = [e["name"] for e in es
            if e["name"] != "TRAILER!!!" and e["content"] is not None
            and "/" in e["name"] and e["name"].rsplit("/", 1)[0] not in namen]
    assert not fehl, "%s: Dateien ohne Elternordner: %s" % (wo, fehl[:4])


def haupt():
    if len(sys.argv) != 3:
        print("Gebrauch: baue-v0ag-umbau.py EIN.cpio AUS.cpio", file=sys.stderr)
        return 2
    ein_cpio, aus_cpio = sys.argv[1], sys.argv[2]
    es = newc.read_cpio(ein_cpio)
    assert es[-1]["name"] == "TRAILER!!!", "TRAILER nicht letzter Eintrag"
    elternpruefung(es, "Grundarchiv")
    assert "sbin/switch_root" in {e["name"] for e in es}, "switch_root fehlt im Grundarchiv"
    treffer = 0
    for e in es:
        if e["name"] != "init":
            continue
        anfang = e["content"].decode()
        assert anfang.count("\n") == GRUNDZEILEN, \
            "Grundarchiv hat %d Zeilen, erwartet %d" % (anfang.count("\n"), GRUNDZEILEN)
        e["content"] = umbau(anfang).encode()
        treffer += 1
    assert treffer == 1, "init genau %d mal im Archiv" % treffer

    blob = newc.emit(es)
    neben = aus_cpio + ".r"
    with open(neben, "wb") as f:
        f.write(blob)
    zurueck = {e["name"]: e for e in newc.read_cpio(neben)}
    neuer = zurueck["init"]["content"]
    assert neuer == next(e["content"] for e in es if e["name"] == "init"), \
        "round-trip init nicht dicht"
    elternpruefung(list(zurueck.values()), "nach round-trip")
    os.remove(neben)
    with open(aus_cpio, "wb") as f:
        f.write(blob)
    os.chmod(aus_cpio, 0o644)
    print("baue-v0ag: init %d B, %d Zeilen, Eintraege %d, switch_root %d B, init sha %s"
          % (len(neuer), neuer.decode().count("\n"), len(zurueck),
             len(zurueck["sbin/switch_root"]["content"]),
             hashlib.sha256(neuer).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(haupt())
