#!/usr/bin/env python3
"""
Assembles the report: sections + tables + figures -> report.md

The section files contain placeholders of the form [Table T6], [Table: design nomenclature] and
[Figure F1]. Tables live in tables.md (whose numbers are produced by build_tables.py); figures live
in figures/ (produced by make_figures.py). Nothing is rewritten here: this script only concatenates
and substitutes.

It also refreshes README.md: the block between <!-- abstract --> ... <!-- /abstract --> is
replaced with the current §0, and the blocks between <!-- table:Tn --> ... <!-- /table --> with
the current tables from tables.md, so the README never carries a number that the script did not
produce.

The one thing it does rewrite is the separator row of every markdown table, which is what sets
the column widths in the PDF: see fit_table_widths below.

Run it after every change to a section, to tables.md or to a figure:

    python assemble.py
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
TABLES = "tables.md"
SECTIONS = [
    "sections/00_abstract.md",
    "sections/01_repository_and_paper.md",
    "sections/02_benchmarks.md",
    "sections/03_cost_reconstruction.md",
    "sections/04_three_levers.md",
    "sections/05_ranking_stability.md",
    "sections/06_s4_prime.md",
    "sections/07_paper_and_code.md",
    "sections/08_limitations.md",
]
APPENDIX = "sections/appendix_a_deflated_sharpe_ratio.md"
REFERENCES = "sections/09_references.md"
FIGURES = {
    "F1": ("figures/F1_out_of_sample_validation.png",
           "F1. Out-of-sample validation of the cost reconstruction"),
    "F2": ("figures/F2_factorial_design.png",
           "F2. The four cells of the VWAP entry filter × exit structure plane, under the two exit thresholds"),
    "F3": ("figures/F3_net_profit_vs_slippage.png",
           "F3. Decay under costs. The 0 bps baseline already includes IB commissions"),
}
README = "README.md"
TITLE = "# Intraday momentum on SPY: an independent replication and cost analysis of `blackswan-quants/intraday-momentum`"
OUTPUT = "report.md"


def read(name):
    with io.open(os.path.join(BASE, name), encoding="utf-8") as f:
        return f.read()


def table_blocks(text):
    """Split tables.md on '### ' headings and index the blocks by key (T6, T9, or the lowercased title)."""
    out = {}
    for piece in re.split(r"^### ", text, flags=re.M)[1:]:
        title = piece.split("\n", 1)[0]
        m = re.match(r"(T\d+[a-z]?)\b", title)
        key = m.group(1) if m else title.strip().lower()
        # a block ends where the next '## ' heading or a '---' separator begins
        lines = []
        for line in piece.split("\n"):
            if re.match(r"^---\s*$", line) or re.match(r"^##(?!#)\s", line):
                break
            lines.append(line)
        out[key] = "### " + "\n".join(lines).rstrip() + "\n"
    return out


def substitute(text, tables, used, missing):
    def tab(m):
        key = m.group(1)
        k = key if re.match(r"^T\d+[a-z]?$", key) else key.strip(": ").lower()
        if k in tables:
            used.add(k)
            return tables[k]
        missing.append(m.group(0))
        return m.group(0)

    text = re.sub(r"\[Table:?\s*([^\]]+)\]", tab, text)

    def fig(m):
        k = m.group(1)
        if k in FIGURES and os.path.exists(os.path.join(BASE, FIGURES[k][0])):
            used.add(k)
            return "![%s](%s)" % (FIGURES[k][1], FIGURES[k][0])
        missing.append(m.group(0))
        return m.group(0)

    return re.sub(r"\[Figure\s+(F\d+)\]", fig, text)


# ================================================================================================
# Table column widths
# ================================================================================================
# Pandoc takes the relative width of a table's columns from the number of dashes in its separator
# row, and switches from natural sizing to fixed widths as soon as any line of the table is longer
# than 72 characters (its --columns default), which is the case for most tables here. A separator
# written `|---|---|---|` therefore gives every column the same share of the page, and a cell
# whose longest word does not fit its share overflows into the column next to it: that is what
# turns "reproduced" and "196.125%" into "reproduced196.125%" in the PDF.
#
# The pass below rewrites the separator from the content. Each column asks for the width its
# widest row needs, measured in ems of the table font; when the total does not fit the text block
# the surplus is shared out in proportion to how much each column asked for beyond its longest
# unbreakable word, so a column of prose wraps and a column of numbers never does. Columns whose
# cells are mostly numeric are right-aligned. A table that fits at its natural width and is
# already short enough for pandoc to size on its own is left alone, so small tables stay compact
# instead of being stretched across the page.

PAGE_WIDTH_PT = 461.0     # \columnwidth for a4paper with 2.4cm margins
TABCOLSEP_PT = 4.0        # \tabcolsep, set in pdf/meta.yaml
TABLE_FONT_PT = 9.0       # \small, applied to every table in pdf/meta.yaml
PANDOC_COLUMNS = 72       # pandoc's --columns default
MONO_EM = 0.602           # DejaVu Sans Mono is monospaced at this width

# Width of a character in ems of DejaVu Serif, close enough for laying out columns.
_EM = {" ": 0.32, ".": 0.32, ",": 0.32, ":": 0.34, ";": 0.34, "'": 0.28, "\u2019": 0.28,
       "%": 0.95, "(": 0.39, ")": 0.39, "[": 0.39, "]": 0.39, "-": 0.42, "\u2212": 0.60,
       "+": 0.60, "/": 0.34, "=": 0.60, "<": 0.60, ">": 0.60, "!": 0.35, "?": 0.44,
       "\u2032": 0.31, "\u00d7": 0.60, "\u00b7": 0.32}
_SPAN = re.compile(r"(`[^`]*`|\$[^$]*\$)")
_NUMERIC = re.compile(r"^[\-+\u2212]?[\d,]+(?:\.\d+)?%?$")


def _text_em(s):
    """Width of plain text, in ems."""
    return sum(_EM.get(c, 0.636 if c.isdigit() else 0.70 if c.isupper() else 0.52) for c in s)


def _math_em(s):
    """Width of an inline formula: every control sequence prints as roughly one glyph."""
    s = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+", "n", s)
    s = re.sub(r"[{}\\^_ ]", "", s)
    return 0.55 * len(s)


def _plain(cell):
    """The cell with its markdown emphasis removed, for the numeric test."""
    return re.sub(r"[*`$]", "", cell).strip()


def _pieces(cell):
    """The cell as (width, breakable) pieces: formulas and code spans never break."""
    cell = re.sub(r"\*\*|\*", "", cell.replace("<br>", " ")).strip()
    out = []
    for part in _SPAN.split(cell):
        if not part:
            continue
        if part.startswith("`"):
            out.append((MONO_EM * (len(part) - 2), False))
        elif part.startswith("$"):
            out.append((_math_em(part[1:-1]), False))
        else:
            for word in part.split():
                out.append((_text_em(word), True))
    return out or [(0.0, True)]


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _allocate(natural, minimum, budget):
    if sum(natural) <= budget:
        return natural
    slack = budget - sum(minimum)
    if slack <= 0:
        return minimum
    room = [n - m for n, m in zip(natural, minimum)]
    total = sum(room) or 1.0
    return [m + slack * r / total for m, r in zip(minimum, room)]


def _separator(rows, raw_lines):
    n = len(rows[0])
    natural = [max(sum(w for w, _ in _pieces(r[c])) + 0.6 for r in rows) for c in range(n)]
    minimum = [max(max(w for w, _ in _pieces(r[c])) + 0.6 for r in rows) for c in range(n)]
    body = rows[1:]
    aligns = []
    for c in range(n):
        vals = [_plain(r[c]) for r in body if _plain(r[c])]
        hits = sum(1 for v in vals if _NUMERIC.match(v))
        aligns.append("r" if len(vals) >= 2 and hits >= 0.6 * len(vals) else "l")
    budget = 0.95 * (PAGE_WIDTH_PT - (2 * n - 2) * TABCOLSEP_PT) / TABLE_FONT_PT
    if sum(natural) <= budget and max(len(l) for l in raw_lines) <= PANDOC_COLUMNS:
        # pandoc will size this one itself, and a short separator keeps it compact
        return "|" + "|".join("---:" if a == "r" else ":---" for a in aligns) + "|"
    widths = _allocate(natural, minimum, budget)
    scale = 100.0 / max(sum(widths), 1e-9)
    out = []
    for w, a in zip(widths, aligns):
        dashes = "-" * max(3, int(round(w * scale)))
        out.append(dashes + ":" if a == "r" else ":" + dashes)
    return "|" + "|".join(out) + "|"


def fit_table_widths(text):
    """Rewrite every markdown table's separator row so the columns are sized from their content."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        head = lines[i]
        if head.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            raw = [lines[i]] + lines[i + 2:j]
            rows = [_cells(l) for l in raw]
            if len(set(len(r) for r in rows)) == 1 and len(rows[0]) > 1:
                out.append(head)
                out.append(_separator(rows, raw))
                out.extend(lines[i + 2:j])
                i = j
                continue
        out.append(head)
        i += 1
    return "\n".join(out)


def refresh_readme(tables):
    """Replace every <!-- table:Tn --> ... <!-- /table --> block in README.md with the current table."""
    path = os.path.join(BASE, README)
    if not os.path.exists(path):
        return
    text = read(README)

    def rep(m):
        key = m.group(1)
        if key not in tables:
            return m.group(0)
        # drop the '### Tn.' heading line: the README has its own
        body = tables[key].split("\n", 1)[1].strip("\n")
        return "<!-- table:%s -->\n%s\n<!-- /table -->" % (key, body)

    new = re.sub(r"<!-- table:(T\d+) -->\n.*?<!-- /table -->", rep, text, flags=re.S)
    # the abstract, from sections/00_abstract.md without its heading
    abstract = read(SECTIONS[0]).split("\n", 1)[1].strip("\n")
    new = re.sub(r"<!-- abstract -->\n.*?<!-- /abstract -->",
                 lambda m: "<!-- abstract -->\n%s\n<!-- /abstract -->" % abstract, new, flags=re.S)
    if new != text:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print("README.md: tables refreshed")


def main():
    tables = table_blocks(read(TABLES))
    refresh_readme(tables)
    used, missing, parts = set(), [], [TITLE, ""]

    for name in SECTIONS:
        if not os.path.exists(os.path.join(BASE, name)):
            print("  missing:", name, file=sys.stderr)
            continue
        parts.append(substitute(read(name), tables, used, missing).rstrip())
        parts.append("")

    appendix = read(APPENDIX).replace("# Deflated Sharpe Ratio on S4′ tight",
                                      "# Appendix A. Deflated Sharpe Ratio on S4′ tight", 1)
    parts.append(substitute(appendix, tables, used, missing).rstrip())
    parts.append("")
    parts.append(read(REFERENCES).rstrip())
    out = fit_table_widths("\n".join(parts) + "\n")

    with io.open(os.path.join(BASE, OUTPUT), "w", encoding="utf-8") as f:
        f.write(out)

    print("%s: %d words" % (OUTPUT, len(out.split())))
    unused = sorted(set(tables) - used) + sorted(set(FIGURES) - used)
    if unused:
        print("not referenced by any placeholder:", ", ".join(unused))
    if missing:
        print("placeholders without a block:", ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    main()
