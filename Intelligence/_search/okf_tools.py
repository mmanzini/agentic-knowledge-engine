#!/usr/bin/env python3
"""In-place OKF tooling for the live wiki — no export snapshot.

Each bundle directory is OKF-conformant in place: `index.md` routers, articles
with `type` frontmatter + a `related:` graph, and a derived `log.md`. This
script maintains the two derived/checked pieces:

  --check            conformance pass (strict-YAML frontmatter parses; every
                     article has `type`; related:/relative links resolve; no
                     legacy v0.1 `timestamp:`/`source:` fields; generated/
                     verified shapes valid). Prints `okf=conformant` or
                     `okf=<N>-violations`. Used by the `refine` verb.
  --log [bundle ...] (re)write `Intelligence/<bundle>/log.md` from log.tsv
                     for the named bundles (default: all). Run by the
                     consolidate auto-chain for touched bundles.

Requires PyYAML (strict frontmatter parsing per OKF v0.2 — invalid YAML is a
conformance violation). Governance zones (`_episodes/ _eval/ _search/
_unsorted/`) are never bundles and are skipped.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

SEARCH_DIR = Path(__file__).resolve().parent
INTEL_DIR = SEARCH_DIR.parent
LOG_TSV = INTEL_DIR / "log.tsv"

SKIP_DIRS = {"_episodes", "_eval", "_unsorted", "_search", "_export"}
INDEX_FILES = {"index.md", "_index.md", "_master-index.md", "log.md"}


def iter_articles(only_bundle=None):
    """Yield (bundle, topic, path) for every article (non-router) file."""
    for bundle_dir in sorted(INTEL_DIR.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name in SKIP_DIRS:
            continue
        if only_bundle and bundle_dir.name != only_bundle:
            continue
        for path in sorted(bundle_dir.rglob("*.md")):
            if path.name in INDEX_FILES:
                continue
            rel = path.relative_to(INTEL_DIR)
            topic = rel.parts[1] if len(rel.parts) > 2 else ""
            yield bundle_dir.name, topic, path


def split_frontmatter(text):
    """Return (frontmatter_dict_or_None, body, error_or_None).

    Strict: the block between the `---` fences must be valid YAML mapping
    (PyYAML safe_load). error is None (ok), "missing" (no frontmatter
    fences), or "invalid: <reason>" (unparseable / non-mapping).
    """
    if not text.startswith("---\n"):
        return None, text, "missing"
    end = text.find("\n---", 4)
    if end == -1:
        return None, text, "missing"
    block, body = text[4:end], text[end + 4:].lstrip("\n")
    try:
        fm = yaml.safe_load(block)
    except yaml.YAMLError as e:
        reason = str(e).splitlines()[0] if str(e) else e.__class__.__name__
        return None, body, f"invalid: {reason}"
    if not isinstance(fm, dict):
        return None, body, "invalid: frontmatter is not a YAML mapping"
    return fm, body, None


# ---------------------------------------------------------------- conformance

def _bad_actor_event(ev):
    """True when a generated/verified event lacks a non-empty `by`."""
    return not (isinstance(ev, dict) and ev.get("by"))


def check_conformance(only_bundles=None):
    """Return (violations:int, lines:list[str]) without writing anything."""
    missing_type, unresolved = [], []
    invalid_yaml, legacy_v01, bad_shape = [], [], []
    for bundle, _topic, path in iter_articles():
        if only_bundles and bundle not in only_bundles:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body, err = split_frontmatter(text)
        rel = str(path.relative_to(INTEL_DIR))
        if err and err.startswith("invalid"):
            invalid_yaml.append(f"{rel} ({err})")
        if fm is None or not fm.get("type"):
            missing_type.append(rel)
            fm = fm or {}
        # v0.1 leftovers: `timestamp:` scalar / `source:` scalar were replaced
        # by generated:{by,at} and sources:[] in the v0.2 migration.
        if "timestamp" in fm or "source" in fm:
            legacy_v01.append(rel)
        # v0.2 trust-field shapes: generated needs `by`; verified is an event
        # mapping or a list of event mappings, each needing `by`.
        if "generated" in fm and _bad_actor_event(fm["generated"]):
            bad_shape.append(f"{rel} → generated")
        if "verified" in fm:
            v = fm["verified"]
            events = v if isinstance(v, list) else [v]
            if any(_bad_actor_event(ev) for ev in events):
                bad_shape.append(f"{rel} → verified")
        rel_list = fm.get("related")
        for tgt in rel_list if isinstance(rel_list, list) else []:
            if not (INTEL_DIR / str(tgt)).exists():
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
    n = (len(missing_type) + len(unresolved) + len(invalid_yaml)
         + len(legacy_v01) + len(bad_shape))
    lines = []
    for label, items in (("missing type", missing_type),
                         ("unresolved links", unresolved),
                         ("invalid yaml", invalid_yaml),
                         ("legacy v0.1 fields", legacy_v01),
                         ("bad trust-field shape", bad_shape)):
        if items:
            lines.append(f"  {label} ({len(items)}): "
                         + ", ".join(items[:5]) + (" …" if len(items) > 5 else ""))
    return n, lines


# ------------------------------------------------------------------- log.md

def derive_log_md(bundle):
    """Render a per-bundle OKF `log.md` from the central log.tsv rows."""
    if not LOG_TSV.exists():
        return None
    by_date = {}
    for line in LOG_TSV.read_text(encoding="utf-8").splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) < 9 or cols[3] != bundle:
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
    out = [f"# Change log — {bundle}", ""]
    for date in sorted(by_date, reverse=True):
        out.append(f"## {date}")
        out.extend(by_date[date])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_logs(bundles):
    written = []
    for b in bundles:
        md = derive_log_md(b)
        if md:
            (INTEL_DIR / b / "log.md").write_text(md, encoding="utf-8")
            written.append(b)
    return written


def all_bundles():
    return [d.name for d in sorted(INTEL_DIR.iterdir())
            if d.is_dir() and d.name not in SKIP_DIRS]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="conformance pass, no write")
    g.add_argument("--log", nargs="*", metavar="BUNDLE",
                   help="(re)write per-bundle log.md (default: all bundles)")
    args = ap.parse_args()

    if args.check:
        n, lines = check_conformance()
        print("okf=conformant" if n == 0 else f"okf={n}-violations")
        for ln in lines:
            print(ln)
        return 0

    bundles = args.log or all_bundles()
    written = write_logs(bundles)
    print(f"[okf] log.md written for {len(written)} bundle(s): {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
