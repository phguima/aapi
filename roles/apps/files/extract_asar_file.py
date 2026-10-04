#!/usr/bin/env python3
"""Copy one top-level file out of an Electron app.asar archive.

Usage: extract_asar_file.py <app.asar> <name inside the archive> <destination>

The asar header is a Chromium Pickle: 4-byte size field, 4-byte header size, then a pickled
string (4-byte payload size, 4-byte string length, JSON). File data starts right after the
header, at the offsets the JSON gives. Avoids pulling Node and @electron/asar just for an icon.
"""
import json
import os
import struct
import sys

asar, name, dest = sys.argv[1:4]
with open(asar, "rb") as f:
    _, header_size, _, json_len = struct.unpack("<4I", f.read(16))
    header = json.loads(f.read(json_len))
    entry = header["files"][name]
    f.seek(8 + header_size + int(entry["offset"]))
    data = f.read(entry["size"])

os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "wb") as out:
    out.write(data)
