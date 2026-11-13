#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mark boot_a successful in the two Pixel 3 GPT copies on the main LUN."""

import os
from pathlib import Path
import struct
import sys
import zlib

SECTOR = 4096
SUCCESS = 1 << 54
ENTRY_BYTES = 21 * 128


def update_crc(header, entries):
    struct.pack_into("<I", header, 88, zlib.crc32(entries))
    size, = struct.unpack_from("<I", header, 12)
    struct.pack_into("<I", header, 16, 0)
    struct.pack_into("<I", header, 16, zlib.crc32(header[:size]))


def prepare(fd, last, secondary):
    header_lba = last if secondary else 1
    # The factory backup header also points at LBA 2. Its mirrored entry
    # array is physically one sector before the secondary header.
    entries_lba = last - 1 if secondary else 2
    header = bytearray(os.pread(fd, SECTOR, header_lba * SECTOR))
    entries = bytearray(os.pread(fd, SECTOR, entries_lba * SECTOR))
    if len(header) != SECTOR or len(entries) != SECTOR:
        raise ValueError("short GPT read")
    size, header_crc = struct.unpack_from("<II", header, 12)
    current, alternate = struct.unpack_from("<QQ", header, 24)
    entry_lba, count, stride, entry_crc = struct.unpack_from("<QIII", header, 72)
    if (header[:8] != b"EFI PART" or size != 92
            or (current, alternate) != (header_lba, 1 if secondary else last)
            or entry_lba != 2 or (count, stride) != (21, 128)):
        raise ValueError("unexpected Pixel 3 GPT layout")
    if zlib.crc32(header[:16] + bytes(4) + header[20:size]) != header_crc:
        raise ValueError("GPT header checksum mismatch")
    boot = 10 * stride
    if entries[boot + 56:boot + 128].decode("utf-16le").rstrip("\0") != "boot_a":
        raise ValueError("unexpected boot_a entry")
    flags, = struct.unpack_from("<Q", entries, boot + 48)
    struct.pack_into("<Q", entries, boot + 48, flags & ~SUCCESS)
    without_success = zlib.crc32(entries[:ENTRY_BYTES])
    struct.pack_into("<Q", entries, boot + 48, flags | SUCCESS)
    updated = entries[:ENTRY_BYTES]
    if entry_crc not in (without_success, zlib.crc32(updated)):
        raise ValueError("GPT entry checksum mismatch")
    update_crc(header, updated)
    return (header_lba, header), (entries_lba, entries)


def main():
    compatible = Path("/proc/device-tree/compatible").read_bytes().split(b"\0")
    cmdline = Path("/proc/cmdline").read_text().split()
    if b"google,blueline" not in compatible or "androidboot.slot_suffix=_a" not in cmdline:
        raise ValueError("expected Pixel 3 booted from slot A")
    base = Path("/sys/class/block/sda")
    if ((base / "ro").read_text().strip() != "0"
            or int((base / "queue/logical_block_size").read_text()) != SECTOR):
        raise ValueError("main UFS device is not writable with 4 KiB sectors")
    for index, name in ((11, "boot_a"), (12, "boot_b")):
        part = Path(f"/sys/class/block/sda{index}")
        if (f"PARTNAME={name}" not in (part / "uevent").read_text().splitlines()
                or (part / "ro").read_text().strip() != "1"):
            raise ValueError(f"unexpected or writable {name} partition")
    sectors, remainder = divmod(int((base / "size").read_text()) * 512, SECTOR)
    if remainder or sectors < 8:
        raise ValueError("invalid UFS size")

    fd = os.open("/dev/sda", os.O_RDWR)
    try:
        primary = prepare(fd, sectors - 1, False)
        backup = prepare(fd, sectors - 1, True)
        if primary[1][1][:ENTRY_BYTES] != backup[1][1][:ENTRY_BYTES]:
            raise ValueError("GPT copies differ outside the boot-success bit")
        for header, entries in (backup, primary):
            for lba, data in (entries, header):
                offset = lba * SECTOR
                if os.pread(fd, SECTOR, offset) == data:
                    continue
                if os.pwrite(fd, data, offset) != SECTOR:
                    raise OSError("short GPT write")
                os.fsync(fd)
                if os.pread(fd, SECTOR, offset) != data:
                    raise OSError("GPT readback mismatch")
    finally:
        os.close(fd)
    print("boot_a successful; primary and backup GPT checked")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(f"blueline boot-success: {error}")
