---
episode_id: operational-consolidate-2026-01-01T00-00-00Z
kind: operational
verb: consolidate
timestamp: 2026-01-01T00:00:00Z
situation: One web clipping about small-team velocity arrived in Resources/web-clippings/.
intent: Route the clipping to the right bundle/topic and write a cited article.
outcome: success
tags: [domain-a, web-clipping, new-topic]
distilled: false
---

## Situation

A single web clipping discussing why small teams ship faster landed in
`Resources/web-clippings/`. No existing topic in `domain-a` matched it
exactly. (This is a **placeholder** episode demonstrating the schema.)

## Actions

- Compared the clipping against each bundle's `_master-index.md` Scope
  paragraph → routed to `domain-a`.
- No topic fit → created topic `topic-one` with its `_index.md`.
- Wrote the article with inline `(source: clipping-one.md)` citations.
- Updated `topic-one/_index.md` and the bundle `_master-index.md`.

## Outcome

1 article written, 0 quarantined, 0 images. `refine` drift unchanged.

## Insights

When a clipping argues a single thesis with no existing home, creating
a dedicated topic beats forcing it into a loosely-related one — the
routing stays legible for the next run.

## Links

`(source: Resources/web-clippings/clipping-one.md)`,
`(source: domain-a/topic-one/sample-article.md)`
