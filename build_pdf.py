#!/usr/bin/env python3
"""
Builds report_plain.pdf from report.md with pandoc and xelatex.

This is the plain build of the report, the one anyone can reproduce from this repository with
pandoc alone. The typeset `report.pdf` shipped here was produced separately from the same
`report.md`; the text of the two is identical.

The only thing this script does beyond calling pandoc is to drop the level-1 title heading at the
top of report.md: the PDF takes its title block from pdf/meta.yaml, and leaving the heading in
would print the title twice and list it in the table of contents.

    python build_pdf.py
"""
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
SOURCE, META, OUTPUT = "report.md", os.path.join("pdf", "meta.yaml"), "report_plain.pdf"


def main():
    with open(os.path.join(BASE, SOURCE), encoding="utf-8") as f:
        lines = f.read().split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    fd, tmp = tempfile.mkstemp(suffix=".md", dir=BASE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        cmd = ["pandoc", os.path.join(BASE, META), tmp, "-o", os.path.join(BASE, OUTPUT),
               "--pdf-engine=xelatex", "--resource-path=" + BASE]
        rc = subprocess.call(cmd)
    finally:
        os.remove(tmp)
    if rc == 0:
        print(OUTPUT, "written")
    sys.exit(rc)


if __name__ == "__main__":
    main()
