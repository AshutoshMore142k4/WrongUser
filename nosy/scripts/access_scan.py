#!/usr/bin/env python3
"""Read-only diff triage for Nosy. Prints "look here" hints, never verdicts.

Usage (from the repo root):
  python access_scan.py [BASE]     # `git diff BASE` (default HEAD) + untracked files
  git diff main | python access_scan.py -
  python access_scan.py --selftest

Scans added AND removed lines: a deleted owner filter is the classic leak.
"""
import os
import re
import subprocess
import sys

# category -> regex. Broad on purpose: a hit means "go look".
PATTERNS = {
    "route": r"(app\.(get|post|put|patch|delete)\(|router\.|@(Get|Post|Put|Patch|Delete)\(|export\s+(async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\b|['\"]use server['\"])",
    "query": r"(findById|findUnique|findFirst|findMany|\.select\(|\.from\(['\"]|\.query\(|SELECT\s|UPDATE\s|DELETE\s+FROM|\.eq\(['\"]id['\"])",
    "owner": r"\b(user_id|owner_id|org_id|tenant_id|userId|ownerId|orgId|tenantId)\b",
    "auth": r"(middleware|matcher|getSession|getServerSession|getUser\(|currentUser|requireAuth|isAuthenticated|withAuth|clerkMiddleware|@UseGuards|authorize)",
    "rls": r"(row level security|(create|alter|drop)\s+policy|using\s*\(\s*true\s*\)|security\s+definer|security_invoker|create\s+(or\s+replace\s+)?view)",
    "service-role": r"(service_role|SERVICE_ROLE|supabaseAdmin|createClient\([^)]*service)",
    "cache": r"(cache\.(get|set)|redis\.|unstable_cache|lru_cache|cacheKey|revalidate)",
    "storage": r"(createSignedUrl|getPublicUrl|\.storage\.from|s3\.|getSignedUrl|presign)",
    "retrieval": r"(similarity_search|match_documents|vectorStore|\.upsert\(|namespace|embedding)",
    "mass-assign": r"(owner_id|user_id|org_id|tenant_id)\s*[:=]\s*(req\.|body\.|input\.|data\.)|\.\.\.(req\.body|body|input)\b",
    "job": r"(cron|queue\.add|inngest|bullmq|setInterval|background)",
}
COMPILED = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
CREATE_TABLE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)", re.I)
ENABLE_RLS = re.compile(r"alter\s+table\s+(?:only\s+)?([\w.\"]+)\s+enable\s+row\s+level\s+security", re.I)


def scan(diff: str):
    hits, tables, rls_on = [], {}, set()
    old_path = path = None
    old = new = old_left = new_left = 0
    for raw in diff.splitlines():
        # Outside a hunk: file headers. Hunk counts keep a removed "-- comment" from reading as "--- a/file".
        if old_left <= 0 and new_left <= 0:
            if raw.startswith("--- "):
                old_path = raw[4:].removeprefix("a/")
            elif raw.startswith("+++ "):
                p = raw[4:]
                path = old_path if p == "/dev/null" else p.removeprefix("b/")
            elif (m := HUNK.match(raw)):
                old, old_left = int(m[1]), int(m[2] or 1)
                new, new_left = int(m[3]), int(m[4] or 1)
            continue
        tag, text = raw[:1], raw[1:]
        if tag == " ":
            old, new, old_left, new_left = old + 1, new + 1, old_left - 1, new_left - 1
            continue
        if tag == "+":
            mark, line, new, new_left = "", new, new + 1, new_left - 1
        elif tag == "-":
            mark, line, old, old_left = "[removed] ", old, old + 1, old_left - 1
        else:  # "\ No newline at end of file"
            continue
        for cat, rx in COMPILED.items():
            if rx.search(text):
                hits.append((cat, path, line, mark + text.strip()[:100]))
        if tag == "+" and path.endswith(".sql") and (m := CREATE_TABLE.search(text)):
            tables[m.group(1).strip('"').lower()] = (path, line)
        if tag == "+" and (m := ENABLE_RLS.search(text)):
            rls_on.add(m.group(1).strip('"').lower())
    for t, (p, l) in tables.items():
        if t not in rls_on:
            hits.append(("rls-missing", p, l, f"table {t}: no 'enable row level security' in this diff"))
    return hits


def untracked_as_diff():
    """`git diff` never shows new files that were not `git add`-ed; render them as all-added."""
    names = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z"],
                           capture_output=True, text=True, check=True).stdout.split("\0")
    out = []
    for name in filter(None, names):
        try:
            if os.path.getsize(name) > 1_000_000:
                continue
            with open(name, encoding="utf-8", errors="replace") as f:
                body = f.read()
        except OSError:
            continue
        if "\0" in body:  # binary
            continue
        lines = body.splitlines()
        out += ["--- /dev/null", f"+++ b/{name}", f"@@ -0,0 +1,{len(lines)} @@", *("+" + l for l in lines)]
    return "\n".join(out)


def main(argv):
    sys.stdout.reconfigure(errors="replace")  # repo text can hold chars a Windows console can't print
    if argv[:1] == ["--selftest"]:
        return selftest()
    if argv[:1] == ["-"]:
        diff = sys.stdin.read()
    else:
        diff = subprocess.run(["git", "diff", "-U0", *(argv[:1] or ["HEAD"])],
                              capture_output=True, text=True, check=True).stdout
        diff += "\n" + untracked_as_diff()
    hits = scan(diff)
    if not hits:
        print("nosy: no data-access boundary touched - not investigating.")
        print("checked (added, removed and untracked lines): routes, queries, owner columns, auth/middleware, "
              "RLS/policies/views, service-role, caches, storage, retrieval, mass-assign, jobs")
        return 0
    for cat, p, l, t in hits:
        print(f"{cat:12} {p}:{l}  {t}")
    return 0


def selftest():
    sql = ("--- /dev/null\n+++ b/supabase/migrations/0001.sql\n@@ -0,0 +1,3 @@\n"
           "+create table videos (id uuid, user_id uuid);\n"
           "+create table notes (id uuid);\n"
           "+alter table notes enable row level security;\n")
    cats = {(c, t) for c, _, _, t in scan(sql) if c == "rls-missing"}
    assert len(cats) == 1 and "videos" in next(iter(cats))[1], cats

    ts = ("--- a/api/v.ts\n+++ b/api/v.ts\n@@ -0,0 +1,2 @@\n"
          "+export async function GET(req) {\n+  return db.video.findUnique({ where: { id } })\n")
    got = {(c, l) for c, _, l, _ in scan(ts)}
    assert ("route", 1) in got and ("query", 2) in got, got

    # pure deletion of an owner filter must not pass the gate
    rm = "--- a/api/v.ts\n+++ b/api/v.ts\n@@ -7 +6,0 @@\n-    .eq('user_id', user.id)\n"
    assert ("owner", "api/v.ts", 7, "[removed] .eq('user_id', user.id)") in scan(rm), scan(rm)

    # a removed SQL comment ("--- ...") inside a hunk is a line, not a file header
    pol = ("--- a/supabase/migrations/0002.sql\n+++ b/supabase/migrations/0002.sql\n@@ -1,2 +0,0 @@\n"
           "--- owner policy\n-create policy videos_owner on videos using (auth.uid() = user_id);\n")
    assert {(c, p) for c, p, _, _ in scan(pol)} >= {("rls", "supabase/migrations/0002.sql")}, scan(pol)

    # deleting a whole file is attributed to that file, not /dev/null
    gone = "--- a/middleware.ts\n+++ /dev/null\n@@ -1 +0,0 @@\n-export default clerkMiddleware()\n"
    assert [(c, p) for c, p, _, _ in scan(gone)] == [("auth", "middleware.ts")], scan(gone)

    assert scan("--- /dev/null\n+++ b/README.md\n@@ -0,0 +1 @@\n+hello\n") == []
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
