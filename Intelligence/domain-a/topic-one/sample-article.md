---
type: reference
title: Sample article — coordination overhead in software teams
description: Smaller teams ship faster than larger ones because the number of coordination edges grows quadratically with team size, while output grows roughly linearly.
bucket: domain-a
topic: topic-one
tags: []
source: https://example.com/small-teams-ship-faster
resource: https://example.com/small-teams-ship-faster
timestamp: 2026-05-28T11:25:51Z
status: active
related:
  - domain-a/topic-two/another-article.md
---

# Sample article — coordination overhead in software teams

**Source:** [How small teams ship faster than large ones](https://example.com/small-teams-ship-faster)
**Author:** J. Doe
**Captured:** 2026-04-22

---

## Summary

Smaller teams ship faster than larger ones because the number of
coordination edges grows quadratically with team size, while output
grows roughly linearly. The effect is strongest on shared-code-path
work and weakest on parallelisable surfaces.

## The coordination-edge argument

A team of N members has N·(N−1)/2 pairwise channels, each of which
carries some context-syncing cost (source: clipping-one.md). Doubling
team size more than triples the coordination surface, so per-engineer
output drops as the team grows (source: clipping-one.md).

A 2024 internal study at a large tech company found teams of 4–6
produced roughly twice the merged-PR rate per engineer of teams of
12+ (source: clipping-one.md). The original study is not linked from
the clipping, so the figure should be treated as second-hand
(source: needs-verification).

![[image-one.png]]

## When large teams win

The same source concedes one counter-case: when the work is genuinely
parallelisable across independent surfaces — e.g. a localisation
sweep, or a per-region rollout — large teams can win by avoiding the
shared-state contention entirely (source: clipping-one.md).

A second source disagrees: the "premature abstraction" piece argues
that coordination cost is a symptom, not the cause, and that the real
driver is shared-mutable-state in the codebase rather than team size
(source: clipping-two.md). **Unresolved** — the two framings may be
compatible (team size is the proxy, shared state is the mechanism)
but neither source spells that out.

## Key Takeaways

- Coordination edges grow with N², output grows with N (source: clipping-one.md).
- The per-engineer productivity penalty kicks in around 8+ engineers on shared code (source: clipping-one.md).
- Parallelisable work is exempt from the curve (source: clipping-one.md).
- Whether team size is the cause or merely the proxy is unresolved across the available sources.

## Related

- [[../topic-two/another-article]] — companion view on abstraction cost, which is one of the cited counter-arguments above.
