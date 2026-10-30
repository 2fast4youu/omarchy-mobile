#!/bin/sh
# v0m bauen: v0l plus echtes RESTART2 ('restart2 bootloader') und Sonde 150.
#
# Warum: busybox reboot ruft reboot(..., LINUX_REBOOT_CMD_RESTART, NULL) —
# Kommando 'bootloader' landet nirgends. Alle bisherigen Ketten
# 'reboot bootloader|fastboot|recovery' waren Warmboots ohne Grund, der
# letzte wirksame Schritt immer der sysrq-crash. ABOOT zahlte jeden
# Fehlschlag auf slot-retry-count:a ein (2 -> 0, slot-unbootable:a yes um
# 02:39) und zeigte dann selbst das Fastboot-Menue — die "Sonde war
# erfolgreich"-Lesung von v0k war ein zeitlicher Zufall.
#
# Messung: feuert die Sonde und ehrt ABOOT RESTART2 "bootloader", steht das
# Telefon bei ~155 s in fastboot (vom Host zaehlbar). Sonst: sysrq-crash ->
# panic=120 haelt den Trace zwei Minuten aufs Panel, und der naechste Boot
# spiegelt den pstore-Inhalt (ramoops-Feld sitzt seit v0k/v0l im DTB).
set -eo pipefail
docker run --rm \
  -v "$IMGD/fl-v0l":/l \
  -v "$IMGD/fl-v0k":/k \
  -v /Users/gregor/hermes-workspace/omarchy-mobile:/om:ro \
  -v /Users/gregor/hermes-workspace/pmos-ref-build/ref:/ref:ro \
  alpine:edge sh -euc '
apk add --no-cache build-base python3 gzip dtc >/dev/null 2>&1

echo "== poweroff-Knoten im DTB (wer registriert den restart-Handler?) =="
dtc -I dtb -O dts /ref/blueline.dtb 2>/dev/null > /tmp/a.dts
python3 - <<PY
import re
txt = open("/tmp/a.dts").read()
treffer = 0
for m in re.finditer(r"([\w-]+)\s*\{([^{}]*compatible[^{}]*)\}", txt):
    body = m.group(2)
    if any(k in body for k in ("poweroff", "pon", "restart")):
        comp = re.findall(r"compatible = \"([^\"]+)\"", body)
        print("  Knoten", m.group(1), "compatible:", comp)
        treffer += 1
if not treffer:
    print("  KEIN poweroff/pon-Knoten im DTB — RESTART2-Grund wuerde ins Leere laufen")
PY

echo "== restart2: RESTART2 mit Kommando, statisch =="
# Konstanten hartkodiert (linux/reboot.h ist in musl-Containern nicht da):
# LINUX_REBOOT_MAGIC1 fee1dead, MAGIC2 28121969, CMD_RESTART2 e1212120.
cat > /tmp/restart2.c <<EOF
#include <stdio.h>
#include <unistd.h>
#include <sys/syscall.h>
int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: restart2 <command>\n"); return 2; }
    sync();
    long rc = syscall(SYS_reboot, 0xfee1dead, 0x28121969, 0xe1212120, argv[1]);
    if (rc < 0) { perror("reboot RESTART2"); return 1; }
    sleep(10);
    return 0;
}
EOF
gcc -static -Os -o /tmp/restart2 /tmp/restart2.c
ls -l /tmp/restart2

echo "== Archiv umbauen: restart2 dazu, Sonde 150, Kette ersetzen =="
python3 - <<PY
import copy, sys
sys.path.insert(0, "/om/device/blueline/firstlight")
import newc
es = newc.read_cpio("/l/ramdisk.cpio")   # das v0l-Archiv (Init = v0l-Fassung)
init = [e for e in es if e["name"] == "init"][0]
text = init["content"].decode()
alt = """        reboot bootloader 2>/dev/null
        reboot fastboot 2>/dev/null
        reboot recovery 2>/dev/null
        echo c > /proc/sysrq-trigger 2>/dev/null"""
neu = """        /bin/restart2 bootloader
        mark "restart2 bootloader zurueck: $?"
        sleep 30
        mark "restart2 wirkte nicht — sysrq-crash als Notnagel"
        echo c > /proc/sysrq-trigger 2>/dev/null"""
assert text.count(alt) == 1, "Sonden-Kette nicht gefunden"
init["content"] = text.replace(alt, neu).encode()
probe = [e for e in es if e["name"] == "etc/omamobile-panic-probe"][0]
probe["content"] = b"150\n"
bb = [e for e in es if e["name"] == "bin/busybox"][0]
tool = copy.deepcopy(bb)
tool["name"] = "bin/restart2"
tool["content"] = open("/tmp/restart2", "rb").read()
es.append(tool)
open("/l/new.cpio", "wb").write(newc.emit(es))
print("Archiv umgebaut: restart2 (%d B), Sonde 150" % len(tool["content"]))
PY
gzip -n -9 -c /l/new.cpio > /l/ramdisk-m.gz

python3 /om/device/blueline/firstlight/pack-v0.py \
  --kernel /k/kernel-blob --ramdisk /l/ramdisk-m.gz \
  --cmdline "console=ttyMSM0,115200n8 console=tty0 loglevel=8 printk.devkmsg=on nowatchdog noreboot.not panic=120 androidboot.hardware=qcom androidboot.board=blueline rdinit=/init" \
  --name "" --kernel-addr 0x8000 --ramdisk-addr 0x1000000 --tags-addr 0x1000 \
  --pagesize-field 0 --pagesize-align 4096 --reference /ref/boot.img -o /l/v0m.img 2>&1 | tail -2

echo "== Gegenlesen aus dem fertigen Bild =="
python3 - <<PY
import gzip, struct
d = open("/l/v0m.img", "rb").read()
ks = struct.unpack_from("<I", d, 8)[0]
rs = struct.unpack_from("<I", d, 16)[0]
rd = 4096 + ((ks + 4095) // 4096) * 4096
assert d[rd:rd + 3] == b"\x1f\x8b\x08", "ramdisk nicht seitenbuendig"
raw = gzip.decompress(d[rd:rd + rs])
assert raw.count(b"bin/restart2\0") == 1, "restart2 fehlt im fertigen Bild"
i = raw.find(b"etc/omamobile-panic-probe\0")
ns = int(raw[i - 16:i - 8], 16)
fs = int(raw[i - 110 + 54:i - 110 + 62], 16)
data = ((i - 110 + 110 + ns) + 3) & ~3
assert raw[data:data + fs] == b"150\n", raw[data:data + fs]
assert b"restart2 bootloader" in raw, "neue Sonde-Kette fehlt"
cmd = d[64:576].split(b"\0")[0].decode()
assert "panic=120" in cmd, cmd
print("v0m ok: restart2 im Bild, Sonde 150, panic=120,", len(d), "Bytes")
PY
sha256sum /l/v0m.img
cp /l/v0m.img /l/firstlight.img
'
