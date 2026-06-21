#!/usr/bin/env python3
"""Emit the wiki as a portable OKF (Open Knowledge Format) bundle.

A bundle is a directory of markdown files: articles carry their OKF
frontmatter, every folder has an `index.md` router, each bucket carries a
derived `log.md` changelog, and links resolve without Obsidian. Atlas
private zones (_episodes, _eval, _search, _export, _unsorted, log.tsv)
are never included.

Usage:
    python3 Intelligence/_export/export_okf.py                 # whole wiki
    python3 Intelligence/_export/export_okf.py github-trends   # one bucket
    python3 Intelligence/_export/export_okf.py --out /tmp/okf --tar
    python3 Intelligence/_export/export_okf.py --check         # conformance only, no write
"""

import argparse
import os
import re
import shutil
import sys
import tarfile
from pathlib import Path

from okf_common import (EXPORT_DIR, INDEX_FILES, INTEL_DIR, SKIP_DIRS,
                        build_slug_index, iter_articles, split_frontmatter)

LOG_TSV = INTEL_DIR / "log.tsv"


# ---------------------------------------------------------------- conformance

def check_conformance(only_buckets=None):
    """Return (violations:int, lines:list[str]) without writing anything."""
    missing_type = []
    unresolved = []
    for bucket, _topic, path in iter_articles():
        if only_buckets and bucket not in only_buckets:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        rel = str(path.relative_to(INTEL_DIR))
        if fm is None or "type" not in fm or not fm.get("type"):
            missing_type.append(rel)
            fm = fm or {}
        # frontmatter related: must resolve to real files
        for tgt in fm.get("related", []) if isinstance(fm.get("related"), list) else []:
            if not (INTEL_DIR / tgt).exists():
                unresolved.append(f"{rel} → related:{tgt}")
        # inline relative-path links to .md *inside the wiki* must resolve.
        # Links pointing outside Intelligence/ (e.g. ../../../Resources/… source
        # citations, often deleted post-consolidation) are provenance, not OKF
        # graph edges — skip them.
        for m in re.findall(r"\]\((\.{1,2}/[^)]+\.md)\)", body):
            tgt = (path.parent / m).resolve()
            try:
                tgt.relative_to(INTEL_DIR)
            except ValueError:
                continue  # outside the wiki — not an OKF edge
            if not tgt.exists():
                unresolved.append(f"{rel} → {m}")
    n = len(missing_type) + len(unresolved)
    lines = []
    if missing_type:
        lines.append(f"  missing type ({len(missing_type)}): " + ", ".join(missing_type[:5])
                     + (" …" if len(missing_type) > 5 else ""))
    if unresolved:
        lines.append(f"  unresolved links ({len(unresolved)}): " + ", ".join(unresolved[:5])
                     + (" …" if len(unresolved) > 5 else ""))
    return n, lines


# --------------------------------------------------------------- link rewrite

def rewrite_wikilinks(text, dst_relpath, slug_index):
    """Best-effort `[[ ]]` → relative markdown link for bundle index files.

    Targets that cannot be resolved are left as-is (harmless to OKF
    consumers, still valid for Obsidian).
    """
    dst_dir = os.path.dirname(dst_relpath)

    def repl(m):
        inner = m.group(1)
        target, _, alias = inner.partition("|")
        target = target.strip().strip("./")
        alias = alias.strip() or target.rsplit("/", 1)[-1]
        norm = target.replace("_master-index", "index").replace("_index", "index")
        # path-like target (topic/index, ../other/index): resolve from dst_dir
        if "/" in norm:
            cand = os.path.normpath(os.path.join(dst_dir, norm))
            rel = os.path.relpath(cand, dst_dir)
            return f"[{alias}]({rel}.md)"
        # bare slug → look up its article path, make relative to dst_dir
        hits = slug_index.get(target)
        if hits:
            rel = os.path.relpath(hits[0], dst_dir or ".")
            return f"[{alias}]({rel})"
        return m.group(0)

    return re.sub(r"\[\[([^\]]+)\]\]", repl, text)


# ------------------------------------------------------------------- log.md

def derive_log_md(bucket):
    """Render a per-bucket OKF `log.md` from the central log.tsv rows."""
    if not LOG_TSV.exists():
        return None
    rows = []
    for line in LOG_TSV.read_text(encoding="utf-8").splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 9 or cols[3] != bucket:
            continue
        rows.append(cols)
    if not rows:
        return None
    by_date = {}
    for ts, verb, source, _b, topic, changed, _img, status, notes in rows:
        if status not in ("kept", "quarantined"):
            continue
        date = ts[:10]
        detail = notes.strip() or f"{changed} article(s)"
        loc = f"{topic}/" if topic and topic != "(all)" else ""
        by_date.setdefault(date, []).append(f"- {verb} {loc}— {detail}")
    out = [f"# Change log — {bucket}", ""]
    for date in sorted(by_date, reverse=True):
        out.append(f"## {date}")
        out.extend(by_date[date])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# -------------------------------------------------------------------- export

def export_tree(buckets, out_dir, slug_index):
    out_dir.mkdir(parents=True, exist_ok=True)
    article_count = 0

    for bucket in buckets:
        src_bucket = INTEL_DIR / bucket
        for src in sorted(src_bucket.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(INTEL_DIR)
            # rename folder routers to OKF index.md
            if src.name in ("_master-index.md", "_index.md"):
                rel = rel.with_name("index.md")
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix == ".md":
                text = src.read_text(encoding="utf-8", errors="replace")
                # Rewrite [[wikilinks]] -> relative markdown links in the BUNDLE
                # copy (routers and article bodies alike), so a non-Obsidian
                # consumer can traverse. The vault keeps its [[ ]] untouched.
                text = rewrite_wikilinks(text, str(rel), slug_index)
                if src.name not in INDEX_FILES:
                    article_count += 1
                dst.write_text(text, encoding="utf-8")
            else:
                shutil.copy2(src, dst)        # images and other assets
        log_md = derive_log_md(bucket)
        if log_md:
            (out_dir / bucket / "log.md").write_text(log_md, encoding="utf-8")

    # top-level router
    top = INTEL_DIR / "index.md"
    if top.exists():
        text = rewrite_wikilinks(top.read_text(encoding="utf-8"), "index.md", slug_index)
        (out_dir / "index.md").write_text(text, encoding="utf-8")
    return article_count


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bucket", nargs="?", help="export one bucket (default: whole wiki)")
    ap.add_argument("--out", help="output directory (default: _export/out)")
    ap.add_argument("--tar", action="store_true", help="also emit a .tar.gz of the bundle")
    ap.add_argument("--check", action="store_true", help="conformance only, write nothing")
    args = ap.parse_args()

    if args.check:
        n, lines = check_conformance()        # whole-wiki — refine's rollup
        print("okf=conformant" if n == 0 else f"okf={n}-violations")
        for ln in lines:
            print(ln)
        return 0

    all_buckets = [d.name for d in sorted(INTEL_DIR.iterdir())
                   if d.is_dir() and d.name not in SKIP_DIRS]
    if args.bucket:
        if args.bucket not in all_buckets:
            print(f"[export] no such bucket: {args.bucket}")
            return 1
        buckets = [args.bucket]
    else:
        buckets = all_buckets

    n, lines = check_conformance(only_buckets=buckets)   # scope to what we export
    if n:
        print(f"[export] warning: okf={n}-violations in exported scope (exporting anyway)")
        for ln in lines:
            print(ln)

    out_dir = Path(args.out) if args.out else EXPORT_DIR / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    slug_index = build_slug_index()
    count = export_tree(buckets, out_dir, slug_index)

    print(f"[export] bundle={out_dir} buckets={len(buckets)} articles={count} okf={'conformant' if n == 0 else f'{n}-violations'}")
    if args.tar:
        tar_path = out_dir.with_suffix(".tar.gz")
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(out_dir, arcname=out_dir.name)
        print(f"[export] tarball={tar_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
