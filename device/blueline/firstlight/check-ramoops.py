#!/usr/bin/env python3
"""Vermisst alle reserved-memory-Bereiche des Distro-DTB und prueft den
ramoops-Kandidaten 0x9f800000 (1 MiB) auf Ueberlappung — Claude-Checkin
2026-10-29: pstore darf in keinen Firmware-Carveout schreiben."""
import re
import subprocess
import sys

dts = sys.argv[1]
txt = open(dts).read()
i = txt.index("reserved-memory {")
depth = 0
j = i
for k in range(i, len(txt)):
    if txt[k] == "{":
        depth += 1
    elif txt[k] == "}":
        depth -= 1
        if depth == 0:
            j = k
            break
block = txt[i:j]
regions = []
for m in re.finditer(r"([\w-]+)\s*\{([^{}]*)\}", block):
    name, body = m.group(1), m.group(2)
    reg = re.search(r"reg = <([0-9a-fx\s]+)>;", body)
    if not reg:
        continue
    nums = [int(x, 16) for x in re.findall(r"0x([0-9a-f]+)", reg.group(1))]
    pairs = []
    if len(nums) % 4 == 0:
        for q in range(0, len(nums), 4):
            pairs.append((nums[q] << 32 | nums[q + 1], nums[q + 2] << 32 | nums[q + 3]))
    else:
        for q in range(0, len(nums), 2):
            pairs.append((nums[q], nums[q + 1]))
    for start, size in pairs:
        regions.append((name, start, size))
regions.sort(key=lambda x: x[1])
print(f"{'Bereich':34s} {'start':>14s} .. {'ende':>14s}")
for name, s, sz in regions:
    mb = sz / (1024 * 1024)
    print(f"{name:34s} 0x{s:012x} .. 0x{s+sz:012x}  ({mb:.0f} MiB)")
RA, RS = 0x9F800000, 0x100000
print()
overlap = [(n, hex(s), hex(sz)) for n, s, sz in regions
           if n != "memory" and not (RA + RS <= s or RA >= s + sz)]
print(f"ramoops-Kandidat 0x{RA:x}..0x{RA+RS:x}:")
print("  UEBERLAPPUNG mit:", overlap if overlap else "keine")
rs_ = sorted([(s, s + sz, n) for n, s, sz in regions if n != "memory"])
u = max([e for st, e, n in rs_ if e <= RA], default=None)
o = min([st for st, e, n in rs_ if st >= RA + RS], default=None)
u = hex(u) if u else "keiner"
o = hex(o) if o else "keiner"
print(f"  reserviert endet darunter: {u} | beginnt darueber: {o}")
if o != "keiner":
    lo = int(u, 16) if u != "keiner" else 0
    print(f"  freier Spalt zwischen den Carveouts: {(int(o, 16) - lo) // (1024*1024)} MiB")
else:
    print("  kein reservierter Bereich oberhalb (bis RAM-Obergrenze)")
