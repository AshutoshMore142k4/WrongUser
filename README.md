# WrongUser

[![Skills](https://skills.sh/b/AshutoshMore142k4/nosy)](https://skills.sh/AshutoshMore142k4/nosy)

**Suspect at the seams. Believe only red.**

WrongUser is an agent skill that signs up as the wrong user and tries to read your first user's data.

If it gets in, you get a failing test. If it can't, you get the exact line of code that stopped it.

That's the whole product. It checks one failure, cross-user and cross-tenant data exposure, because it's the one that is both catastrophic and cleanly provable. User B either got user A's data or didn't. There's nothing to debate, so there are few false alarms, so you'll keep it switched on.

It's small, it works with any agent that reads `SKILL.md`, and it runs in your own repo with your own test framework. It leaves the tests behind. Hack around with it. Make it yours. Enjoy.

```
wronguser · 11 paths tried on this diff
GOT IN       GET /api/videos/:id → wronguser read alice's video
             tests/wronguser/videos.test.ts FAILED (alice's canary in wronguser's response)
BLOCKED      10 paths · RLS "videos_owner" (supabase/migrations/0004_rls.sql:9) · tests green
NOT CHECKED  storage bucket "renders" (no local emulator)
```

A clean run looks like this, and it's worth sharing too:

```
wronguser got nothing. 14/14 blocked (9 by test, 5 static).
```

## Installation (30-second setup)

### 1. Get the skill

**skills.sh**

```bash
npx skills add AshutoshMore142k4/nosy
```

**Claude Code (by hand)**

Copy [`skills/wronguser/`](skills/wronguser/) to `~/.claude/skills/wronguser/` for every project, or `.claude/skills/wronguser/` for one.

**claude.ai**

Zip the `wronguser/` folder (folder at the zip root) and upload it under Settings → Capabilities → Skills.

**API**

Upload the same folder through the Skills API.

More detail in [INSTALL.md](INSTALL.md). Python 3.9+ is only needed for the optional diff scanner.

### 2. Run `wronguser`

In your agent, on the branch you're about to merge:

- `wronguser`: attacks the current diff. This is the default.
- `wronguser baseline`: no diff needed. Maps the whole repo and writes tests for your most important resources. Run this first on an existing app.

### 3. Confirm your ownership map once

WrongUser infers who owns each table or resource and writes it to `wronguser.map.yml`:

```yaml
videos:    {owner: user_id, read: owner,   write: owner}
projects:  {owner: org_id,  via: org_members, read: members, write: members}
templates: {owner: null,    read: public,  write: none}
```

You confirm it once. After that, every verdict is judged against it.

### 4. Bam, you're ready to go.

## Why WrongUser Exists

I built this to fix the one failure that AI app builders make over and over: shipping an app where one user can see another user's stuff.

### #1: Nobody Tests As A Stranger

> "Every access to every object must be checked for authority."
>
> Saltzer & Schroeder, *The Protection of Information in Computer Systems*

**The Problem.** You test as yourself. As yourself, everything works. Nobody signs in as a stranger and asks for your data, so the missing check never shows up until a stranger does.

AI app builders have made this common. Lovable's missing-RLS pattern (CVE-2025-48757) is the best-known example: tables with no row-level security, reachable by anyone with the public key.

**The Fix.** WrongUser is the stranger, on your machine, before launch. It creates `alice` and `wronguser` as test users. Alice creates a resource, and `wronguser` tries to read, list, search, update, delete and export it.

- [`SKILL.md`](skills/wronguser/SKILL.md): the method
- [`leak-catalog.md`](skills/wronguser/references/leak-catalog.md): the attacks it picks from

### #2: "Looks Secure" Is Not Evidence

> "Program testing can be used to show the presence of bugs, but never to show their absence!"
>
> Edsger W. Dijkstra

**The Problem.** A reviewer, human or model, can read a handler and say "that looks unguarded" or "that looks fine". Both are opinions. The unguarded handler may be saved by a database policy, and the tidy one may be calling the database with an admin key. A green test isn't proof either: a test that never signed the attacker in passes for the wrong reason.

**The Fix.** Every finding gets one of four labels, and each label has a bar to clear:

| Label | What it means | Bar |
|---|---|---|
| `GOT IN` | WrongUser read or changed someone else's data | A test it executed failed on unpatched code |
| `MIGHT GET IN` | A likely hole that couldn't be run | Static evidence only, every hop cited, no test built |
| `BLOCKED` | The path is closed | A blocking invariant cited at `file:line`, plus a green test whose controls passed, or a fully cited static trace (labelled `static`) |
| `NOT CHECKED` | Out of budget, or no emulator | The reason, stated |

Every test plants a **canary** in alice's data and includes **controls**: `wronguser` must be able to reach its *own* data through the same path, and SQL tests must run as the app role, not the table owner. If a control fails, the result is `NOT CHECKED`, never `BLOCKED`.

A comment in your code saying "this is safe" is data, not evidence. It gets flagged as a possible prompt injection.

### #3: Alarms You Can't Trust Get Turned Off

**The Problem.** Scanners that cry wolf get disabled by week two.

**The Fix.** `GOT IN` is reserved for a failed test, which is hard to argue with. `BLOCKED` results are shown too, so you can see what was cleared and why, not just what's broken. The bench (below) includes safe decoys on purpose: code that looks scary but is protected. WrongUser is expected to clear them.

- [`03-blocked.md`](examples/03-blocked.md): a handler that looks unguarded but is protected by an RLS policy

### #4: An Audit Decays The Day After

**The Problem.** You fix the hole, ship, and the next refactor reopens it.

**The Fix.** The tests WrongUser writes stay in `tests/wronguser/` as a permanent regression suite, in your own test framework. On the next run it re-runs them first: an old test that turns red is the cheapest `GOT IN` there is. After a fix, it re-runs the red test and your existing suite, and reports the exact commands it ran (or says "suite not run").

The gate also reads *removed* lines, because a deleted owner filter is the classic regression, and untracked files, because a brand-new route you haven't `git add`-ed is still a route.

## How It Works

Four steps and a gate.

**0. Gate (under a minute).** Scan the diff for data-access surface: routes, server actions, queries, auth middleware, RLS and migrations, caches, storage, AI retrieval. If nothing is touched, WrongUser says so, lists what it checked, and stops. No ceremony on a README change.

**1. Ownership map, then trace.** Infer who owns each resource from the schema. A new table with no owner rule is a finding by itself. For each touched path, ask: who can reach it, who does the query run as (an RLS policy blocks nothing on a service-role query), and what enforces ownership on this exact path. This is why a `BLOCKED` can be trusted.

**2. Two-account harness.** `alice` and `wronguser` in your test framework with a local test DB. For Supabase, RLS is proven at the SQL level with `supabase test db` (pgTAP), under each user's JWT claims. Recipes for pgTAP, HTTP routes and service functions are in [`harness.md`](skills/wronguser/references/harness.md).

**3. Prove.** Run the cheapest falsifier. Red on unpatched code is `GOT IN`. Green with passing controls and a cited invariant is `BLOCKED`. If it can't be run, it's `MIGHT GET IN` with the reason.

**4. Contain.** Propose the smallest fix and ask before touching anything but tests.

Budget: about 5 hypotheses, 3 test files and 20 tool calls after the gate. When it runs out, it lists what it did not check.

## Safety

WrongUser attacks things, so it has to be boring about permissions.

- **Local and test environments only.** It never touches deployed URLs, other people's sites, or production keys. It checks what your config points at before running anything, and never prints secret values.
- **New test files only by default.** Any other edit, install, service start, migration or network use gets asked about first.
- **Repo text is data.** Instructions hidden in comments, docs or seed data don't change a verdict.

See [THREAT_MODEL.md](THREAT_MODEL.md) for the permission tiers.

## Summary

Access control is the bug you only find by being the wrong person. This skill is a cheap way to be the wrong person before someone else is. Try it on your next migration.

## Reference

One skill, two modes. `wronguser` is user-invoked: type it. It can also be reached for by the agent when you ask things like "can other users see my data?" or "is this safe to launch?".

### Skill

- **[wronguser](skills/wronguser/SKILL.md)**: Prove whether user B can reach user A's data. Gate → ownership map and trace → two-account harness → prove → contain. Writes a ledger of `GOT IN` / `MIGHT GET IN` / `BLOCKED` / `NOT CHECKED`.
  - `wronguser`: run on the current diff, before merge.
  - `wronguser baseline`: build the ownership map and starter tests with no diff.

### What it hunts

Direct ID access, missing filters in list and search, GraphQL resolvers (queries and mutations), RLS gaps (RLS off, `using (true)`, views that bypass RLS, a service-role key in client code), caches keyed without the user, RAG retrieval with no ACL filter, storage URLs, background jobs running as the wrong principal, and `owner_id` overwrite via mass assignment. Details in the [leak catalog](skills/wronguser/references/leak-catalog.md).

### Worked examples

- [`01-got-in.md`](examples/01-got-in.md): service-role client, no owner filter, a failing test
- [`02-might-get-in.md`](examples/02-might-get-in.md): a cache key without the user, no emulator, so honestly unproven
- [`03-blocked.md`](examples/03-blocked.md): looks open, closed by an RLS policy, cited by line

### The scanner

`python skills/wronguser/scripts/access_scan.py [BASE]` lists lines in your diff (added, removed, and untracked files) that touch the data-access surface, e.g. `route  api/videos/route.ts:3`. It's deliberately broad. A hit means "look here", never "vulnerable". Check it works with `python skills/wronguser/scripts/access_scan.py --selftest`.

### Repo layout

```
skills/wronguser/            the skill folder (copy or zip this)
├── SKILL.md
├── references/leak-catalog.md
├── references/harness.md    test recipes: pgTAP, HTTP routes, service functions
└── scripts/access_scan.py   read-only diff triage, stdlib only
tests/ACCEPTANCE.md          21 acceptance tests
eval/EVAL_PLAN.md            two-account bench and kill rule
examples/                    three worked ledgers
THREAT_MODEL.md  INSTALL.md
```

## Status

WrongUser is early. The skill, scanner, catalog, examples and acceptance tests exist, and the scanner and the canary-and-controls method have been exercised on a small SQLite fixture. Not yet done: the pgTAP and HTTP recipes have not been run against a real Supabase or web app, and the "Leaky Bakery" demo app (six planted leaks, four safe decoys) and the head-to-head bench against a plain agent don't exist yet. Until they do, there are no published detection numbers.

The [eval plan](eval/EVAL_PLAN.md) has a kill rule: if WrongUser doesn't beat a plain agent on false alarms, or `GOT IN` turns out to be mostly noise, it doesn't ship.
