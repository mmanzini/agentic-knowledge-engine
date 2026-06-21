# _export — OKF bundle emission zone

Governance zone (like `_search/`, `_eval/` and `_unsorted/`), **not a
bucket**: the `query` bucket-walk ignores it and no articles live here.
It holds the tooling that emits the wiki as a portable **Open Knowledge
Format (OKF)** bundle, and the one-time frontmatter backfill.

- `export_okf.py` — the `export` verb's engine. Emits an OKF bundle from
  the wiki (a bucket or the whole thing): copies conformant articles,
  renames `_master-index.md`/`_index.md` to OKF `index.md`, derives a
  per-bucket `log.md` from `Intelligence/log.tsv`, rewrites `[[ ]]` to
  relative markdown links in the bundle copy, keeps the
  `related:`/relative-path graph, and strips private zones (`_episodes/`,
  `_eval/`, `_search/`, `_export/`, `_unsorted/`, `log.tsv`). `--check`
  runs the no-write conformance pass that `refine` reports as `okf=…`;
  `--tar` also emits a tarball. Output defaults to
  `Intelligence/_export/out/` (gitignored).
- `migrate_frontmatter.py` — one-time backfill that adds the OKF YAML
  frontmatter block to existing articles that predate the schema.
  Idempotent: articles that already have frontmatter are skipped. Run
  per bucket (`--bucket <name>`) or all at once (`--all`); the body is
  left untouched.
- `okf_common.py` — shared helpers (frontmatter read/write, the
  bucket→`type` map you customise, article iteration). No third-party
  deps.

Neither script is part of the `consolidate` auto-chain. `export` runs on
user request; the migration runs once during the OKF adoption.
