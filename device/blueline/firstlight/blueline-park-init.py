#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import gzip
from pathlib import Path
import subprocess
import sys
import tempfile

import newc

source, output = map(Path, sys.argv[1:])
with tempfile.NamedTemporaryFile() as archive:
    archive.write(gzip.decompress(source.read_bytes()))
    archive.flush()
    entries = newc.read_cpio(archive.name)
entry = next(entry for entry in entries if entry["name"] == "init")
init = entry["content"].decode()
park = """# Keep a blocking descriptor alive after switch_root removes the early binaries.
park_ready=0
if mkfifo -m 600 /run/blueline-init-park; then
    exec 8<>/run/blueline-init-park
    rm -f /run/blueline-init-park
    park_ready=1
fi
park_init() {
    [ "$park_ready" = 1 ] || return
    while :; do
        read -r -t 3600 _ <&8 || :
    done
}
"""
mount = "mount -t tmpfs tmpfs /run || mark 'mount tmpfs FAILED'"
assert init.count(mount) == 1
init = init.replace(mount, mount.replace("-t tmpfs", "-t tmpfs -o mode=755") + "\n" + park)
handoff = '            mark "v0ak switch_root kehrt zurueck: Ramdisk bleibt Wurzel"'
assert init.count(handoff) == 1
init = init.replace(handoff, '            park_init\n' + handoff)
pos = init.index('logflush() {')
end = init.index('\n}\n', pos)
init = init[:pos] + 'logflush() {\n    return 0' + init[end:]
# Keep early USB recovery and stop the RAM debug telnet loop before user services start.
telnet = '( while :; do telnetd -l /bin/sh; sleep 2; done ) &'
assert init.count(telnet) == 1
init = init.replace(telnet, 'telnetd -b 172.16.42.1 -l /bin/sh')
switch_root = '            /sbin/switch_root /ud /init'
init = init.replace(switch_root, '            pkill -x telnetd 2>/dev/null || true\n' + switch_root)
start = init.index('UDNAME=""\n')
end = init.index('[ -n "$UDNAME" ]', start)
init = init[:start] + '''UDNAME=""
UDDISK=""
for uevent in /sys/block/sd*/sd*/uevent; do
    grep -qx 'PARTNAME=userdata' "$uevent" || continue
    part=${uevent%/uevent}
    [ "$(cat "$part/start")" = "$UDSTART" ] || continue
    disk=${part%/*}
    grep -qx 'PARTNAME=boot_a' "$disk/${disk##*/}11/uevent" || continue
    grep -qx 'PARTNAME=boot_b' "$disk/${disk##*/}12/uevent" || continue
    UDNAME=${part##*/}
    UDDISK=${disk##*/}
    break
done
''' + init[end:]
init = init.replace('scheibe="${ud%[0-9]*}"', 'scheibe="${ud%%[0-9]*}"')
init = init.replace('            [ -n "$ud" ] && [ sda = "${s##*/}" ] && continue\n', '')
handoff_start = init.index('if [ -n "$UDNAME" ]; then')
handoff_end = init.index('# v0af:', handoff_start)
handoff_code = init[handoff_start:handoff_end]
handoff_code = handoff_code.replace('/dev/sda', '/dev/$UDDISK')
handoff_code = handoff_code.replace('/sys/block/sda/sda*', '/sys/block/$UDDISK/$UDDISK*')
init = init[:handoff_start] + handoff_code + init[handoff_end:]
subprocess.run(['sh', '-n'], input=init.encode(), check=True)
entry["content"] = init.encode()
output.write_bytes(gzip.compress(newc.emit(entries), mtime=0))
