# -*- coding: utf-8 -*-
"""HWPX unpack / repack helpers.

An .hwpx file is an OPC (ZIP) container. Two rules matter for Hangul to
re-open a repacked file:
  1. the `mimetype` entry must be the FIRST entry and stored UNCOMPRESSED.
  2. all other entries are normal DEFLATE.
"""
import os
import shutil
import zipfile


def _onerr(func, path, exc):
    os.chmod(path, 0o777)
    func(path)


def unpack(hwpx_path, out_dir):
    """Extract an .hwpx into out_dir (cleared first). Returns out_dir."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir, onexc=_onerr)
    os.makedirs(out_dir)
    with zipfile.ZipFile(hwpx_path) as z:
        z.extractall(out_dir)
    return out_dir


def pack(src_dir, hwpx_path):
    """Repack src_dir into an .hwpx (mimetype first, stored)."""
    if os.path.exists(hwpx_path):
        os.remove(hwpx_path)
    with zipfile.ZipFile(hwpx_path, "w") as zf:
        mt = os.path.join(src_dir, "mimetype")
        if os.path.exists(mt):
            zf.write(mt, "mimetype", compress_type=zipfile.ZIP_STORED)
        for dirpath, _, files in os.walk(src_dir):
            for fn in files:
                full = os.path.join(dirpath, fn)
                arc = os.path.relpath(full, src_dir).replace(os.sep, "/")
                if arc == "mimetype":
                    continue
                zf.write(full, arc, compress_type=zipfile.ZIP_DEFLATED)
    return hwpx_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4 or sys.argv[1] not in ("unpack", "pack"):
        print("usage: hwpx_pack.py unpack <file.hwpx> <dir>")
        print("       hwpx_pack.py pack   <dir> <file.hwpx>")
        sys.exit(1)
    cmd, a, b = sys.argv[1:4]
    if cmd == "unpack":
        print(unpack(a, b))
    else:
        print(pack(a, b))
