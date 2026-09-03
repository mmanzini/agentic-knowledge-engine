# Handover — personal website migration off Wix

**Date:** 2026-08-12 · **Status:** site live, registrar transfer in flight
**Repo:** `~/Documents/repos/personal-portfolio-website` (private, `mmanzini/personal-portfolio-website`)
**Live:** https://www.maxmanzini.com

The repo `README.md` is the source of truth for architecture, the `/admin`
setup, DNS values and rollback. **Read it first — do not duplicate it here.**
This document only covers what the README cannot: what is mid-flight, what was
decided and why, and the traps that cost time.

---

## Where things stand

| Thing | State |
|---|---|
| Site | Live on Vercel. Lighthouse 97 / 100 / 100 / 92, CLS 0, 231 KiB |
| `www.maxmanzini.com` | Canonical, 200 |
| `maxmanzini.com`, both `massimilianomanzini.com` hosts | 308 → canonical |
| Blog | 3 essays from Atlas, markdown collection, `/blog` archive |
| `/admin` | Sveltia CMS, working, full round-trip verified |
| DNS | Hosted at **Wix** (A + CNAME → Vercel) |
| `maxmanzini.com` registrar | **`pendingTransfer` Wix → Porkbun**, started 2026-08-12 20:10Z |
| `massimilianomanzini.com` registrar | Wix, `clientTransferProhibited` |

---

## The one thing in flight

`maxmanzini.com` is mid-transfer to Porkbun. Registry status is
`pendingTransfer`, nameservers still `ns0/ns1.wixdns.net`.

**When it completes, immediately set the nameservers at Porkbun to:**

```
susan.ns.cloudflare.com
todd.ns.cloudflare.com
```

A Cloudflare zone for `maxmanzini.com` is already staged and **verified** — both
nameservers were queried directly and return byte-identical answers to what Wix
serves today. So the nameserver flip is a swap between two servers giving the
same response, not a leap.

**Why this is timed:** between the transfer completing and the nameservers
changing, DNS is answered by Wix for a domain Wix no longer manages. They are
under no obligation to keep doing it. Do not leave the gap open.

Verify after:

```bash
dig +short NS maxmanzini.com                    # -> susan/todd.ns.cloudflare.com
dig +short A maxmanzini.com                     # -> 216.198.79.1
curl -sI https://www.maxmanzini.com/ | head -1  # -> 200
```

---

## Decisions taken, and why

Recording the reasoning because several of these look wrong without it.

- **Astro, not the shipped runtime.** The zip was a Claude Design export running
  on a proprietary client-side runtime — no static HTML, no SEO, ~370 KB of JS.
  Ported to Astro; design-system token CSS reused verbatim, only `Icons` and
  `Button` reimplemented (transcribed out of the compiled bundle).
- **Hero stays company-agnostic.** Max's call, so it survives the Xlinq move.
- **Canonical is `maxmanzini.com`**, not the longer domain, despite the latter
  holding the existing SEO. 308s carry it across.
- **DNS stayed at Wix.** The plan was Cloudflare nameservers. Wix does not permit
  nameserver changes on domains it registers — its DNS page literally says "NS
  records are not editable". Hence the registrar transfer now under way.
- **Cloudflare Registrar is not usable as the first hop.** It requires the domain
  to already be on Cloudflare nameservers, which Wix blocks. Circular. Porkbun
  first; Cloudflare Registrar becomes possible later if ever wanted.
- **The 2017–2021 / 2017–2018 timeline rows overlap on purpose.** Two legal
  entities during the merger, and Max held Head of UX continuously. The CV shows
  it the same way. There is a code comment saying so. **Do not "fix" it.**
- **Fonts are licensed.** GT Walsheim wero — Max confirmed. woff2 only; do not
  restore the `.ttf` files from the export.
- **CMS config was deliberately stripped.** `view_filters`, `summary` and
  `sortable_fields` were removed after they hung the collection load. They were
  unrequested conveniences. Do not add them back speculatively.

---

## Traps that cost real time

Each of these presented as a success and failed silently.

1. **Cloudflare's "Deploy to Cloudflare" button created the worker repo without
   `src/`.** It shipped the Hello World starter and reported success. Source was
   pushed manually and deployed with `wrangler deploy`. If the worker is ever
   redeployed, check `https://sveltia-cms-auth.manzini-m.workers.dev/` returns
   **404**, not `200 Hello world`.
2. **Saving worker variables creates a version but does not deploy it.** The live
   version stayed on the pre-secrets one, so the error message never changed
   after saving. Fix: `wrangler versions deploy <id>@100%`. This will recur on
   any secret rotation.
3. **Local DNS caches lied twice.** Both times the site was correct and the
   machine running the checks had stale records. Always confirm against a public
   resolver or `curl --resolve` before believing a failure.
4. **`curl -I` sends HEAD**, and the auth worker only handles GET — HEAD returns
   404 from its fall-through. Not a fault.
5. **The CMS writes `image: ''`, not an absent key.** `??` does not catch empty
   strings, so every post without a hero image had a broken `og:image`. Fixed in
   the schema. Watch for the same shape in any new optional field.

---

## Changed since this was written (2026-08-13)

The README covers all of it; this is just the pointer.

- **Mobile nav fixes.** The bar takes a ground while the drawer is open, and the
  burger becomes an X. Journey rows now read title → company → period →
  description on mobile.
- **Favicon** is the recovered Wix mark (`public/favicon.png`); `favicon.svg` is
  gone.
- **Experience, projects and recommendations are CMS collections** now, one
  `.yml` per entry under `src/content/`, ordered by an `order` field rather than
  a date sort. The hardcoded arrays in `index.astro` are gone.
- **LinkedIn URLs were wrong sitewide** — the handle is `maxmanzini`, not
  `massimilianomanzini`. Fixed in three places.
- **Umami analytics**, free tier, proxied through `/s.js` and `/api/send` via
  `vercel.json` rewrites so it is same-origin and survives blockers. Cookieless,
  so still no consent banner. Website ID is in `Base.astro` and is public by
  design.

## Open items

**Now**
- Finish the `maxmanzini.com` transfer → set Cloudflare nameservers → verify.

**~8 October** (60-day ICANN lock from a 2026-08-09 registrant change)
- Repeat the whole transfer for `massimilianomanzini.com`. Stage its Cloudflare
  zone only when ready — pending zones get purged if left too long.

**~~26 August~~ → after 8 October** — Wix Premium cancellation, **deferred
2026-08-13, deliberately. Do not bring it forward.**

The original date was wrong because it ignored DNS delegation. Both apexes still
delegate from `ns0/ns1.wixdns.net`, so Wix sits in the resolution path for the
*live canonical site*, not just the old domain — cancelling while that is true
risks taking the site down. It only becomes safe once nothing resolves through
Wix, which is after the `massimilianomanzini.com` transfer completes.

Also note cancelling removes the rollback below, and Wix does not prorate
refunds after 14 days, so going early saves nothing if the plan is already paid.
The deciding question is the plan's **renewal date** — if it renews before
October, cancel a few days after the `maxmanzini.com` nameserver flip (when only
the old domain is exposed) and test both domains within minutes.

- Rollback while Premium is live: A record → `185.230.63.171`,
  `www` CNAME → `cdn1.wixdns.net`.

**1 September**
- Xlinq starts. The `jobs` array is **gone** — experience is now a CMS
  collection. Edit the Van Lanschot Kempen entry in `/admin` (or
  `src/content/jobs/`) to close the period at 2026, and add the new role with a
  lower `order` so it sits above. Hero needs no change.

**Whenever**
- Submit the site to Google Search Console, add
  `https://www.maxmanzini.com/sitemap-index.xml`. The 308s carry ranking from
  the old domain but Search Console makes it faster and surfaces problems.
- More essays exist in Atlas beyond the three published — see
  `Resources/Projects/articles-and-essays/` and ledger rows T001/T002/T039.
  The Heist Framework essay (`Resources/documents/frameworks/Way of Working/`)
  is the strongest unpublished piece; needs the employer anonymised.

---

## Accounts and access

| | |
|---|---|
| GitHub | `mmanzini`, `gh` CLI authenticated locally |
| Vercel | Hobby, personal account. Project `personal-portfolio-website` |
| Cloudflare | `manzini.m@gmail.com`. Worker + staged `maxmanzini.com` zone. `wrangler` authenticated locally |
| Porkbun | new, transfer in progress |
| Wix | **the account owning the domains is NOT the one the Wix MCP connects to** — that one holds `makewithresonance.com` (Cristina Mandolesi). Check before touching billing or DNS. |

**Vercel Hobby was blocked for "fair use" on 2026-08-12**, before this project
existed — a previously hosted MCP server is the likely cause. Unblocked
manually. If it recurs the site goes down with the account. Keep heavy workloads
off it. Cloudflare Pages would be ~10 minutes if ever needed: the build is
static and only `vercel.json` needs porting to `_headers` / `_redirects`.

No secrets in this document or the repo. Worker credentials live in Cloudflare;
the Porkbun auth code is single-use and expires with the transfer.

---

## Suggested skills for the next session

- **`obsidian:obsidian-cli`** — if updating Atlas task state (`Tasks/ledger.md`
  row T013, `TASKS.md`) as items close.
- **`wrangler`** — before any Cloudflare Worker command; the versions-vs-
  deployments distinction in trap 2 is exactly what it guards against.
- **`code-review`** — before merging any substantial change to the site.
- **`humanizer`** or `Resources/personal/writing-rules.md` — if drafting new blog
  posts. Max's voice rules are explicit: no em dashes, no "leverage/showcase/
  pivotal", UK English, first person, opinions stated plainly.

Not needed: `artifact-design`, `dataviz`, anything front-end-generative. The
design is fixed and must not be re-invented.
