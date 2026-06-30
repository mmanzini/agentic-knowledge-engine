#!/usr/bin/env python3
"""Tier-2 hybrid search over the Intelligence/ wiki.

Combines FTS5 keyword search with cosine similarity over local
embeddings (when the index was built with them), merged by
reciprocal-rank fusion. Results are POINTERS to articles — the agent
must open and read the pointed articles and cite them per the schema;
search output itself is never a citation source.

Usage:
    python3 Intelligence/_search/search.py "your query" [--top N] [--json]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

SEARCH_DIR = Path(__file__).resolve().parent
DB_PATH = SEARCH_DIR / "index.db"

RRF_K = 60  # standard reciprocal-rank-fusion constant


def fts_query(db, query, limit):
    """Keyword search; returns ranked chunk ids."""
    # Quote terms so user punctuation can't break FTS5 query syntax.
    terms = re.findall(r"\w+", query)
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    rows = db.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
        (match, limit)).fetchall()
    return [r[0] for r in rows]


def semantic_query(db, query, limit):
    """Embedding search; returns ranked chunk ids, or [] if unavailable."""
    has_embeddings = db.execute(
        "SELECT 1 FROM chunks WHERE embedding IS NOT NULL LIMIT 1").fetchone()
    if not has_embeddings:
        return []
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except Exception:
        return []
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qvec = np.asarray(model.encode([query], normalize_embeddings=True)[0], dtype="float32")
    ids, vecs = [], []
    for cid, blob in db.execute("SELECT id, embedding FROM chunks WHERE embedding IS NOT NULL"):
        ids.append(cid)
        vecs.append(np.frombuffer(blob, dtype="float32"))
    sims = np.stack(vecs) @ qvec  # normalized → dot product = cosine
    order = np.argsort(-sims)[:limit]
    return [ids[i] for i in order]


def rrf_merge(rankings, top):
    """Reciprocal-rank fusion across ranked id lists."""
    scores = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)[:top]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=8, help="max results (default 8)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("[search] no index found — run: python3 Intelligence/_search/build_index.py",
              file=sys.stderr)
        return 1

    db = sqlite3.connect(DB_PATH)
    pool = max(args.top * 4, 20)
    keyword = fts_query(db, args.query, pool)
    semantic = semantic_query(db, args.query, pool)
    merged = rrf_merge([r for r in (keyword, semantic) if r], args.top)

    results = []
    seen_articles = set()
    for cid in merged:
        row = db.execute(
            "SELECT c.text, c.path, f.bundle, f.topic FROM chunks c "
            "JOIN files f ON f.path = c.path WHERE c.id = ?", (cid,)).fetchone()
        if row is None:
            continue
        text, path, bundle, topic = row
        snippet = " ".join(text.split())[:200]
        results.append({"article": path, "bundle": bundle, "topic": topic,
                        "snippet": snippet})
        seen_articles.add(path)

    mode = "hybrid" if semantic else "keyword-only"
    if args.json:
        print(json.dumps({"query": args.query, "mode": mode, "results": results},
                         ensure_ascii=False, indent=2))
    elif not results:
        print(f"[search] mode={mode} — no matches. The answer is likely not in the wiki.")
    else:
        print(f"[search] mode={mode} — {len(results)} chunks across "
              f"{len(seen_articles)} articles (pointers — read and cite the articles):")
        for r in results:
            print(f"  {r['article']} — {r['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
