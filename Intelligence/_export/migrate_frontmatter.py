#!/usr/bin/env python3
"""One-time backfill: add OKF YAML frontmatter to existing articles.

For each article that predates the schema change, derive the frontmatter
fields and prepend the block. The body is left untouched. Idempotent:
articles that already have a frontmatter block are skipped.

Field derivation:
  type        — bucket default (okf_common.BUCKET_TYPE), with overrides
  title       — the H1
  description — first sentence of the `## Summary` section
  bucket/topic— from the path
  source      — the `**Source:**` line's link target or parenthetical
  resource    — the source target if it is an http(s) URL, else blank
  timestamp   — last git commit time of the file (fallback: mtime)
  status      — active
  related     — `## Related` [[ ]] targets resolved to repo-relative paths

Usage:
    python3 Intelligence/_export/migrate_frontmatter.py --bucket github-trends
    python3 Intelligence/_export/migrate_frontmatter.py --all [--dry-run]
"""

import argparse
import datetime as dt
import re
import sys

from okf_common import (INTEL_DIR, build_slug_index, default_type,
                        emit_frontmatter, git_timestamp, iter_articles,
                        split_frontmatter)


def first_sentence(body):
    m = re.search(r"(?ms)^##\s+Summary\s*\n+(.+?)(?:\n\s*\n|\n##\s)", body)
    if not m:
        return ""
    para = " ".join(m.group(1).split())
    cut = re.search(r"\.\s", para)
    return (para[:cut.start() + 1] if cut else para).strip()


def extract_title(body):
    m = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    return m.group(1).strip() if m else ""


def extract_source(body):
    m = re.search(r"(?m)^\*\*Source:\*\*\s*(.+?)\s*$", body)
    if not m:
        return "", ""
    raw = m.group(1).strip()
    link = re.search(r"\[[^\]]*\]\(([^)]+)\)", raw)
    target = link.group(1).strip() if link else raw.strip("() ")
    resource = target if target.startswith("http") else ""
    return target, resource


def extract_related(body, bucket, slug_index):
    rels = []
    m = re.search(r"(?ms)^##\s+Related\s*\n(.+?)(?:\n##\s|\Z)", body)
    if not m:
        return rels
    for link in re.findall(r"\[\[([^\]]+)\]\]", m.group(1)):
        slug = link.split("|")[0].split("#")[0].strip().lstrip("./")
        slug = slug.rsplit("/", 1)[-1].removesuffix(".md")
        candidates = slug_index.get(slug, [])
        if not candidates:
            continue
        same = [c for c in candidates if c.split("/")[0] == bucket]
        chosen = (same or candidates)[0]
        if chosen not in rels:
            rels.append(chosen)
    return rels


def build_frontmatter(bucket, topic, path, slug_index):
    body = path.read_text(encoding="utf-8", errors="replace")
    slug = path.stem
    source, resource = extract_source(body)
    ts = git_timestamp(path)
    if not ts:
        ts = dt.datetime.utcfromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = {
        "type": default_type(bucket, slug),
        "title": extract_title(body) or slug.replace("-", " ").title(),
        "description": first_sentence(body),
        "bucket": bucket,
        "topic": topic,
        "tags": [],
        "source": source,
        "resource": resource,
        "timestamp": ts,
        "status": "active",
        "related": extract_related(body, bucket, slug_index),
    }
    return fm, body


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--bucket", help="migrate one bucket")
    g.add_argument("--all", action="store_true", help="migrate every bucket")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    slug_index = build_slug_index()
    migrated, skipped = 0, 0
    for bucket, topic, path in iter_articles(only_bucket=None if args.all else args.bucket):
        text = path.read_text(encoding="utf-8", errors="replace")
        existing, _ = split_frontmatter(text)
        if existing is not None:
            skipped += 1
            continue
        fm, body = build_frontmatter(bucket, topic, path, slug_index)
        rel = path.relative_to(INTEL_DIR)
        if args.dry_run:
            print(f"[migrate] would write {rel}  type={fm['type']} related={len(fm['related'])}")
        else:
            path.write_text(emit_frontmatter(fm) + "\n" + body, encoding="utf-8")
            print(f"[migrate] {rel}  type={fm['type']} related={len(fm['related'])}")
        migrated += 1

    print(f"[migrate] done: {migrated} migrated, {skipped} already had frontmatter"
          + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
