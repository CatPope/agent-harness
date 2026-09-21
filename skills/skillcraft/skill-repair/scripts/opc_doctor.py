#!/usr/bin/env python3
"""Diagnose why an OPC/ZIP document (.hwpx / .docx / .pptx / .xlsx / .odt ...)
is broken or won't open. Standard library only, so a no-base agent can run it.

It checks the structural mistakes that silently corrupt these containers:
  * the file is a valid, non-truncated ZIP;
  * if it uses a `mimetype` marker (HWPX / ODF), that entry is FIRST and stored
    UNCOMPRESSED — the classic "Hangul won't open it" bug;
  * every XML part (`.xml` / `.rels` / `.hpf`) is well-formed.

Usage:
    python opc_doctor.py <document>

Exit code is non-zero if any FAIL is reported. This validates the *container*,
not the document's meaning — a file can pass here and still look wrong, so the
human open-and-check step still applies.
"""
import sys
import zipfile
from xml.dom import minidom

OK, WARN, FAIL = "ok ", "warn", "FAIL"
XML_SUFFIXES = (".xml", ".rels", ".hpf")


def main(argv):
    # Entry names and messages can contain non-ASCII (e.g. Korean filenames);
    # keep output from crashing on a legacy console (Windows cp949, etc.).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - older Pythons / non-reconfigurable stream
        pass
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]

    rows = []
    def add(level, msg):
        rows.append((level, msg))

    # 1) Valid ZIP?
    if not zipfile.is_zipfile(path):
        print("FAIL: not a ZIP/OPC container (or file missing): {}".format(path))
        return 1

    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad is not None:
            add(FAIL, "corrupt/truncated entry: {}".format(bad))
        else:
            add(OK, "zip integrity ok ({} entries)".format(len(z.infolist())))

        names = z.namelist()
        infos = z.infolist()

        # 2) mimetype convention (HWPX / ODF). Absent for OOXML (docx/xlsx/pptx).
        if "mimetype" in names:
            first = infos[0]
            if first.filename != "mimetype":
                add(FAIL, "'mimetype' is not the FIRST entry (it is #{}: {}) - "
                          "Hangul/ODF will refuse to open the file".format(
                              names.index("mimetype"), first.filename))
            elif first.compress_type != zipfile.ZIP_STORED:
                add(FAIL, "'mimetype' is compressed; it MUST be stored "
                          "uncompressed (ZIP_STORED)")
            else:
                add(OK, "'mimetype' is first and stored uncompressed")
        else:
            add(WARN, "no 'mimetype' entry (normal for OOXML .docx/.xlsx/.pptx)")

        # 3) XML well-formedness of every XML-ish part.
        xml_parts = [n for n in names if n.lower().endswith(XML_SUFFIXES)]
        broken = []
        for n in xml_parts:
            try:
                minidom.parseString(z.read(n))
            except Exception as e:  # noqa: BLE001 - report any parse failure
                broken.append((n, str(e).splitlines()[0]))
        if broken:
            for n, err in broken:
                add(FAIL, "malformed XML in {}: {}".format(n, err))
        else:
            add(OK, "all {} XML part(s) are well-formed".format(len(xml_parts)))

    print("=== opc_doctor: {} ===".format(path))
    for level, msg in rows:
        print("  [{}] {}".format(level, msg))
    failed = sum(1 for lvl, _ in rows if lvl == FAIL)
    print("--- {} check(s), {} failing ---".format(len(rows), failed))
    if failed:
        return 1
    print("container looks structurally valid (still open it once to confirm)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
