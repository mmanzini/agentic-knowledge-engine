#!/usr/bin/env python3
"""Build the tier-2 hybrid search index over Intelligence/ articles.

Walks Intelligence/<bucket>/<topic>/*.md, chunks article bodies per
section, and writes a SQLite database (index.db, gitignored) with:

  - an FTS5 table for keyword search (ships with the system sqlite3)
  - an embeddings table via sentence-transformers (all-MiniLM-L6-v2,
    local, free) — if the model is unavailable the build degrades
    gracefully to FTS-only and says so

Incremental: files whose content hash is unchanged are skipped.

Usage:
    python3 Intelligence/_search/build_index.py [--rebuild]
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

SEARCH_DIR = Path(__file__).resolve().parent
INTEL_DIR = SEARCH_DIR.parent
DB_PATH = SEARCH_DIR / "index.db"

# Governance zones and index files are routing overhead, not articles.
SKIP_DIRS = {"_episodes", "_eval", "_unsorted", "_search", "_export"}
SKIP_FILES = {"_index.md", "_master-index.md", "index.md"}

EMBED_MODEL = "all-MiniLM-L6-v2"


def iter_articles():
    """Yield (bucket, topic, path) for every article file."""
    for bucket_dir in sorted(INTEL_DIR.iterdir()):
        if not bucket_dir.is_dir() or bucket_dir.name in SKIP_DIRS:
            continue
        for path in sorted(bucket_dir.rglob("*.md")):
            if path.name in SKIP_FILES:
                continue
            rel = path.relative_to(INTEL_DIR)
            topic = rel.parts[1] if len(rel.parts) > 2 else ""
            yield bucket_dir.name, topic, path


def parse_frontmatter(text):
    """Return (facets:dict, body) — minimal reader for OKF frontmatter.

    Pulls type/title/description (scalars) and tags (inline list). Not a
    general YAML parser; matches what consolidate/migration emit.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block, body = text[4:end], text[end + 4:].lstrip("\n")
    fm = {}
    for line in block.splitlines():
        m = re.match(r"^(type|title|description|tags):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "tags":
            inner = val.strip("[]").strip()
            fm["tags"] = " ".join(x.strip() for x in inner.split(",") if x.strip())
        else:
            fm[key] = val
    return fm, body


def facet_chunk(facets):
    """A leading synthetic chunk so FTS/embeddings match frontmatter facets."""
    parts = []
    if facets.get("title"):
        parts.append(facets["title"])
    if facets.get("description"):
        parts.append(facets["description"])
    tail = []
    if facets.get("type"):
        tail.append(f"type:{facets['type']}")
    if facets.get("tags"):
        tail.append(f"tags: {facets['tags']}")
    if tail:
        parts.append(" ".join(tail))
    return "\n".join(parts).strip()


def chunk_article(text):
    """Split an article body into per-section chunks.

    Sections are delimited by `## ` headings; the preamble (title +
    metadata) is its own chunk. Oversized sections are split on blank
    lines at ~1500 chars so embeddings stay focused.
    """
    sections = re.split(r"(?m)^(?=## )", text)
    chunks = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if len(sec) <= 1500:
            chunks.append(sec)
            continue
        buf = ""
        for para in sec.split("\n\n"):
            if buf and len(buf) + len(para) > 1500:
                chunks.append(buf.strip())
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            chunks.append(buf.strip())
    return chunks


def load_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(EMBED_MODEL)
    except Exception as exc:  # noqa: BLE001 — any failure means FTS-only
        print(f"[build_index] semantic tier unavailable ({exc.__class__.__name__}: {exc})")
        print("[build_index] building FTS-only index. To enable semantic search:")
        print("[build_index]     pip3 install sentence-transformers")
        return None


def ensure_schema(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,        -- relative to Intelligence/
            bucket TEXT NOT NULL,
            topic TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedded INTEGER NOT NULL DEFAULT 0,
            type TEXT DEFAULT '',         -- OKF frontmatter facets
            tags TEXT DEFAULT '',
            title TEXT DEFAULT '',
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
            seq INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding BLOB                 -- float32 vector; NULL in FTS-only builds
        );
        CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text, content='chunks', content_rowid='id'
        );
        """
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="drop and rebuild from scratch")
    args = parser.parse_args()

    if args.rebuild and DB_PATH.exists():
        DB_PATH.unlink()

    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    ensure_schema(db)

    embedder = load_embedder()

    known = {row[0]: (row[1], row[2]) for row in db.execute("SELECT path, content_hash, embedded FROM files")}
    seen, added, skipped = set(), 0, 0
    pending = []  # (rel_path, bucket, topic, content_hash, facets, chunks)

    for bucket, topic, path in iter_articles():
        rel = str(path.relative_to(INTEL_DIR))
        seen.add(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        prev = known.get(rel)
        # Unchanged file is current unless it lacks embeddings we can now add.
        if prev and prev[0] == content_hash and (prev[1] == 1 or embedder is None):
            skipped += 1
            continue
        facets, body = parse_frontmatter(text)
        chunks = chunk_article(body)
        fc = facet_chunk(facets)
        if fc:
            chunks = [fc] + chunks
        pending.append((rel, bucket, topic, content_hash, facets, chunks))

    # Remove rows for deleted files so search never routes to a gone article.
    removed = set(known) - seen
    for rel in removed:
        db.execute(
            "INSERT INTO chunks_fts(chunks_fts, rowid, text) "
            "SELECT 'delete', id, text FROM chunks WHERE path = ?", (rel,))
        db.execute("DELETE FROM files WHERE path = ?", (rel,))

    for rel, bucket, topic, content_hash, facets, chunks in pending:
        db.execute(
            "INSERT INTO chunks_fts(chunks_fts, rowid, text) "
            "SELECT 'delete', id, text FROM chunks WHERE path = ?", (rel,))
        db.execute("DELETE FROM files WHERE path = ?", (rel,))
        vectors = [None] * len(chunks)
        if embedder is not None and chunks:
            import numpy as np
            embs = embedder.encode(chunks, normalize_embeddings=True)
            vectors = [np.asarray(v, dtype="float32").tobytes() for v in embs]
        db.execute(
            "INSERT INTO files (path, bucket, topic, content_hash, embedded, type, tags, title, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rel, bucket, topic, content_hash, 1 if embedder is not None else 0,
             facets.get("type", ""), facets.get("tags", ""),
             facets.get("title", ""), facets.get("description", "")))
        for seq, (chunk, vec) in enumerate(zip(chunks, vectors)):
            cur = db.execute(
                "INSERT INTO chunks (path, seq, text, embedding) VALUES (?, ?, ?, ?)",
                (rel, seq, chunk, vec))
            db.execute(
                "INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)", (cur.lastrowid, chunk))
        added += 1

    db.commit()
    total = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    nchunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    mode = "hybrid (FTS5 + embeddings)" if embedder is not None else "FTS-only"
    print(f"[build_index] mode={mode} files={total} chunks={nchunks} "
          f"indexed={added} unchanged={skipped} removed={len(removed)}")
    print(f"[build_index] db={DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
