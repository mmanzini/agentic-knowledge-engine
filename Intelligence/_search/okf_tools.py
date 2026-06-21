#!/usr/bin/env python3
"""In-place OKF tooling for the live wiki — no export snapshot.

Each bucket directory *is* its own OKF bundle: `index.md` routers, articles
with `type` frontmatter + a `related:` graph, and a derived `log.md`. This
script maintains the two derived/checked pieces:

  --check            conformance pass (every article has `type`; related:/
                     relative links resolve). Prints `okf=conformant` or
                     `okf=<N>-violations`. Used by the `refine` verb.
  --log [bucket ...] (re)write `Intelligence/<bucket>/log.md` from log.tsv
                     for the named buckets (default: all). Run by the
                     consolidate auto-chain for touched buckets.

No third-party deps. Governance zones (`_episodes/ _eval/ _search/
_unsorted/`) are never buckets and are skipped.
"""

import argparse
import re
import sys
from pathlib import Path

SEARCH_DIR = Path(__file__).resolve().parent
INTEL_DIR = SEARCH_DIR.parent
LOG_TSV = INTEL_DIR / "log.tsv"

SKIP_DIRS = {"_episodes", "_eval", "_unsorted", "_search", "_export"}
INDEX_FILES = {"index.md", "_index.md", "_master-index.md", "log.md"}


def iter_articles(only_bucket=None):
    """Yield (bucket, topic, path) for every article (non-router) file."""
    for bucket_dir in sorted(INTEL_DIR.iterdir()):
        if not bucket_dir.is_dir() or bucket_dir.name in SKIP_DIRS:
            continue
        if only_bucket and bucket_dir.name != only_bucket:
            continue
        for path in sorted(bucket_dir.rglob("*.md")):
            if path.name in INDEX_FILES:
                continue
            rel = path.relative_to(INTEL_DIR)
            topic = rel.parts[1] if len(rel.parts) > 2 else ""
            yield bucket_dir.name, topic, path


def split_frontmatter(text):
    """Return (frontmatter_dict_or_None, body). Minimal YAML-ish reader."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    block, body = text[4:end], text[end + 4:].lstrip("\n")
    fm, key = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                fm[key] = []
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [x.strip() for x in inner.split(",")] if inner else []
            else:
                fm[key] = val
        elif line.lstrip().startswith("- ") and key is not None:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(line.lstrip()[2:].strip())
    return fm, body


# ---------------------------------------------------------------- conformance

def check_conformance(only_buckets=None):
    """Return (violations:int, lines:list[str]) without writing anything."""
    missing_type, unresolved = [], []
    for bucket, _topic, path in iter_articles():
        if only_buckets and bucket not in only_buckets:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        rel = str(path.relative_to(INTEL_DIR))
        if fm is None or not fm.get("type"):
            missing_type.append(rel)
            fm = fm or {}
        for tgt in fm.get("related", []) if isinstance(fm.get("related"), list) else []:
            if not (INTEL_DIR / tgt).exists():
                unresolved.append(f"{rel} → related:{tgt}")
        # inline relative .md links *inside the wiki* must resolve; links
        # pointing outside Intelligence/ (e.g. ../../Resources source citations)
        # are provenance, not OKF graph edges — skip them.
        for m in re.findall(r"\]\((\.{1,2}/[^)]+\.md)\)", body):
            tgt = (path.parent / m).resolve()
            try:
                tgt.relative_to(INTEL_DIR)
            except ValueError:
                continue
            if not tgt.exists():
                unresolved.append(f"{rel} → {m}")
    n = len(missing_type) + len(unresolved)
    lines = []
    if missing_type:
        lines.append(f"  missing type ({len(missing_type)}): "
                     + ", ".join(missing_type[:5]) + (" …" if len(missing_type) > 5 else ""))
    if unresolved:
        lines.append(f"  unresolved links ({len(unresolved)}): "
                     + ", ".join(unresolved[:5]) + (" …" if len(unresolved) > 5 else ""))
    return n, lines


# ------------------------------------------------------------------- log.md

def derive_log_md(bucket):
    """Render a per-bucket OKF `log.md` from the central log.tsv rows."""
    if not LOG_TSV.exists():
        return None
    by_date = {}
    for line in LOG_TSV.read_text(encoding="utf-8").splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 9 or cols[3] != bucket:
            continue
        ts, verb, topic = cols[0], cols[1], cols[4]
        changed, status = cols[5], cols[7]
        notes = "\t".join(cols[8:])          # tolerate stray tabs in notes
        if status not in ("kept", "quarantined"):
            continue
        detail = notes.strip() or f"{changed} article(s)"
        loc = f"{topic}/ " if topic and topic != "(all)" else ""
        by_date.setdefault(ts[:10], []).append(f"- {verb} {loc}— {detail}")
    if not by_date:
        return None
    out = [f"# Change log — {bucket}", ""]
    for date in sorted(by_date, reverse=True):
        out.append(f"## {date}")
        out.extend(by_date[date])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_logs(buckets):
    written = []
    for b in buckets:
        md = derive_log_md(b)
        if md:
            (INTEL_DIR / b / "log.md").write_text(md, encoding="utf-8")
            written.append(b)
    return written


def all_buckets():
    return [d.name for d in sorted(INTEL_DIR.iterdir())
            if d.is_dir() and d.name not in SKIP_DIRS]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="conformance pass, no write")
    g.add_argument("--log", nargs="*", metavar="BUCKET",
                   help="(re)write per-bucket log.md (default: all buckets)")
    args = ap.parse_args()

    if args.check:
        n, lines = check_conformance()
        print("okf=conformant" if n == 0 else f"okf={n}-violations")
        for ln in lines:
            print(ln)
        return 0

    buckets = args.log or all_buckets()
    written = write_logs(buckets)
    print(f"[okf] log.md written for {len(written)} bucket(s): {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
