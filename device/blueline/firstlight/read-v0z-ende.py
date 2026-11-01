#!/usr/bin/env python3
import zipfile
z = zipfile.ZipFile('/Users/gregor/hermes-workspace/images/fl-v0z/new.cpio')
data = z.read('init').decode('utf-8', 'replace').splitlines()
print("Gesamtzeilen:", len(data))
for i, line in enumerate(data[470:], start=471):
    print(f"{i}|{line}")
