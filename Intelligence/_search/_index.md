# _search — tier-2 hybrid recall zone

Governance zone (like `_eval/` and `_unsorted/`), **not a bucket**: the
`query` bucket-walk ignores it and no articles live here. It holds the
local hybrid search index and its tooling — `build_index.py` (indexer),
`search.py` (query CLI), and the gitignored `index.db` build artifact.
The agent uses it only at **tier 2** of the query verb: when the tier-1
index walk misses or the question is fuzzy/cross-cutting, run
`python3 Intelligence/_search/search.py "<query>" --json` and treat the
hits as **routing pointers** — open the pointed articles, read them, and
cite them per the schema. Search output itself is never a citation
source. The index is rebuilt by the consolidate auto-chain
(`build_index.py`, incremental) so it tracks the wiki without manual
upkeep; `refine` reports staleness in its `notes`.
