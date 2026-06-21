#!/usr/bin/env python3
"""Shared helpers for the OKF export/migration tooling.

No third-party dependencies — a minimal frontmatter reader/writer keeps
this runnable on a bare Python 3 (PyYAML is not assumed present, same as
the _search tooling degrades without sentence-transformers).
"""

import re
import subprocess
from pathlib import Path

EXPORT_DIR = Path(__file__).resolve().parent
INTEL_DIR = EXPORT_DIR.parent

# Governance zones: never exported, never migrated.
SKIP_DIRS = {"_episodes", "_eval", "_unsorted", "_search", "_export"}
INDEX_FILES = {"_index.md", "_master-index.md", "index.md"}

# Bucket -> default OKF `type`. Mirrors the *Article type vocabulary*
# table in schema.md. Map YOUR buckets here; unknown buckets fall back
# to DEFAULT_TYPE. (The placeholder boilerplate buckets are illustrative.)
DEFAULT_TYPE = "reference"
BUCKET_TYPE = {
    "domain-a": "reference",
    "domain-b": "reference",
}


def default_type(bucket, slug):
    """Default `type` for an article. Extend with per-article overrides."""
    return BUCKET_TYPE.get(bucket, DEFAULT_TYPE)


def iter_articles(root=INTEL_DIR, only_bucket=None):
    """Yield (bucket, topic, path) for every article file in the wiki."""
    for bucket_dir in sorted(root.iterdir()):
        if not bucket_dir.is_dir() or bucket_dir.name in SKIP_DIRS:
            continue
        if only_bucket and bucket_dir.name != only_bucket:
            continue
        for path in sorted(bucket_dir.rglob("*.md")):
            if path.name in INDEX_FILES:
                continue
            rel = path.relative_to(root)
            topic = rel.parts[1] if len(rel.parts) > 2 else ""
            yield bucket_dir.name, topic, path


def split_frontmatter(text):
    """Return (frontmatter_dict_or_None, body). Body excludes the block.

    Minimal parser: scalars `key: value` and simple block lists
    (`key:` then `  - item` lines). Sufficient for the keys this tooling
    emits; not a general YAML implementation.
    """
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    block = text[4:end]
    body = text[end + 4:].lstrip("\n")
    fm, key = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                fm[key] = []          # may become a block list
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


def emit_frontmatter(fm):
    """Render an ordered frontmatter block (trailing newline included)."""
    order = ["type", "title", "description", "bucket", "topic", "tags",
             "source", "resource", "timestamp", "status", "related"]
    lines = ["---"]
    for k in order:
        if k not in fm:
            continue
        v = fm[k]
        if k in ("tags",) and isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        elif k == "related" and isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
            if not v:
                lines[-1] = f"{k}: []"
        else:
            lines.append(f"{k}: {v}" if v != "" else f"{k}:")
    lines.append("---")
    return "\n".join(lines) + "\n"


def git_timestamp(path):
    """Last git commit time of a file as ISO 8601 UTC, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format-local:%Y-%m-%dT%H:%M:%SZ",
             "--", str(path)],
            cwd=INTEL_DIR, capture_output=True, text=True,
            env={"TZ": "UTC", "PATH": __import__("os").environ.get("PATH", "")},
        )
        ts = out.stdout.strip()
        return ts or None
    except Exception:
        return None


def build_slug_index(root=INTEL_DIR):
    """Map article slug -> list of repo-relative paths (for [[ ]] resolution)."""
    idx = {}
    for _bucket, _topic, path in iter_articles(root):
        idx.setdefault(path.stem, []).append(str(path.relative_to(root)))
    return idx
