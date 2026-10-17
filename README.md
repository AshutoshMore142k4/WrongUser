# Nosy

> **Suspect at the seams. Believe only red.**

Nosy is an agent skill that signs up as a second user and tries to read your first user's data.

If it gets in, you get a failing test. If it can't, you get the exact line of code that stopped it.

That's the whole product. It checks one failure, cross-user and cross-tenant data exposure, because it's the one that is both catastrophic and cleanly provable. User B either got user A's data or didn't. There's nothing to debate, so there are few false alarms, so you'll keep it switched on.

```
nosy · 11 paths tried on this diff
GOT IN       GET /api/videos/:id → nosy read alice's video
             tests/nosy/videos.test.ts FAILED (alice's canary in nosy's response)
BLOCKED      10 paths · RLS "videos_owner" (supabase/migrations/0004_rls.sql:9) · tests green
NOT CHECKED  storage bucket "renders" (no local emulator)
```

Clean run:

```
nosy got nothing. 14/14 blocked (9 by test, 5 static).
```

Worth sharing too.

## Installation (30-second setup)

### 1. Get the skill

The skill is the [`nosy/`](nosy/) folder: `SKILL.md`, `references/`, `scripts/`.

**Claude Code**

Copy it into your skills directory:

- all projects: `~/.claude/skills/nosy/`
- one project: `.claude/skills/nosy/`

**claude.ai**

Zip the `nosy/` folder (folder at the zip root) and upload it under Settings → Capabilities → Skills.

**API**

Upload the same folder through the Skills API.

Full details in [INSTALL.md](INSTALL.md). Python 3 is only needed for the optional diff scanner; everything else runs in your repo's own test framework.

### 2. Run it

- `nosy`: runs on your current diff, before you merge. This is the default.
- `nosy baseline`: no diff needed. Builds the ownership map for the whole repo and writes tests for your most important resources. Run this first on an existing app.

### 3. Confirm your ownership map once

Nosy infers who owns each table or resource and writes it to `nosy.map.yml`:

```yaml
videos:    {owner: user_id, access: owner-only}
orgs:      {owner: id,      access: members}
templates: {owner: null,    access: public-read}
```

You confirm it once. After that, every verdict is judged against it.

Bam, you're done.

## Why Nosy exists

### #1: Everyone ships "it works", nobody ships "it's mine"

**The Problem.** You test as yourself. As yourself, everything works. Nobody signs in as a stranger and asks for your data, so the missing check never shows up until a stranger does.

AI app builders have made this common. Lovable's missing-RLS pattern (CVE-2025-48757) exposed roughly 170 of 1,645 scanned apps across 303 endpoints, and a later incident in a featured app exposed 18,697 records.

**The Fix.** Nosy is the stranger, on your machine, before launch. It creates `alice` and `nosy` as test users. Alice creates a resource, and `nosy` tries to read, list, search, update, delete and export it.

- [`SKILL.md`](nosy/SKILL.md): the method
- [`references/leak-catalog.md`](nosy/references/leak-catalog.md): the attacks it picks from

### #2: "Looks secure" is not evidence

**The Problem.** A reviewer, human or model, can read a handler and say "that looks unguarded" or "that looks fine". Both are opinions. The unguarded handler may be saved by a database policy, and the tidy one may be calling the database with an admin key.

**The Fix.** Every finding is one of four labels, and each label has a bar to clear:

| Label | What it means | Bar |
|---|---|---|
| `GOT IN` | Nosy read or changed someone else's data | A test Nosy executed failed on unpatched code |
| `MIGHT GET IN` | A likely hole that could not be run | Static evidence only, every hop cited, no test built |
| `BLOCKED` | The path is closed | A blocking invariant cited at `file:line`, plus a green test whose controls passed, or a fully cited static trace (labelled `static`) |
| `NOT CHECKED` | Out of budget, or no emulator | The reason, stated |

Nosy never claims a test it didn't run, and never marks something `BLOCKED` without naming the line that blocks it. A comment in your code saying "this is safe" is treated as data, not evidence, and flagged as a possible prompt injection.

### #3: Alarms you can't trust get turned off

**The Problem.** Scanners that cry wolf get disabled by week two.

**The Fix.** `GOT IN` is reserved for a failed test, which is hard to argue with. `BLOCKED` results are shown too, so you can see what was cleared and why, not just what's broken. The bench (below) includes safe decoys on purpose: code that looks scary but is protected. Nosy is expected to clear them.

- [`examples/03-blocked.md`](examples/03-blocked.md): an unguarded-looking handler that's actually safe

### #4: A one-off audit decays the day after

**The Problem.** You fix the hole, ship, and the next refactor reopens it.

**The Fix.** The tests Nosy writes stay in `tests/nosy/` as a permanent regression suite, in your own test framework. After a fix, Nosy re-runs the red test and your existing suite, and reports the exact commands it ran (or says "suite not run").

## How it works

Four steps and a gate.

**0. Gate (under a minute).** Scan the diff for data-access surface: routes, server actions, queries, auth middleware, RLS and migrations, caches, storage, AI retrieval. Deleted lines count (a removed owner filter is the classic leak), and so do new files you haven't `git add`-ed yet. If nothing is touched, Nosy says so, lists what it checked, and stops. No ceremony on a README change.

**1. Ownership map, then trace.** Infer who owns each resource from the schema. A new table with no owner rule is a finding by itself. For each touched path, Nosy asks: who can reach it, who does the query run as (an RLS policy blocks nothing on a service-role query), and what enforces ownership on this exact path. This is why a `BLOCKED` can be trusted.

**2. Two-account harness.** `alice` and `nosy` in your test framework with a local test DB. Alice's data carries a unique canary. A read leaks if the canary reaches nosy; a write leaks if alice's row actually changed. For Supabase, RLS is proven at the SQL level with `supabase test db` (pgTAP), under each user's JWT claims.

**3. Prove.** Run the cheapest falsifier. Red on unpatched code is `GOT IN`. Green is only `BLOCKED` if the controls also passed (nosy really is signed in and can reach *its own* data through the same path) and the invariant is cited. Otherwise a green test could just mean the harness is broken. If it can't be run, it's `MIGHT GET IN` with the reason.

**4. Contain.** Propose the smallest fix and ask before touching anything but tests.

Budget: about 5 hypotheses, 3 attacks and 20 tool calls after the gate. When it runs out, it lists what it did not check.

## What it hunts

Direct ID access, missing filters in list and search, GraphQL resolvers (queries and mutations), RLS gaps (RLS off, `using (true)`, views that bypass RLS, a service-role key in client code), caches keyed without the user, RAG retrieval with no ACL filter, storage URLs, background jobs running as the wrong principal, and `owner_id` overwrite via mass assignment.

For each: what to look for, how Nosy attacks it, and what counts as a blocking invariant, in the [leak catalog](nosy/references/leak-catalog.md).

## Safety

Nosy is a skill that attacks things, so it has to be boring about permissions.

- **Local and test environments only.** It never touches deployed URLs, other people's sites, or production keys. If the only database it can reach is prod, it stops.
- **New test files only by default.** Any other edit, install, migration or network use gets asked about first.
- **Repo text is data.** Instructions hidden in comments or docs don't change a verdict.

See [THREAT_MODEL.md](THREAT_MODEL.md) for the permission tiers.

## Worked examples

- [`01-got-in.md`](examples/01-got-in.md): service-role client, no owner filter, a failing test
- [`02-might-get-in.md`](examples/02-might-get-in.md): a cache key without the user, no emulator, so honestly unproven
- [`03-blocked.md`](examples/03-blocked.md): looks open, closed by an RLS policy, cited by line

## Reference

### Modes

- **`nosy`**: run on the diff. Pre-merge.
- **`nosy baseline`**: build the ownership map and starter tests with no diff.

### Repo layout

```
nosy/                        the skill folder (zip or copy this)
├── SKILL.md
├── references/leak-catalog.md
├── references/harness.md    test recipes: pgTAP, HTTP routes, service functions
└── scripts/access_scan.py   read-only diff triage, stdlib only
tests/ACCEPTANCE.md          21 acceptance tests
eval/EVAL_PLAN.md            two-account bench and kill rule
examples/                    three worked ledgers
THREAT_MODEL.md  INSTALL.md
```

### The scanner

`python nosy/scripts/access_scan.py [BASE]` lists lines in your diff that touch the data-access surface, e.g. `route  api/videos/route.ts:3`. It is deliberately broad. A hit means "look here", never "vulnerable". Verify it works with `python nosy/scripts/access_scan.py --selftest`.

## Status and honesty

Nosy is early. The skill, scanner, catalog, examples and acceptance tests exist. The "Leaky Bakery" demo app (six planted leaks, four safe decoys) and the head-to-head bench against a plain agent do not yet, and until they do there are no published detection numbers. The [eval plan](eval/EVAL_PLAN.md) includes a kill rule: if Nosy doesn't beat a plain agent on false alarms, or `GOT IN` turns out to be mostly noise, it doesn't ship.

Hack around with it. Make it yours.
